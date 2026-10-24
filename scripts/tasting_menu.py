#!/usr/bin/env python3
"""Read-only GitHub intake and validation for the FLaNN Tasting Menu.

No dependencies. `sync` fetches issues/comments and writes a reviewable JSON
snapshot; it never publishes, selects papers, or mutates GitHub. All review
content remains untrusted text and must be escaped by website renderers.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/tasting-menu.json"
SNAPSHOT = ROOT / "data/tasting-menu-nominations.json"
MARKER = "<!-- flann-tasting-menu -->"
RELATIONSHIPS = {"Independent reader", "Author / coauthor", "Other conflict of interest"}
BASE = "Recommend (+1)"
STRONG = "Strongly recommend (+5)"
REASON_FIELD = "Why do you believe this is a good paper?"
SCORING_KEYS = {"recommendation", "endorsement", "threshold", "minCommentLength"}
EXCLUDED_LABELS = {
    "rejected", "withdrawn", "spam", "tasting-menu-rejected",
    "tasting-menu-withdrawn", "tasting-menu-spam",
}
EMPTY_VALUES = {"", "_no response_", "no response", "n/a", "na", "none", "tbd", "-"}
FIELD_NAMES = {"Edition", "Paper title", "Paper URL", "Authors", "Published", "Topic",
               "Relationship", "Recommendation", REASON_FIELD}


class ValidationError(ValueError):
    """Invalid input that can be reported without a traceback."""


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("Expected an ISO date or timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO date or timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            raise ValidationError("Timestamps must specify a timezone")
    return parsed.astimezone(timezone.utc)


def boundary(value: str | None, *, closing: bool = False) -> datetime | None:
    if value is None:
        return None
    parsed = timestamp(value)
    if closing and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        parsed = datetime.combine(parsed.date(), time.max, timezone.utc)
    return parsed


def validate_config(config: dict) -> None:
    if not isinstance(config, dict):
        raise ValidationError("Configuration must be an object")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(config.get("repository", ""))):
        raise ValidationError("repository must be owner/repository")
    if not isinstance(config.get("preview"), bool):
        raise ValidationError("preview must be true or false")
    if type(config.get("targetPapers")) is not int or config["targetPapers"] < 1:
        raise ValidationError("targetPapers must be a positive integer; it is a planning target, not a cap")
    validate_scoring(config.get("scoring"))
    edition = config.get("edition")
    if not isinstance(edition, dict):
        raise ValidationError("edition must be an object")
    if not isinstance(edition.get("id"), str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", edition["id"]):
        raise ValidationError("edition.id must be a lowercase slug")
    if edition.get("status") not in {"planning", "open", "review", "closed", "published"}:
        raise ValidationError("Unknown edition status")
    for key in ("title", "paperWindow"):
        if not isinstance(edition.get(key), str) or not edition[key].strip():
            raise ValidationError(f"edition.{key} is required")
    for key in ("opens", "closes"):
        if key not in edition:
            raise ValidationError(f"edition.{key} must be a date, timestamp or null")
    opens = boundary(edition["opens"])
    closes = boundary(edition["closes"], closing=True)
    if opens and closes and opens >= closes:
        raise ValidationError("The round must close after it opens")
    if not config["preview"] and edition["status"] == "open" and not (opens and closes):
        raise ValidationError("A live open round needs opening and closing dates")


def validate_scoring(scoring: dict) -> None:
    if not isinstance(scoring, dict) or set(scoring) != SCORING_KEYS:
        raise ValidationError("scoring must contain recommendation, endorsement, threshold and minCommentLength")
    for key in SCORING_KEYS:
        if type(scoring[key]) is not int or scoring[key] < 1:
            raise ValidationError(f"scoring.{key} must be a positive integer")
    if scoring["recommendation"] != 1:
        raise ValidationError("The basic recommendation weight is fixed at 1, including author and conflicted recommendations")
    if scoring["endorsement"] <= scoring["recommendation"]:
        raise ValidationError("The endorsement weight must be greater than the recommendation weight")


def recommendation_labels(scoring: dict) -> tuple[str, str]:
    return f"Recommend (+{scoring['recommendation']})", f"Strongly recommend (+{scoring['endorsement']})"


def valid_reason(value: str, scoring: dict) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized.lower() not in EMPTY_VALUES and len(normalized) >= scoring["minCommentLength"]


def safe_url(value: str) -> str:
    """Accept public HTTPS links, rejecting executable and local URLs."""
    if not isinstance(value, str) or value != value.strip() or re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValidationError("URLs must be HTTPS links without whitespace or backslashes")
    try:
        parts = urlsplit(value)
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError as exc:
        raise ValidationError("Malformed URL") from exc
    if parts.scheme.lower() != "https" or not host or parts.username or parts.password or port not in {None, 443}:
        raise ValidationError("Only public HTTPS URLs without credentials or custom ports are allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or host.endswith((".local", ".localhost", ".internal", ".test", ".invalid", ".example")) or re.fullmatch(r"[0-9.]+", host):
            raise ValidationError("Local or reserved hostnames are not allowed")
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValidationError("Invalid hostname") from exc
        if not re.fullmatch(r"[a-z0-9.-]+", host) or any(not label or label.startswith("-") or label.endswith("-") for label in host.split(".")):
            raise ValidationError("Invalid hostname")
    else:
        if not address.is_global:
            raise ValidationError("Private or reserved IP addresses are not allowed")
        if address.version == 6:
            host = f"[{host}]"
    return urlunsplit(("https", host, parts.path or "/", parts.query, parts.fragment))


def canonical_paper(value: str) -> tuple[str, str]:
    url = safe_url(value)
    parts = urlsplit(url)
    host = parts.hostname
    if host in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
        match = re.fullmatch(r"/(?:abs|pdf|html)/((?:\d{4}\.\d{4,5}|[A-Za-z.-]+/\d{7}))(?:v\d+)?(?:\.pdf)?/?", parts.path)
        if match:
            arxiv_id = match.group(1).lower()
            return "arxiv:" + arxiv_id, "https://arxiv.org/abs/" + arxiv_id
    if host in {"doi.org", "dx.doi.org", "www.doi.org"}:
        doi = unquote(parts.path).lstrip("/").rstrip("/").lower()
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi) or re.search(r"[\x00-\x20\x7f]", doi):
            raise ValidationError("Malformed DOI link")
        arxiv_alias = re.fullmatch(r"10\.48550/arxiv\.(\d{4}\.\d{4,5}|[a-z.-]+/\d{7})(?:v\d+)?", doi)
        if arxiv_alias:
            arxiv_id = arxiv_alias.group(1)
            return "arxiv:" + arxiv_id, "https://arxiv.org/abs/" + arxiv_id
        return "doi:" + doi, "https://doi.org/" + quote(doi, safe="/:;()[]-._~")
    query = sorted((key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                   if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"})
    canonical = urlunsplit(("https", parts.netloc, parts.path.rstrip("/") or "/", urlencode(query), ""))
    return "url:" + hashlib.sha256(canonical.encode()).hexdigest()[:24], canonical


def parse_fields(body: str | None) -> dict[str, str]:
    if not isinstance(body, str):
        return {}
    fields: dict[str, str] = {}
    headings = [heading for heading in re.finditer(r"^### ([^\r\n]+)\s*$", body, re.MULTILINE)
                if heading.group(1).strip() in FIELD_NAMES]
    for index, heading in enumerate(headings):
        key = heading.group(1).strip()
        if key in fields:
            return {}  # Repeated fields are ambiguous; do not silently choose one.
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        value = body[heading.end():end].strip()
        fields[key] = "" if value.lower() in EMPTY_VALUES else value
    return fields


def published_date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError("Published dates must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Published dates must use a valid YYYY-MM-DD date") from exc


def is_person(item: dict) -> bool:
    user = item.get("user") or {}
    login = user.get("login", "")
    return bool(isinstance(login, str) and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", login)
                and user.get("type") != "Bot" and not login.lower().endswith("[bot]"))


def contribution_date(item: dict, config: dict, now: datetime) -> datetime | None:
    try:
        created = timestamp(item.get("created_at"))
    except ValidationError:
        return None
    opens = boundary(config["edition"]["opens"])
    closes = boundary(config["edition"]["closes"], closing=True)
    if created > now or (opens and created < opens) or (closes and created > closes):
        return None
    return created


def endorsement(item: dict, fields: dict[str, str], scoring: dict) -> dict | None:
    if not is_person(item) or fields.get("Relationship") not in RELATIONSHIPS:
        return None
    requested = fields.get("Recommendation")
    base, strong_label = recommendation_labels(scoring)
    independent = fields["Relationship"] == "Independent reader"
    valid_labels = {base, strong_label} if independent else {BASE, base, strong_label}
    if requested not in valid_labels or not valid_reason(fields.get(REASON_FIELD), scoring):
        return None
    try:
        url = safe_url(item.get("html_url", ""))
    except ValidationError:
        return None
    recommendation = requested if independent else BASE
    return {
        "login": item["user"]["login"],
        "relationship": fields["Relationship"],
        "recommendation": recommendation,
        "reason": fields[REASON_FIELD],
        "url": url,
    }


def summarize(endorsements: list[dict], scoring: dict) -> dict:
    _, strong_label = recommendation_labels(scoring)
    strong = sum(item["relationship"] == "Independent reader" and item["recommendation"] == strong_label for item in endorsements)
    score = sum(1 if item["relationship"] != "Independent reader" else
                scoring["endorsement"] if item["recommendation"] == strong_label else scoring["recommendation"]
                for item in endorsements)
    return {"supporters": len(endorsements), "strong": strong,
            "score": score, "eligible": score >= scoring["threshold"]}


def build_snapshot(config: dict, issues: list[dict], comments: dict[int, list[dict]],
                   now: datetime | None = None) -> dict:
    validate_config(config)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    papers: dict[str, dict] = {}
    votes: dict[str, dict[str, tuple]] = {}
    for issue in sorted(issues, key=lambda item: (item.get("created_at", ""), item.get("number", 0))):
        labels = {str(label.get("name", "") if isinstance(label, dict) else label).lower()
                  for label in issue.get("labels", [])}
        if "pull_request" in issue or "tasting-menu" not in labels or labels & EXCLUDED_LABELS or not is_person(issue):
            continue
        fields = parse_fields(issue.get("body"))
        if fields.get("Edition") != config["edition"]["id"] or not fields.get("Paper title"):
            continue
        if contribution_date(issue, config, now) is None:
            continue
        try:
            paper_id, paper_url = canonical_paper(fields.get("Paper URL", ""))
            issue_url = safe_url(issue.get("html_url", ""))
            published_date(fields.get("Published", ""))
        except (ValidationError, ValueError):
            continue
        if not fields.get("Authors") or not fields.get("Topic"):
            continue
        if paper_id not in papers:
            papers[paper_id] = {
                "id": paper_id, "title": fields["Paper title"], "url": paper_url,
                "authors": fields["Authors"], "published": fields["Published"],
                "topic": fields["Topic"], "issueUrl": issue_url,
            }
            votes[paper_id] = {}
        contributions = [(issue, fields)]
        for comment in comments.get(issue.get("number"), []):
            if MARKER in (comment.get("body") or ""):
                contributions.append((comment, parse_fields(comment.get("body"))))
        for item, review_fields in contributions:
            created = contribution_date(item, config, now)
            review = endorsement(item, review_fields, config["scoring"])
            if created is None or review is None:
                continue
            login = review["login"].lower()
            order = (created, item.get("id", 0))
            previous = votes[paper_id].get(login)
            if previous is None or order > previous[0]:
                votes[paper_id][login] = (order, review)
    for paper_id, paper in papers.items():
        reviews = [row[1] for _, row in sorted(votes[paper_id].items())]
        paper.update(summarize(reviews, config["scoring"]))
        paper["endorsements"] = reviews
    return {
        "updatedAt": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "edition": config["edition"]["id"],
        "scoring": dict(config["scoring"]),
        "papers": sorted(papers.values(), key=lambda paper: (-paper["score"], paper["id"])),
    }


class GitHub:
    """Only fetch fixed GitHub API endpoints; never follow untrusted pagination URLs."""

    def __init__(self, repository: str, token: str | None = None):
        self.repository = repository
        self.token = token

    def pages(self, endpoint: str, **query) -> list[dict]:
        rows = []
        page = 1
        while True:
            params = urlencode({**query, "per_page": 100, "page": page})
            url = f"https://api.github.com/repos/{self.repository}/{endpoint}?{params}"
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "FLaNN-Tasting-Menu",
                       "X-GitHub-Api-Version": "2022-11-28"}
            if self.token:
                headers["Authorization"] = "Bearer " + self.token
            try:
                with urlopen(Request(url, headers=headers), timeout=30) as response:
                    data = json.load(response)
            except HTTPError as exc:
                raise ValidationError(f"GitHub API returned HTTP {exc.code}. Check repository access and API limits.") from exc
            except (URLError, TimeoutError) as exc:
                raise ValidationError("Could not reach the GitHub API. No snapshot was written.") from exc
            if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
                raise ValidationError("Unexpected GitHub API response. No snapshot was written.")
            rows.extend(data)
            if len(data) < 100:
                return rows
            page += 1

    def collect(self) -> tuple[list[dict], dict[int, list[dict]]]:
        issues = self.pages("issues", state="all", labels="tasting-menu", sort="created", direction="asc")
        comments = {}
        for issue in issues:
            if "pull_request" not in issue and issue.get("comments", 0):
                number = issue.get("number")
                if type(number) is not int or number < 1:
                    raise ValidationError("Unexpected issue number from GitHub")
                comments[number] = self.pages(f"issues/{number}/comments")
        return issues, comments


def validate_snapshot(config: dict, snapshot: dict) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("edition") != config["edition"]["id"]:
        raise ValidationError("Snapshot must match the configured edition")
    validate_scoring(snapshot.get("scoring"))
    if snapshot["scoring"] != config["scoring"]:
        raise ValidationError("Snapshot scoring must match the edition configuration; use a new edition ID to change established rules")
    if snapshot.get("updatedAt") is not None:
        timestamp(snapshot["updatedAt"])
    if not isinstance(snapshot.get("papers"), list):
        raise ValidationError("Snapshot papers must be a list")
    if snapshot["papers"] and snapshot.get("updatedAt") is None:
        raise ValidationError("A populated snapshot needs updatedAt")
    ids = set()
    for paper in snapshot["papers"]:
        if not isinstance(paper, dict):
            raise ValidationError("Snapshot paper must be an object")
        paper_id, _ = canonical_paper(paper.get("url", ""))
        if paper.get("id") != paper_id or paper_id in ids:
            raise ValidationError("Snapshot IDs must be canonical and unique")
        ids.add(paper_id)
        for key in ("title", "authors", "published", "topic"):
            if not isinstance(paper.get(key), str) or not paper[key].strip():
                raise ValidationError(f"Missing paper {key}")
        published_date(paper["published"])
        safe_url(paper.get("issueUrl", ""))
        reviews = paper.get("endorsements")
        if not isinstance(reviews, list):
            raise ValidationError("endorsements must be a list")
        people = set()
        for review in reviews:
            if not isinstance(review, dict):
                raise ValidationError("Endorsements must be objects")
            login = review.get("login", "")
            if not is_person({"user": {"login": login}}) or login.lower() in people:
                raise ValidationError("Endorsements require unique human logins")
            people.add(login.lower())
            base, strong_label = recommendation_labels(config["scoring"])
            valid_labels = {base, strong_label} if review.get("relationship") == "Independent reader" else {BASE}
            if review.get("relationship") not in RELATIONSHIPS or review.get("recommendation") not in valid_labels:
                raise ValidationError("Unknown relationship or recommendation")
            if not valid_reason(review.get("reason"), config["scoring"]):
                raise ValidationError("Recommendations need a comment meeting the edition's minimum length")
            safe_url(review.get("url", ""))
        for key, expected in summarize(reviews, config["scoring"]).items():
            if type(paper.get(key)) is not type(expected) or paper.get(key) != expected:
                raise ValidationError(f"Snapshot {key} disagrees with its endorsements")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Could not read valid JSON from {path.relative_to(ROOT)}: {exc}") from exc


def write_snapshot(snapshot: dict) -> None:
    """Replace the snapshot only after all API calls and validation succeed."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=SNAPSHOT.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    try:
        temporary.replace(SNAPSHOT)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sync", "check", "test"))
    args = parser.parse_args()
    if args.command == "test":
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_tasting_menu.py")
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    try:
        config = read_json(CONFIG)
        validate_config(config)
        if args.command == "sync":
            if config["edition"]["status"] == "published":
                raise ValidationError("Published editions are frozen. For an explicit reviewed correction, change edition.status to 'review', review the new snapshot in a pull request, then restore 'published'.")
            previous = read_json(SNAPSHOT)
            if previous.get("edition") == config["edition"]["id"] and previous.get("updatedAt") is not None and previous.get("scoring") != config["scoring"]:
                raise ValidationError("This edition's scoring rules are frozen after its first snapshot. Use a new edition ID for changed rules.")
            issues, comments = GitHub(config["repository"], os.environ.get("GITHUB_TOKEN")).collect()
            snapshot = build_snapshot(config, issues, comments)
            validate_snapshot(config, snapshot)
            write_snapshot(snapshot)
            print(f"Saved {len(snapshot['papers'])} nominations for host validation. No GitHub changes or publication performed.")
        else:
            validate_snapshot(config, read_json(SNAPSHOT))
            print("Tasting Menu configuration and nomination snapshot are valid.")
    except ValidationError as exc:
        print(f"Tasting Menu: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
