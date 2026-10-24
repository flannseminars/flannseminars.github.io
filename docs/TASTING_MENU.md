# FLaNN Tasting Menu

An open, community-led way to find a few papers worth spending time with. Three times a year, readers nominate papers, explain what they found valuable, and help FLaNN assemble a small, approachable reading menu.

The result is up to five highlights per edition. Each highlight has a paper link, a short editorial introduction, an optional video, and attributed recommendations from people who have read the work. The public nomination archive remains available for everyone who wants a longer menu.

## What makes this useful

The scarce resource is reader attention. A useful recommendation should tell someone **why this paper is worth their time, what to look at, and where its claims stop**. Enthusiasm is welcome, but a more forceful adjective should not buy a larger vote. A strong endorsement earns extra weight by providing specific evidence and acknowledging a limitation.

This is a reading recommendation, not a scientific award or a claim that unselected papers are worse. Selection will reflect the available recommendations, editorial capacity, and the mix of subjects in an edition.

## The pilot

- Publish the rules, eligibility period, and opening and closing times before accepting nominations.
- Keep nominations and endorsements open for two weeks. Anyone with a GitHub account can participate publicly.
- During the third week, check eligibility and conflicts, contact contributors when clarification is needed, and prepare up to five highlights.
- Publish an editorial record explaining selections and any departures from the advisory score. Keep all eligible nominations visible.
- After publication, review participation and editor workload before changing the rules for the next edition.

Do not promise exactly five papers. If only three have convincing independent support, publish three. Review the whole window at its deadline rather than taking the first five submissions: timing, time zones, and access to a large network should not decide the menu.

### Suggested annual rhythm

| Edition | Papers from the preceding period | Nomination period | Editorial work |
| --- | --- | --- | --- |
| January | September–December of the previous year | Two announced weeks in January | Following week |
| May | January–April | Two announced weeks in May | Following week |
| September | May–August | Two announced weeks in September | Following week |

These are proposed recurring months, not scheduled deadlines. Choose the pilot's exact dates and time zone before opening it. If the community is organized around conference cycles, the published paper window can name that cycle instead of using the calendar periods above.

For the pilot, accept publicly accessible papers, including preprints, with a first public version or a substantive new version in the announced window. A version update must explain what changed. Ask for a stable paper link and version date. Editors should resolve borderline cases publicly and consistently; a private claim of eligibility is insufficient.

## How participation works

One public GitHub issue represents one nominated paper. Search existing nominations before creating another. Anyone, including an author, can nominate a paper. The nomination supplies bibliographic details and the nominator's recommendation; later recommendations are recorded in comments. Together, nominations and comments supply one latest valid contribution per GitHub account per canonical paper. An extra comment does not buy an extra vote.

A recommendation is a signed, structured issue comment. GitHub reactions can express appreciation, but they are not counted votes. Participants identify their relationship to the paper and their level of engagement with it. Recommendations are public and may be reproduced on the FLaNN website with attribution and a link to the original; posting through this template agrees to that use. The comment template includes the marker `<!-- flann-tasting-menu -->` and these exact headings:

```markdown
<!-- flann-tasting-menu -->
### Relationship
Independent reader

### Recommendation
Strongly recommend (+2)

### Why read it?
[Explain the contribution and why it matters to a reader.]

### What have you read or checked?
[Identify the parts of the work you examined and what you learned.]

### Caveat or limitation
[State an important assumption, limitation, or open question.]
```

Use one relationship value: `Independent reader`, `Author / coauthor`, or `Other conflict of interest`. Use one recommendation value: `Recommend (+1)` or `Strongly recommend (+2)`. Replace the bracketed instructions with your own text. A basic recommendation needs a reason; the checked-work and caveat sections are optional for that level.

The automatic completeness checks require at least 120 characters of reasoning, 60 characters describing what was read or checked, and 40 characters of caveat for an independent strong endorsement. An otherwise valid recommendation that falls short counts as one point. These thresholds reject thin submissions; they cannot judge scientific substance, which editors must read.

| Contribution | Advisory weight | Requirements |
| --- | --- | --- |
| Recommendation | 1 | State what makes the paper worth reading and declare any relevant relationship. |
| Strong endorsement | 2 | Have read or checked the relevant work; give a concrete contribution, evidence or insight, and a limitation or boundary. |
| Author, coauthor, or other conflicted endorsement | At most 1 | Declare the relationship. It does not count as independent support, regardless of requested strength. |
| Reaction, anonymous praise, or an incomplete record | 0 | Visible discussion may still be useful, but it does not count toward the score. |

A strong endorsement is worth two points in total, not an additional two points. Recommend as many papers as you can honestly discuss during the pilot; there is no artificial scarcity budget for strong endorsements yet. If many submissions become generic or coordinated, revise the rules prospectively after the pilot.

