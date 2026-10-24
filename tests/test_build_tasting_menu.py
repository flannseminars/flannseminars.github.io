"""Publication-boundary regressions using isolated, realistic edition fixtures."""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE / 'scripts'))
spec = importlib.util.spec_from_file_location('build_tasting_menu', SITE / 'scripts/build_tasting_menu.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
REPOSITORY = 'flannseminars/flannseminars.github.io'
SOURCE = f'https://github.com/{REPOSITORY}/issues/123#issuecomment-456'
SCORING = {'recommendation': 1, 'endorsement': 5, 'threshold': 20, 'minCommentLength': 20}
TEMPLATE = '''<!doctype html><html><body>
<!-- highlights:start --><!-- highlights:end -->
<span data-score="recommendation">1</span><span data-score="endorsement">5</span>
<span id="snapshot-date">Not open</span>
<div id="nominations" aria-live="polite"><div>No nominations yet</div></div>
<noscript>Read GitHub</noscript>
<span id="form-mode">Next edition</span>
<p class="tm-note" id="form-explanation">Prepare a recommendation for the next round.</p>
<button type="submit" id="draft-button" disabled>Prepare draft →</button>
<!-- archive:start --><!-- archive:end -->
</body></html>'''


class BuildTastingMenuTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'data').mkdir()
        (self.root / 'tasting-menu.html').write_text(TEMPLATE)
        self.config = {
            'repository': REPOSITORY, 'preview': True, 'targetPapers': 5,
            'scoring': copy.deepcopy(SCORING),
            'edition': {'id': 'pilot', 'title': 'Pilot edition', 'status': 'planning',
                        'opens': None, 'closes': None, 'paperWindow': 'Previous cycle'},
        }
        self.editions = [self.edition('preview', example=True)]
        self.papers = [self.paper('example-paper', 'preview', example=True)]

    @staticmethod
    def edition(slug, example=False, scoring=None):
        return {
            'id': slug, 'title': f'{slug.title()} edition', 'label': slug.title(),
            'published': '2026-10-01', 'example': example,
            'description': 'A small collection of reader recommendations.',
            'scoring': copy.deepcopy(scoring or SCORING),
            'resultsUrl': None if example else f'https://github.com/{REPOSITORY}/issues/123',
            'validationNote': 'Duplicate submissions and declared relationships were checked.',
        }

    @staticmethod
    def paper(slug, edition='pilot', example=False):
        return {
            'id': slug, 'edition': edition, 'example': example,
            'title': 'An interesting construction', 'authors': 'A. Author', 'published': '2026',
            'topic': 'Theory', 'url': 'https://arxiv.org/abs/2610.12345',
            'standfirst': 'Readers recommend spending time with this construction.',
            'endorsements': [{
                'example': example, 'name': 'Example reader A' if example else 'Test reader',
                'relationship': 'Independent reader', 'weight': 5,
                'text': 'I think this is a good paper because its construction suggests new possibilities.',
                'url': None if example else SOURCE,
            }],
            'support': {'recommendations': 0, 'endorsements': 4, 'score': 20},
            'hostNote': 'The public tally was checked against the announced rules.',
            'discussionUrl': None if example else f'https://github.com/{REPOSITORY}/issues/123',
        }

    def live(self):
        self.config['preview'] = False
        self.config['edition']['status'] = 'published'
        self.editions = [self.edition('pilot')]
        self.papers = [self.paper('real-paper')]

    def render(self, check=False):
        (self.root / 'data/tasting-menu.json').write_text(json.dumps(self.config))
        (self.root / 'data/tasting-menu-editorial.json').write_text(json.dumps({
            'editions': self.editions, 'papers': self.papers,
        }))
        with redirect_stdout(io.StringIO()):
            builder.render(check=check, root=self.root)

    def read(self, relative='tasting-menu.html'):
        return (self.root / relative).read_text()

    def test_preview_off_removes_sample_posts_editions_and_quotes(self):
        self.render()
        sample_paths = [self.root / 'tasting-menu/papers/example-paper.html',
                        self.root / 'tasting-menu/editions/preview.html']
        self.assertTrue(all(path.exists() for path in sample_paths))
        self.config['preview'] = False
        with self.assertRaisesRegex(ValueError, 'remove'):
            self.render(check=True)
        self.assertTrue(all(path.exists() for path in sample_paths), '--check must not mutate files')
        self.render()
        self.assertFalse(any(path.exists() for path in sample_paths))
        for relative in ('tasting-menu.html', 'tasting-menu/archive.html'):
            content = self.read(relative)
            self.assertNotIn('Example reader A', content)
            self.assertNotIn('example-paper.html', content)
        self.render(check=True)
        self.config['preview'] = True
        self.render()
        self.assertTrue(all(path.exists() for path in sample_paths))

    def test_removed_generated_entries_leave_unrelated_files_alone(self):
        self.render()
        handwritten = self.root / 'tasting-menu/papers/handwritten.html'
        handwritten.write_text('<p>An unrelated page</p>')
        self.editions, self.papers = [], []
        self.render()
        self.assertTrue(handwritten.exists())
        self.assertFalse((self.root / 'tasting-menu/papers/example-paper.html').exists())
        self.assertFalse((self.root / 'tasting-menu/editions/preview.html').exists())

    def test_real_quotes_and_results_require_this_repositorys_sources(self):
        for field in ('quote', 'results', 'discussion'):
            for url in (None, 'https://example.com/comment',
                        'https://github.com/another/project/issues/1',
                        f'https://github.com/{REPOSITORY}/issues-not-a-thread/1'):
                with self.subTest(field=field, url=url):
                    self.live()
                    if field == 'quote':
                        self.papers[0]['endorsements'][0]['url'] = url
                    elif field == 'results':
                        self.editions[0]['resultsUrl'] = url
                    else:
                        self.papers[0]['discussionUrl'] = url
                    with self.assertRaises(ValueError):
                        self.render()

    def test_examples_cannot_impersonate_real_readers_or_source_links(self):
        for key, value in [('name', 'A real researcher'), ('url', SOURCE), ('example', False)]:
            with self.subTest(field=key):
                self.papers = [self.paper('example-paper', 'preview', example=True)]
                self.papers[0]['endorsements'][0][key] = value
                with self.assertRaises(ValueError):
                    self.render()
        self.papers = [self.paper('example-paper', 'preview', example=True)]
        self.render()
        page = self.read('tasting-menu/papers/example-paper.html')
        self.assertNotIn('Example reader A', page)
        self.assertNotIn(self.papers[0]['endorsements'][0]['text'], page)

    def test_more_than_five_qualifying_papers_are_all_published(self):
        self.live()
        self.papers = [self.paper(f'paper-{number}') for number in range(7)]
        self.render()
        self.assertEqual(len(list((self.root / 'tasting-menu/papers').glob('*.html'))), 7)
        for paper in self.papers:
            self.assertIn(f'papers/{paper["id"]}.html', self.read())
        self.assertIn('7 papers', self.read('tasting-menu/archive.html'))

    def test_twenty_ordinary_recommendations_qualify_without_extra_quorum(self):
        self.live()
        self.papers[0]['support'] = {'recommendations': 20, 'endorsements': 0, 'score': 20}
        self.papers[0]['endorsements'][0].update(weight=1, relationship='Author / coauthor')
        self.render()
        page = self.read('tasting-menu/papers/real-paper.html')
        self.assertIn('20 recommendations', page)
        self.assertIn('20 <span>endorsements</span>', page)
        self.assertIn('0 strong endorsements', page)
        self.assertIn('Author / coauthor', page)
        self.assertIn('20<small>endorsements</small>', self.read())

    def test_menu_counts_people_instead_of_weighted_points(self):
        self.live()
        self.papers[0]['support'] = {'recommendations': 1, 'endorsements': 4, 'score': 21}
        self.render()
        self.assertIn('5<small>endorsements</small>', self.read())
        self.assertNotIn('21<small>endorsements</small>', self.read())

    def test_invalid_or_below_threshold_scores_are_rejected_before_writing(self):
        invalid = [
            {'recommendations': 0, 'endorsements': 4, 'score': 21},
            {'recommendations': 4, 'endorsements': 3, 'score': 19},
            {'recommendations': -1, 'endorsements': 5, 'score': 24},
            {'recommendations': True, 'endorsements': 4, 'score': 21},
        ]
        for support in invalid:
            with self.subTest(support=support):
                self.live()
                self.papers = [self.paper('valid'), self.paper('invalid')]
                self.papers[1]['support'] = support
                with self.assertRaises(ValueError):
                    self.render()
                self.assertEqual(self.read(), TEMPLATE)
                self.assertFalse((self.root / 'tasting-menu/papers/valid.html').exists())

    def test_optional_author_guide_is_omitted_and_real_guide_has_no_placeholder(self):
        self.live()
        self.render()
        page = self.read('tasting-menu/papers/real-paper.html')
        self.assertNotIn('id="author-guide"', page)
        self.assertNotIn('No companion video', page)
        self.assertNotIn('Placeholder', page)
        self.papers[0]['authorGuide'] = {
            'example': False, 'by': 'The authors', 'title': 'A way into the paper',
            'paragraphs': ['Start with the construction.'], 'videoUrl': None,
        }
        self.render()
        page = self.read('tasting-menu/papers/real-paper.html')
        self.assertIn('id="author-guide"', page)
        self.assertIn('By The authors', page)
        self.assertNotIn('Placeholder', page)

    def test_sample_author_guide_is_not_displayed_as_an_author_contribution(self):
        self.papers[0]['authorGuide'] = {
            'example': True, 'by': 'Example authors', 'title': 'An illustrative guide',
            'paragraphs': ['Sample guide copy, not supplied by the actual paper authors.'], 'videoUrl': None,
        }
        self.render()
        page = self.read('tasting-menu/papers/example-paper.html')
        self.assertNotIn('id="author-guide"', page)
        self.assertNotIn('Example authors', page)
        self.assertNotIn('Sample guide copy', page)

    def test_archives_keep_permanent_navigation_and_their_original_scoring(self):
        self.live()
        old_rules = dict(SCORING, endorsement=3, threshold=30)
        self.editions.append(self.edition('past', scoring=old_rules))
        old_paper = self.paper('older-paper', 'past')
        old_paper['support'] = {'recommendations': 0, 'endorsements': 10, 'score': 30}
        old_paper['endorsements'][0]['weight'] = 3
        self.papers.append(old_paper)
        self.render()
        self.assertIn('href="tasting-menu/editions/past.html"', self.read())
        self.assertIn('href="../tasting-menu/editions/past.html"', self.read('tasting-menu/archive.html'))
        edition_page = self.read('tasting-menu/editions/past.html')
        self.assertIn('href="../../tasting-menu/papers/older-paper.html"', edition_page)
        self.assertIn('+3 endorsement · 30-point threshold', edition_page)
        old_page = self.read('tasting-menu/papers/older-paper.html')
        self.assertIn('href="../editions/past.html"', old_page)
        self.assertIn('href="../archive.html"', old_page)
        self.assertIn('20-point threshold', self.read('tasting-menu/editions/pilot.html'))
        self.render(check=True)

    def test_active_edition_rules_cannot_disagree_with_the_current_call(self):
        self.live()
        self.editions[0]['scoring']['threshold'] = 25
        self.papers[0]['support'] = {'recommendations': 0, 'endorsements': 5, 'score': 25}
        with self.assertRaises(ValueError):
            self.render()

    def test_no_javascript_status_is_truthful_for_every_round_state(self):
        self.config['preview'] = False
        self.editions, self.papers = [], []
        expected = {'planning': 'Nominations have not opened', 'review': 'Host checks in progress',
                    'closed': 'Nominations closed', 'published': 'Edition published'}
        for status, label in expected.items():
            with self.subTest(status=status):
                self.config['edition']['status'] = status
                self.render()
                self.assertIn(label, self.read())
                self.assertNotIn('No real nominations have been collected', self.read())
        self.config['edition'].update(status='open', opens='2027-01-01T00:00:00Z', closes='2027-01-15T23:59:59Z')
        self.render()
        self.assertIn('Nomination window: 2027-01-01T00:00:00Z', self.read())
        self.assertIn('2027-01-15T23:59:59Z', self.read())
        self.assertIn('id="draft-button" disabled', self.read())

    def test_unknown_edition_duplicate_ids_and_example_mismatches_are_rejected(self):
        mutations = [
            lambda: self.papers[0].update(edition='unknown'),
            lambda: self.papers.append(copy.deepcopy(self.papers[0])),
            lambda: self.editions.append(copy.deepcopy(self.editions[0])),
            lambda: self.papers[0].update(example=True),
            lambda: self.papers[0].update(id='../unsafe'),
            lambda: self.editions[0].update(validationNote=''),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                self.live()
                mutate()
                with self.assertRaises(ValueError):
                    self.render()

    def test_conflicted_quotes_cannot_claim_five_points(self):
        for relationship in ('Author / coauthor', 'Other conflict of interest'):
            with self.subTest(relationship=relationship):
                self.live()
                self.papers[0]['endorsements'][0]['relationship'] = relationship
                with self.assertRaisesRegex(ValueError, 'Conflicted'):
                    self.render()

    def test_displayed_recommendations_cannot_duplicate_readers_or_exceed_tally(self):
        self.live()
        self.papers[0]['endorsements'].append(copy.deepcopy(self.papers[0]['endorsements'][0]))
        with self.assertRaises(ValueError):
            self.render()
        self.live()
        self.papers[0]['support'] = {'recommendations': 20, 'endorsements': 0, 'score': 20}
        # The retained +5 excerpt cannot be part of a tally containing no +5 votes.
        with self.assertRaises(ValueError):
            self.render()

    def test_unsafe_links_are_rejected_and_reader_text_is_escaped(self):
        self.live()
        self.papers[0]['title'] = '<script>alert("title")</script>'
        self.papers[0]['endorsements'][0].update(text='<img src=x onerror=alert(1)>', name='Reader <name>')
        self.render()
        page = self.read('tasting-menu/papers/real-paper.html')
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('&lt;img', page)
        self.assertIn('Reader &lt;name&gt;', page)
        self.assertNotIn('<script>', page)
        for url in ('javascript:alert(1)', 'https://localhost/private', 'https://127.0.0.1/private'):
            with self.subTest(url=url):
                self.live()
                self.papers[0]['url'] = url
                with self.assertRaises(ValueError):
                    self.render()

    def test_missing_generated_regions_fail_instead_of_silently_skipping(self):
        for marker in ('<!-- highlights:end -->', '<!-- archive:end -->', 'id="snapshot-date"'):
            with self.subTest(marker=marker):
                (self.root / 'tasting-menu.html').write_text(TEMPLATE.replace(marker, ''))
                with self.assertRaises(ValueError):
                    self.render()

    def test_actual_site_template_build_is_repeatable_without_mutating_source(self):
        source = (SITE / 'tasting-menu.html').read_text()
        (self.root / 'tasting-menu.html').write_text(source)
        self.render()
        self.render(check=True)
        self.assertEqual((SITE / 'tasting-menu.html').read_text(), source)
        self.assertTrue((self.root / 'tasting-menu/archive.html').exists())
        self.assertTrue((self.root / 'tasting-menu/editions/preview.html').exists())


if __name__ == '__main__':
    unittest.main()
