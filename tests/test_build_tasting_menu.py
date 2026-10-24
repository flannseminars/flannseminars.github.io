"""Regression tests for publication boundaries, using isolated site copies."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('build_tasting_menu', SCRIPTS / 'build_tasting_menu.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

TEMPLATE = '''<!doctype html><html><body>
<div class="tm-preview" id="preview-notice">Preview</div>
<span id="edition-label">Preview</span>
<!-- highlights:start --><!-- highlights:end -->
<span id="snapshot-date">Not open</span>
<div id="nominations" aria-live="polite"><div>Preview nominations</div></div>
<noscript>Read GitHub</noscript>
<span id="form-mode">Preview</span>
<p class="tm-note" id="form-explanation">Preview</p>
<button type="submit" id="draft-button" disabled>Preview</button>
<div id="edition-archive">Archive</div>
</body></html>'''


class BuildTastingMenuTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'data').mkdir()
        (self.root / 'tasting-menu.html').write_text(TEMPLATE)
        self.config = {
            'repository': 'flannseminars/flannseminars.github.io', 'preview': True,
            'edition': {'id': 'pilot', 'title': 'Pilot edition', 'status': 'planning',
                        'opens': None, 'closes': None, 'paperWindow': 'Previous cycle'},
            'maxPapers': 5,
        }
        self.example = {
            'id': 'example-paper', 'example': True, 'edition': 'preview',
            'title': 'A useful paper', 'authors': 'A. Author', 'published': '2026',
            'topic': 'Theory', 'url': 'https://arxiv.org/abs/2601.01234',
            'standfirst': 'An editorial introduction.', 'summary': ['A short summary.'],
            'whyRead': 'An interesting construction.', 'readingGuide': ['Start with the construction.'],
            'caveat': 'The construction has assumptions.', 'video': None,
            'discussionUrl': None, 'selectionReason': None, 'endorsements': [],
        }
        self.papers = [copy.deepcopy(self.example)]

    def save(self):
        (self.root / 'data/tasting-menu.json').write_text(json.dumps(self.config))
        (self.root / 'data/tasting-menu-editorial.json').write_text(json.dumps({'papers': self.papers}))

    def render(self, check=False):
        self.save()
        builder.render(check=check, root=self.root)

    def real_paper(self, slug, edition='pilot'):
        paper = copy.deepcopy(self.example)
        paper.update(id=slug, edition=edition, example=False,
                     selectionReason='Specific independent support and relevance.',
                     discussionUrl='https://github.com/flannseminars/flannseminars.github.io/issues/1')
        return paper

    def test_preview_off_removes_example_pages_and_check_is_read_only(self):
        self.render()
        example_path = self.root / 'tasting-menu/papers/example-paper.html'
        self.assertTrue(example_path.exists())
        self.config['preview'] = False
        with self.assertRaisesRegex(ValueError, 'remove'):
            self.render(check=True)
        self.assertTrue(example_path.exists(), '--check must not delete files')
        self.render()
        self.assertFalse(example_path.exists())
        index = (self.root / 'tasting-menu.html').read_text()
        self.assertNotIn('example-paper.html', index)
        self.assertNotIn('No community nominations have been collected for this preview', index)
        self.render(check=True)

    def test_preview_can_be_enabled_again(self):
        self.config['preview'] = False
        self.render()
        self.config['preview'] = True
        self.render()
        index = (self.root / 'tasting-menu.html').read_text()
        self.assertIn('id="preview-notice"><strong>Design preview', index)
        self.assertIn('example-paper.html', index)

    def test_removing_editorial_entry_cleans_generated_file_only(self):
        self.render()
        unrelated = self.root / 'tasting-menu/papers/handwritten.html'
        unrelated.write_text('<p>Unrelated page</p>')
        self.papers = []
        self.render()
        self.assertFalse((self.root / 'tasting-menu/papers/example-paper.html').exists())
        self.assertTrue(unrelated.exists())

    def test_static_status_uses_configured_dates_without_claiming_open_now(self):
        self.config['preview'] = False
        self.config['edition'].update(status='open', opens='2027-01-01T00:00:00Z', closes='2027-01-15T23:59:59Z')
        self.render()
        index = (self.root / 'tasting-menu.html').read_text()
        self.assertIn('Nomination window: 2027-01-01T00:00:00Z', index)
        self.assertIn('2027-01-15T23:59:59Z', index)
        self.assertNotIn('Pilot round · not open yet', index)
        self.assertNotIn('Preview the submission flow', index)
        self.assertIn('id="draft-button" disabled', index)

    def test_static_published_round_does_not_claim_first_edition_is_ahead(self):
        self.config['preview'] = False
        self.config['edition']['status'] = 'published'
        self.papers = [self.real_paper('published-paper')]
        self.render()
        index = (self.root / 'tasting-menu.html').read_text()
        self.assertIn('Edition published', index)
        self.assertNotIn('The first edition is still ahead of us', index)

    def test_limit_applies_per_edition_including_archived_editions(self):
        self.papers = [self.real_paper(f'paper-{number}', 'past') for number in range(6)]
        with self.assertRaisesRegex(ValueError, 'paper limit'):
            self.render()
        self.papers = [self.real_paper(f'paper-{number}', 'past' if number < 3 else 'pilot') for number in range(6)]
        self.render()
        self.config['maxPapers'] = 6
        with self.assertRaisesRegex(ValueError, '1 to 5'):
            self.render()

    def test_invalid_editorial_is_rejected_before_writing(self):
        invalid = [
            ('summary', 'Not an array'), ('readingGuide', []), ('example', 'false'),
            ('title', None), ('video', 'javascript:alert(1)'),
            ('endorsements', [{'text': 'Praise', 'name': 'Reader', 'url': 'https://github.com/reader'}]),
        ]
        for field, value in invalid:
            with self.subTest(field=field):
                self.papers = [self.real_paper('valid'), self.real_paper('invalid')]
                self.papers[1][field] = value
                with self.assertRaises(ValueError):
                    self.render()
                self.assertEqual((self.root / 'tasting-menu.html').read_text(), TEMPLATE)
                self.assertFalse((self.root / 'tasting-menu/papers/valid.html').exists())

    def test_duplicate_or_unsafe_ids_are_rejected(self):
        for slug in ('example-paper', '../escape'):
            with self.subTest(slug=slug):
                self.papers = [copy.deepcopy(self.example), self.real_paper(slug)]
                with self.assertRaisesRegex(ValueError, 'Paper IDs'):
                    self.render()

    def test_real_highlight_requires_selection_and_source_discussion(self):
        for field in ('selectionReason', 'discussionUrl'):
            with self.subTest(field=field):
                self.papers = [self.real_paper('real-paper')]
                self.papers[0][field] = None
                with self.assertRaisesRegex(ValueError, field):
                    self.render()

    def test_text_is_escaped_and_unsafe_quote_url_is_rejected(self):
        self.papers = [self.real_paper('real-paper')]
        self.papers[0]['title'] = '<script>alert("title")</script>'
        self.papers[0]['endorsements'] = [{
            'text': '<img src=x onerror=alert(1)>', 'name': 'A <reader>',
            'relationship': 'Independent reader', 'url': 'https://github.com/reader',
        }]
        self.render()
        page = (self.root / 'tasting-menu/papers/real-paper.html').read_text()
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('&lt;img', page)
        self.assertNotIn('<script>', page)
        self.papers[0]['endorsements'][0]['url'] = 'https://localhost/private'
        with self.assertRaises(ValueError):
            self.render()

    def test_missing_template_region_fails_instead_of_silently_skipping(self):
        (self.root / 'tasting-menu.html').write_text(TEMPLATE.replace('<!-- highlights:end -->', ''))
        with self.assertRaisesRegex(ValueError, 'highlights region'):
            self.render()


if __name__ == '__main__':
    unittest.main()