An independent reader is someone who is neither an author/coauthor nor otherwise materially connected to the paper. Declare relevant relationships such as advising, recent close collaboration, a direct commercial stake, or involvement in the work. Same-institution affiliation alone is not automatically a conflict; disclose it when it could reasonably affect how readers interpret the recommendation. Editors make uncertain cases explicit in the public record.

**The eligibility floor for a highlight is two independent readers, including at least one independent strong endorsement.** This is a minimum for editorial consideration, not automatic selection. Editors check the substance of endorsements and declared conflicts before finalizing a highlight.

GitHub accounts and declarations provide public attribution, not verified real-world identity or independently audited conflict checks. Do not describe the counts as verified expert consensus. Report manipulation, duplicate identities, or undisclosed relationships through a public correction where practical; editors may remove abusive or privacy-sensitive material under ordinary repository moderation.

## How editors choose the menu

Use at least two editors to review the final shortlist where possible. An editor who authored or has a material conflict with a candidate should recuse themselves from that decision. Name the participating editors in the edition's publication note.

1. Merge duplicate paper nominations by linking them to a canonical issue. The importer combines arXiv versions and arXiv-issued DOI aliases automatically. For an ordinary publisher DOI and a separate arXiv link to the same work, normalize the Paper URL fields to one canonical link; posting cross-links alone does not combine their votes. Preserve the original public discussion.
2. Check paper-window eligibility, accessible links, complete recommendations, and conflicts. Do not count a nomination itself as an extra vote.
3. Identify papers that meet the independent-support floor. Use the advisory score to help prioritize reading, while checking the actual substance of the recommendations. Review the generated data before publishing; an automatic eligibility flag is not editorial approval.
4. Choose up to five based on the strength of the evidence, relevance to FLaNN, and a useful mix of topics and perspectives. Avoid interpreting community size or name recognition as paper quality.
5. Record a short, factual selection reason for each highlight and explain meaningful departures from the score. Mark eligible papers left out for capacity or edition balance without implying a negative scientific judgment.
6. Publish the edition through a reviewed pull request. Freeze its selection record; later factual corrections should be dated and linked publicly.

Avoid public numerical ratings of paper quality. The tally measures declared recommendations under these rules; it is not an estimate of correctness, impact, or importance.

## What a paper highlight contains

- **Paper:** title, authors, public paper URL, version/date, and optional code or project links.
- **Why spend time on it:** a short editorial introduction, roughly 120–200 words, with a concrete takeaway and who may find it useful.
- **What to notice:** one or two specific ideas, results, or figures that help a reader start.
- **Scope:** an important limitation, assumption, or unresolved question. Enthusiasm is more credible when its boundaries are visible.
- **Watch:** an optional existing author talk or a short new explanation, linked to its source. A video is useful but should not delay an otherwise complete highlight.
- **Community voices:** a small number of accurate, attributed excerpts with links back to their public recommendation comments.
- **Editorial record:** selection reason, publication date, and later corrections.

The website form requires acknowledgment that posted contributions are public and may be quoted with attribution; the issue form and comment template disclose the same terms. Contributors using those flows have already agreed, so editors do not need to request that permission again. When importing a direct contribution supplied outside these flows, verify that the contributor agreed to the proposed attribution and reuse. Keep accurate excerpts and links to their source. Do not silently sharpen praise, remove a material caveat, or present an author's own endorsement as independent validation. Prefer linking to an existing video; obtain permission before republishing or editing someone else's recording.

The linked GitHub discussion is the pilot's comment system. It keeps moderation, attribution, and the original context in one place without adding a separate account system to the static website.

## Moderation and corrections

Welcome substantive disagreement and clarification; this is not a venue for personal attacks or allegations without evidence. Keep the public discussion focused on the paper. Editors may ask contributors to clarify unsupported claims, conflicts, or ambiguous submissions. Explain exclusions and corrections publicly without amplifying private information.

Use the canonical nomination issue for correction requests and link any resulting website pull request. A correction to a published edition should preserve what changed and why. Do not quietly rewrite a published selection because later votes change its score.

If a contributor withdraws permission to quote them, remove the website excerpt and retain only the minimum public correction note needed. The original GitHub content remains subject to GitHub's own controls and the contributor's choices.

## Pipeline and activation

The repository implements a static-site pilot: public GitHub issues and structured recommendation comments feed a generated JSON snapshot; editors then maintain a separate publication record. The website reads those files. There is no private submission queue or hidden voting interface.

The checked-in pilot is in **planning / preview mode**. Sample material, where shown, is clearly marked as illustrative. Opening a local page or merging these files does not by itself announce a call, enable collection, or publish a completed edition.

The site configuration is in `data/tasting-menu.json`; editorial choices and highlight content are in `data/tasting-menu-editorial.json`. Keep generated nomination data separate from editorial prose so a refresh cannot overwrite a published summary or selection decision.

