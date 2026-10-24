"""Behavior tests for public intake; no network or external dependencies."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SPEC = importlib.util.spec_from_file_location("tasting_menu", Path(__file__).resolve().parents[1] / "scripts/tasting_menu.py")
tm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tm)

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
CONFIG = {
    "repository": "flannseminars/flannseminars.github.io", "preview": True, "maxPapers": 5,
    "edition": {"id": "pilot", "title": "Pilot edition", "status": "planning",
                "opens": None, "closes": None, "paperWindow": "Previous research cycle"},
}


def review_fields(strong=False, relationship="Independent reader"):
    return {
        "Relationship": relationship,
        "Recommendation": tm.STRONG if strong else tm.BASE,
        "Why read it?": "The paper connects its structural result to a concrete algorithm, with a clear explanation of which assumptions matter. The key example made the distinction useful to me.",
        "What have you read or checked?": "I read the central argument and checked its worked example against the assumptions stated in Section 2.",
        "Caveat or limitation": "The result depends on an assumption that the paper does not establish for arbitrary datasets.",
    }


def body(fields):
    return "\n\n".join(f"### {key}\n\n{value}" for key, value in fields.items())


def issue(number=1, login="alice", strong=False, url="https://arxiv.org/abs/2401.01234", **changes):
    fields = {"Edition": "pilot", "Paper title": "A useful paper", "Paper URL": url,
              "Authors": "A. Researcher and B. Researcher", "Published": "2026-09-01", "Topic": "Theory"}
    fields.update(review_fields(strong))
    row = {"id": number, "number": number, "body": body(fields), "labels": [{"name": "tasting-menu"}],
           "user": {"login": login, "type": "User"}, "created_at": "2026-10-01T12:00:00Z",
           "updated_at": "2026-10-01T12:00:00Z", "state": "open", "comments": 0,
           "html_url": f"https://github.com/flannseminars/flannseminars.github.io/issues/{number}"}
    row.update(changes)
    return row


def comment(login="bob", strong=False, ident=100, fields=None, **changes):
    row = {"id": ident, "body": tm.MARKER + "\n\n" + body(fields or review_fields(strong)),
           "user": {"login": login, "type": "User"}, "created_at": "2026-10-02T12:00:00Z",
           "html_url": f"https://github.com/flannseminars/flannseminars.github.io/issues/1#issuecomment-{ident}"}
    row.update(changes)
    return row


def snapshot(issues=None, comments=None, config=None):
    return tm.build_snapshot(config or CONFIG, issues if issues is not None else [issue()], comments or {}, NOW)


class CanonicalPaperTests(unittest.TestCase):
    def test_arxiv_versions_merge_across_pdf_html_and_abs(self):
        expected = ("arxiv:2401.01234", "https://arxiv.org/abs/2401.01234")
        for url in ("https://arxiv.org/pdf/2401.01234v3.pdf", "https://www.arxiv.org/abs/2401.01234v2",
                    "https://arxiv.org/html/2401.01234v1", "https://arxiv.org/abs/2401.01234?utm_source=mail"):
            with self.subTest(url=url):
                self.assertEqual(tm.canonical_paper(url), expected)

    def test_old_arxiv_ids(self):
        self.assertEqual(tm.canonical_paper("https://arxiv.org/pdf/math/0301234v2.pdf")[0], "arxiv:math/0301234")

    def test_doi_hosts_and_case_merge(self):
        self.assertEqual(tm.canonical_paper("https://dx.doi.org/10.1234/EXAMPLE"),
                         tm.canonical_paper("https://doi.org/10.1234/example"))

    def test_arxiv_doi_alias_and_versions_share_the_arxiv_identity(self):
        expected = tm.canonical_paper("https://arxiv.org/abs/2510.00368")
        for url in ("https://doi.org/10.48550/arXiv.2510.00368", "https://dx.doi.org/10.48550/arxiv.2510.00368v2",
                    "https://doi.org/10.48550%2FarXiv.2510.00368v3?utm_source=mail"):
            with self.subTest(url=url):
                self.assertEqual(tm.canonical_paper(url), expected)
        self.assertEqual(tm.canonical_paper("https://doi.org/10.48550/arXiv.math/0301234v2"),
                         tm.canonical_paper("https://arxiv.org/abs/math/0301234"))

    def test_percent_encoded_doi_merges_without_changing_link_structure(self):
        self.assertEqual(tm.canonical_paper("https://doi.org/10.1234%2FEXAMPLE"),
                         tm.canonical_paper("https://doi.org/10.1234/example"))

    def test_source_comment_fragment_is_preserved(self):
        source = "https://github.com/flannseminars/flannseminars.github.io/issues/1#issuecomment-123"
        self.assertEqual(tm.safe_url(source), source)

    def test_generic_tracking_removed_but_identity_query_preserved(self):
        first = tm.canonical_paper("https://papers.example.com/paper?id=1&utm_source=news#section")
        second = tm.canonical_paper("https://papers.example.com/paper?utm_medium=email&id=1")
        self.assertEqual(first, second)
        self.assertNotEqual(first[0], tm.canonical_paper("https://papers.example.com/paper?id=2")[0])

    def test_unsafe_urls_rejected(self):
        for value in ("javascript:alert(1)", "data:text/html,hello", "http://arxiv.org/abs/2401.01234",
                      "https://localhost/x", "https://127.0.0.1/x", "https://[::1]/x", "https://10.0.0.1/x",
                      "https://127.1/x", "https://2130706433/x",
                      "https://169.254.169.254/x", "https://user:pass@arxiv.org/x", "https://arxiv.org:8443/x",
                      "https://arxiv.org\\@evil.com/x", "https://internal/x", "https://site.local/x",
                      "https://arxiv.org/abs/hello\nworld"):
            with self.subTest(value=value), self.assertRaises(tm.ValidationError):
                tm.canonical_paper(value)


class IntakeTests(unittest.TestCase):
    def test_independent_strong_plus_second_reader_qualifies(self):
        result = snapshot([issue(strong=True)], {1: [comment()]})["papers"][0]
        self.assertEqual((result["supporters"], result["strong"], result["score"], result["eligible"]), (2, 1, 3, True))

    def test_single_reader_does_not_qualify(self):
        result = snapshot([issue(strong=True)])["papers"][0]
        self.assertEqual(result["score"], 2)
        self.assertFalse(result["eligible"])

    def test_two_base_votes_do_not_qualify(self):
        result = snapshot(comments={1: [comment()]})["papers"][0]
        self.assertFalse(result["eligible"])

    def test_author_and_conflicted_strong_requests_have_maximum_one(self):
        comments = [comment("author", fields=review_fields(True, "Author / coauthor")),
                    comment("collaborator", ident=101, fields=review_fields(True, "Other conflict of interest"))]
        result = snapshot([issue(strong=True)], {1: comments})["papers"][0]
        self.assertEqual((result["supporters"], result["strong"], result["score"]), (3, 1, 4))
        self.assertFalse(result["eligible"])
        self.assertTrue(all(row["recommendation"] == tm.BASE for row in result["endorsements"] if row["login"] != "alice"))

    def test_incomplete_strong_review_downgrades(self):
        fields = review_fields(True)
        fields["Caveat or limitation"] = "Needs more data."
        result = snapshot(comments={1: [comment(fields=fields)]})["papers"][0]
        self.assertEqual((result["strong"], result["score"]), (0, 2))

    def test_base_vote_needs_only_reason(self):
        fields = {"Relationship": "Independent reader", "Recommendation": tm.BASE, "Why read it?": "The worked example clarified the central claim."}
        result = snapshot(comments={1: [comment(fields=fields)]})["papers"][0]
        self.assertEqual(result["supporters"], 2)

    def test_missing_or_placeholder_reason_is_not_a_vote(self):
        for empty in ("", "_No response_", "N/A"):
            fields = review_fields(True)
            fields["Why read it?"] = empty
            with self.subTest(empty=empty):
                self.assertEqual(snapshot(comments={1: [comment(fields=fields)]})["papers"][0]["supporters"], 1)

    def test_latest_valid_vote_per_login_across_duplicate_issues(self):
        old = issue(strong=True)
        duplicate = issue(number=2, login="ALICE", url="https://arxiv.org/pdf/2401.01234v3.pdf", created_at="2026-10-02T00:00:00Z")
        recent = comment("alice", strong=True, created_at="2026-10-03T00:00:00Z")
        result = snapshot([old, duplicate], {2: [recent]})["papers"]
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["supporters"], result[0]["strong"], result[0]["score"]), (1, 1, 2))
        self.assertEqual(result[0]["issueUrl"], old["html_url"])

    def test_arxiv_and_its_doi_alias_do_not_double_count_one_reader(self):
        original = issue(strong=True)
        duplicate = issue(number=2, url="https://doi.org/10.48550/arXiv.2401.01234v2", created_at="2026-10-02T00:00:00Z")
        papers = snapshot([original, duplicate])["papers"]
        self.assertEqual(len(papers), 1)
        self.assertEqual((papers[0]["supporters"], papers[0]["strong"], papers[0]["score"]), (1, 0, 1))

    def test_new_invalid_vote_does_not_erase_previous_valid_vote(self):
        malformed = comment("alice", fields={"Relationship": "Independent reader", "Recommendation": "Amazing"})
        result = snapshot([issue(strong=True)], {1: [malformed]})["papers"][0]
        self.assertEqual(result["score"], 2)

    def test_unmarked_conversation_is_not_counted(self):
        result = snapshot(comments={1: [comment(body=body(review_fields(True)))]})["papers"][0]
        self.assertEqual(result["supporters"], 1)

    def test_bots_and_pull_requests_are_ignored(self):
        bot_issue = issue(2, user={"login": "robot", "type": "Bot"})
        pr = issue(3, pull_request={"url": "https://api.github.com/pulls/3"})
        bot_comment = comment(user={"login": "robot", "type": "Bot"})
        result = snapshot([issue(), bot_issue, pr], {1: [bot_comment]})["papers"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["supporters"], 1)

    def test_closed_issues_remain_but_rejected_or_wrong_edition_are_excluded(self):
        closed = issue(state="closed")
        rejected = issue(2, labels=[{"name": "tasting-menu"}, {"name": "rejected"}])
        withdrawn = issue(3, labels=[{"name": "tasting-menu"}, {"name": "tasting-menu-withdrawn"}])
        wrong = issue(4)
        wrong["body"] = wrong["body"].replace("\n\npilot", "\n\nold-edition")
        unlabeled = issue(5, labels=[])
        result = snapshot([closed, rejected, withdrawn, wrong, unlabeled])["papers"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["supporters"], 1)

    def test_round_dates_filter_submissions_and_include_entire_closing_date(self):
        config = deepcopy(CONFIG)
        config["edition"].update(opens="2026-10-01", closes="2026-10-02")
        early = comment("early", created_at="2026-09-30T23:59:59Z")
        late = comment("late", created_at="2026-10-03T00:00:00Z")
        final = comment("final", strong=True, created_at="2026-10-02T23:59:59Z")
        result = snapshot(comments={1: [early, late, final]}, config=config)["papers"][0]
        self.assertEqual({row["login"] for row in result["endorsements"]}, {"alice", "final"})
        self.assertTrue(result["eligible"])

    def test_closing_issue_after_deadline_does_not_erase_its_vote(self):
        config = deepcopy(CONFIG)
        config["edition"].update(opens="2026-10-01", closes="2026-10-02")
        result = snapshot([issue(state="closed", updated_at="2026-10-20T00:00:00Z")], config=config)["papers"][0]
        self.assertEqual(result["supporters"], 1)

    def test_future_and_malformed_timestamps_are_ignored(self):
        result = snapshot(comments={1: [comment("future", created_at="2099-01-01T00:00:00Z"), comment("bad", created_at="yesterday")]})["papers"][0]
        self.assertEqual(result["supporters"], 1)

    def test_duplicate_headings_are_ambiguous(self):
        self.assertEqual(tm.parse_fields("### Relationship\nIndependent reader\n### Relationship\nAuthor / coauthor"), {})

    def test_review_prose_can_contain_unrelated_markdown_headings(self):
        fields = review_fields(True)
        fields["Why read it?"] += "\n\n### A useful example\n\nThis part of the argument is particularly clear."
        parsed = tm.parse_fields(body(fields))
        self.assertEqual(parsed["Why read it?"], fields["Why read it?"])

    def test_consent_preamble_is_never_part_of_a_review_or_its_weight(self):
        fields = review_fields(True)
        fields["Caveat or limitation"] = "_No response_"
        generated = tm.MARKER + "\n\nI understand this contribution is public and may be quoted by FLaNN with attribution.\n\n" + body(fields)
        result = snapshot(comments={1: [comment(body=generated)]})["papers"][0]
        review = next(row for row in result["endorsements"] if row["login"] == "bob")
        self.assertEqual(review["caveat"], "")
        self.assertEqual(review["recommendation"], tm.BASE)
        self.assertEqual(result["strong"], 0)

    def test_missing_and_numeric_fields_do_not_create_votes(self):
        fields = review_fields()
        fields["Relationship"] = "42"
        self.assertEqual(snapshot(comments={1: [comment(fields=fields)]})["papers"][0]["supporters"], 1)

    def test_unsafe_paper_url_and_malformed_publication_date_are_ignored(self):
        bad_date = issue(2)
        bad_date["body"] = bad_date["body"].replace("2026-09-01", "next month")
        self.assertEqual(snapshot([issue(url="javascript:alert(1)"), bad_date])["papers"], [])


class ValidationTests(unittest.TestCase):
    def test_empty_and_populated_snapshots_validate(self):
        tm.validate_snapshot(CONFIG, {"updatedAt": None, "edition": "pilot", "papers": []})
        tm.validate_snapshot(CONFIG, snapshot([issue(strong=True)], {1: [comment()]}))

    def test_inflated_score_is_rejected(self):
        data = snapshot()
        data["papers"][0]["score"] = 100
        with self.assertRaises(tm.ValidationError):
            tm.validate_snapshot(CONFIG, data)

    def test_duplicate_votes_are_rejected(self):
        data = snapshot()
        data["papers"][0]["endorsements"] *= 2
        with self.assertRaises(tm.ValidationError):
            tm.validate_snapshot(CONFIG, data)

    def test_booleans_and_strings_cannot_replace_numeric_scores(self):
        for replacement in (True, "1", 1.0, None):
            data = snapshot()
            data["papers"][0]["supporters"] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(tm.ValidationError):
                tm.validate_snapshot(CONFIG, data)

    def test_date_format_and_invalid_calendar_dates_are_rejected(self):
        for published in ("20261001", "2026-02-30", 2026, None):
            with self.subTest(published=published), self.assertRaises(tm.ValidationError):
                tm.published_date(published)

    def test_optional_review_fields_can_be_blank(self):
        fields = {"Relationship": "Independent reader", "Recommendation": tm.BASE, "Why read it?": "Useful evidence for the claim."}
        tm.validate_snapshot(CONFIG, snapshot(comments={1: [comment(fields=fields)]}))

    def test_invalid_or_missing_round_dates_are_rejected(self):
        for dates in ({"opens": "2026-10-03", "closes": "2026-10-02"}, {"opens": "bad", "closes": None}):
            config = deepcopy(CONFIG)
            config["edition"].update(dates)
            with self.subTest(dates=dates), self.assertRaises(tm.ValidationError):
                tm.validate_config(config)
        config = deepcopy(CONFIG)
        config["preview"] = False
        config["edition"]["status"] = "open"
        with self.assertRaises(tm.ValidationError):
            tm.validate_config(config)


class GitHubTests(unittest.TestCase):
    def test_paginates_issues_and_comments_without_trusting_response_links(self):
        issue_rows = [issue(number=index + 1) for index in range(100)]
        issue_rows[0]["comments"] = 101
        api_pages = [issue_rows, [issue(number=101)],
                     [comment(ident=index + 100) for index in range(100)], [comment(ident=200)]]
        responses = [io.BytesIO(json.dumps(page).encode()) for page in api_pages]
        with patch.object(tm, "urlopen", side_effect=responses) as request:
            issues, comments = tm.GitHub(CONFIG["repository"]).collect()
        self.assertEqual(len(issues), 101)
        self.assertEqual(len(comments[1]), 101)
        urls = [call.args[0].full_url for call in request.call_args_list]
        self.assertIn("page=2", urls[1])
        self.assertIn("issues/1/comments", urls[2])
        self.assertIn("page=2", urls[3])

    def test_api_errors_do_not_expose_tokens(self):
        secret = "private-token-not-for-output"
        with patch.object(tm, "urlopen", side_effect=HTTPError("https://api.github.com", 403, "Forbidden", {}, None)):
            with self.assertRaises(tm.ValidationError) as error:
                tm.GitHub(CONFIG["repository"], secret).collect()
        self.assertNotIn(secret, str(error.exception))

    def test_sync_does_not_write_partial_snapshot_after_failure(self):
        with patch.object(tm.sys, "argv", ["tasting_menu.py", "sync"]), patch.object(tm, "read_json", return_value=CONFIG), \
             patch.object(tm.GitHub, "collect", side_effect=tm.ValidationError("API unavailable")), \
             patch.object(tm, "write_snapshot") as write, patch.object(tm.sys, "stderr", io.StringIO()):
            self.assertEqual(tm.main(), 1)
            write.assert_not_called()

    def test_published_sync_refuses_before_any_api_call_or_write(self):
        config = deepcopy(CONFIG)
        config["edition"]["status"] = "published"
        error_output = io.StringIO()
        with patch.object(tm.sys, "argv", ["tasting_menu.py", "sync"]), patch.object(tm, "read_json", return_value=config), \
             patch.object(tm.GitHub, "collect") as collect, patch.object(tm, "write_snapshot") as write, \
             patch.object(tm.sys, "stderr", error_output):
            self.assertEqual(tm.main(), 1)
        collect.assert_not_called()
        write.assert_not_called()
        self.assertIn("Published editions are frozen", error_output.getvalue())
        self.assertIn("reviewed correction", error_output.getvalue())
        self.assertIn("'review'", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