The editorial file contains a `papers` array. Each entry has a stable `id`, `edition`, `title`, `authors`, `published`, `topic`, `url`, `standfirst`, a `summary` array, `whyRead`, a `readingGuide` array, `caveat`, and optional `video`, `discussionUrl`, `selectionReason`, and `endorsements`. Mark illustrative entries with `example: true`; they are excluded when `preview` is false. Use real, source-checked bibliography for examples and never invent votes or community quotations.

The generator builds `tasting-menu.html` and individual pages under `tasting-menu/papers/<id>.html`:

```sh
python3 scripts/build_tasting_menu.py
```

The nomination utility provides synchronization, validation, and pipeline tests:

```sh
python3 scripts/tasting_menu.py sync
python3 scripts/tasting_menu.py check
python3 scripts/tasting_menu.py test
python3 -m unittest discover -s tests -v
python3 scripts/build_tasting_menu.py --check
```

Run these from the repository root. The sync needs network access to GitHub. Use the script's help output for its supported options and authentication configuration. Review the changed snapshot and regenerated pages before committing them.

Before activation, enable the repository's Issues feature, create the `tasting-menu` nomination label, and ensure the issue templates and workflow are on the default branch. GitHub's manually dispatched workflows must exist on the default branch before they are available from the Actions interface. Set the real repository, edition identifier, paper window, and explicit opening/closing timestamps in configuration. Set `preview` to `false` and the edition status to `open` only when the call is ready.

The native GitHub issue form applies the nomination label. Drafts opened from the website use ordinary issue creation because participants may not have permission to set labels themselves. Organizers must inspect incoming `[Tasting Menu]` issues and add `tasting-menu` before those nominations enter a sync. This is visible intake housekeeping, not editorial selection; apply the label to valid nominations consistently and explain exclusions publicly.

The workflow is named **Tasting Menu checks and preview snapshot**. A manual run with `sync: true` produces a snapshot artifact for review; it does not commit data or write to GitHub issues. Ordinary closure of an issue preserves the nomination. To exclude withdrawn, rejected, or spam submissions from the published snapshot, apply the corresponding `tasting-menu-withdrawn`, `tasting-menu-rejected`, or `tasting-menu-spam` label and explain the action when appropriate. Do not use an exclusion label merely because a valid paper was not selected.

The sync reads public GitHub data and writes a local snapshot. Review the resulting change in a pull request before merging it into the published site. Display the snapshot's refresh time: the page is not a live vote counter. Refresh during the call and once after the deadline; the final snapshot and editorial record should describe the same edition and cutoff.

The creation time determines whether a nomination or comment was submitted in the window and which valid contribution is latest. GitHub's API returns the current edited text; it cannot reconstruct exactly what that comment said at the deadline. Review late edits visibly, record any editorial correction, and freeze the final reviewed snapshot after closing. Re-running a sync later is not a way to reproduce historical at-deadline text. The sync command refuses to run when the edition status is `published`. For an intentional correction, temporarily move it to `review`, review the resulting diff in a pull request, and restore `published` before merging.

For a new edition, keep earlier real papers in `data/tasting-menu-editorial.json` with their original edition IDs. The generator retains their pages and lists earlier editions in the website archive. Before changing the active edition, copy its final reviewed nomination snapshot to `data/tasting-menu-archive/<edition>.json` and commit that copy so the cutoff record is preserved. The active board displays one edition; the original GitHub nomination issues and edition fields remain the public discussion archive. Do not overwrite the only copy of earlier summaries, selections, or final nomination records when preparing the next call.

## First-cycle checklist

- [ ] Choose the pilot's paper window, nomination dates, closing time zone, and publication target.
- [ ] Name the editors and agree on recusal and moderation responsibilities.
- [ ] Review the public rules and make any pilot-specific eligibility decisions explicit.
- [ ] Merge the templates and workflow; enable Issues and create the nomination label.
- [ ] Configure the real edition and replace or remove all preview examples.
- [ ] Try one clearly marked test nomination and recommendation, run a sync, and confirm that malformed records and author votes are treated correctly. Apply `tasting-menu-withdrawn` to the test issue and refresh the production snapshot before launch; simply closing the issue does not exclude it.
- [ ] Review the site on mobile and desktop; confirm paper links, GitHub links, snapshot time, and the closed/open state.
- [ ] Open the call and publish the prepared announcement through the organizers' usual channels.
- [ ] During the window, label valid website-created nominations, consolidate duplicates, answer process questions publicly, and refresh the snapshot.
- [ ] After closing, capture the final eligible recommendations and review the shortlist.
- [ ] Prepare and review the paper pages, attribution permissions, selection reasons, and publication note.
- [ ] Publish up to five highlights and preserve the complete nomination list.
- [ ] Review useful participation, diversity of nominators, reader feedback, and editor hours; record improvements for the next edition.

`docs/tasting-menu-call.txt` contains a draft community announcement. Replace every bracketed placeholder and review it before sending. Nothing in this branch sends the announcement automatically.
