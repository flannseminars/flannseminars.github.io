import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../tasting-menu.js', import.meta.url), 'utf8');
const scoring = { recommendation: 1, endorsement: 5, threshold: 20, minCommentLength: 20 };

// Minimal DOM adapter: exercise the shipped script's event handlers and generated
// handoffs without a browser, network access, or a dependency on a DOM package.
class Node {
  constructor(tag = 'div') {
    this.tag = tag;
    this.children = [];
    this.listeners = {};
    this.attributes = {};
    this._text = '';
    this._value = '';
    this.hidden = false;
    this.disabled = false;
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent ?? child).join(''); }
  set value(value) {
    if (this.options) this.selectedIndex = this.options.findIndex(option => option.value === value);
    else this._value = value;
  }
  get value() { return this.options ? this.options[this.selectedIndex]?.value ?? '' : this._value; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._text = ''; this.children = nodes; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  setAttribute(name, value) { this.attributes[name] = value; }
  closest() { return this.field ??= new Node(); }
  focus() {}
  scrollIntoView() {}
  select() {}
}

async function mount({ preview = true, status = 'open', rules = scoring, snapshotRules = rules, papers = [] } = {}) {
  const ids = ['nomination-form', 'paper-search', 'paper-filter', 'nominations', 'nomination-tools',
    'paper-title', 'paper-url', 'paper-authors', 'paper-published', 'paper-topic', 'form-mode',
    'draft-button', 'draft-panel', 'form-status', 'nominate', 'relationship', 'recommendation',
    'reason', 'weight-note', 'draft-text', 'submit-github', 'open-thread', 'reset-mode', 'draft-help',
    'copy-draft', 'form-explanation', 'snapshot-date'];
  const nodes = Object.fromEntries(ids.map(id => [id, new Node()]));
  nodes['paper-filter'].value = 'all';
  nodes.relationship.value = 'Independent reader';
  nodes.recommendation.options = [{ value: 'Recommend (+1)' }, { value: 'Strongly recommend (+5)' }];
  nodes.recommendation.selectedIndex = 0;
  nodes['paper-title'].value = 'An interesting paper';
  nodes['paper-url'].value = 'https://arxiv.org/abs/2401.01234';
  nodes['paper-authors'].value = 'A. Researcher';
  nodes['paper-published'].value = '2026-10-01';
  nodes['paper-topic'].value = 'Theory';
  nodes.reason.value = 'This changes how I think about the problem.';
  const names = { title: 'paper-title', url: 'paper-url', authors: 'paper-authors', published: 'paper-published', topic: 'paper-topic', relationship: 'relationship', recommendation: 'recommendation', reason: 'reason' };
  const config = { repository: 'flannseminars/flannseminars.github.io', preview, scoring: rules,
    edition: { id: 'pilot', title: 'Pilot edition', status, opens: '2020-01-01', closes: '2099-12-31', paperWindow: 'Previous cycle' } };
  const snapshot = { edition: 'pilot', scoring: snapshotRules, updatedAt: papers.length ? '2026-10-24T12:00:00Z' : null, papers };
  const context = {
    document: { getElementById: id => nodes[id] ?? null, createElement: tag => new Node(tag), createTextNode: text => ({ textContent: text }), querySelectorAll: () => [] },
    URL, URLSearchParams, Date,
    FormData: class { entries() { return Object.entries(names).filter(([, id]) => !nodes[id].disabled).map(([name, id]) => [name, nodes[id].value]); } },
    navigator: { clipboard: { writeText: async () => {} } },
    fetch: async path => ({ ok: true, json: async () => path.endsWith('nominations.json') ? snapshot : config }),
  };
  new vm.Script(source).runInNewContext(context);
  await new Promise(resolve => setImmediate(resolve));
  return {
    nodes,
    submit() { nodes['nomination-form'].listeners.submit({ preventDefault() {} }); },
    change(id) { nodes[id].listeners.change(); },
  };
}

test('preview drafts use one freeform comment and never expose public posting', async () => {
  const app = await mount();
  app.nodes.recommendation.value = 'Strongly recommend (+5)';
  app.change('recommendation');
  app.submit();
  assert.match(app.nodes['draft-text'].value, /### Recommendation\n\nStrongly recommend \(\+5\)/);
  assert.match(app.nodes['draft-text'].value, /### Why do you believe this is a good paper\?/);
  assert.doesNotMatch(app.nodes['draft-text'].value, /### What have you read|### Caveat/);
  assert.equal(app.nodes['submit-github'].hidden, true);
  assert.equal(app.nodes['open-thread'].hidden, true);
});

test('both weights reject short Unicode comments and whitespace padding', async () => {
  for (const recommendation of ['Recommend (+1)', 'Strongly recommend (+5)']) {
    for (const reason of ['😀'.repeat(19), 'a' + ' '.repeat(40) + 'b']) {
      const app = await mount();
      app.nodes.recommendation.value = recommendation;
      app.nodes.reason.value = reason;
      app.submit();
      assert.match(app.nodes['form-status'].textContent, /at least 20 characters/);
      assert.equal(app.nodes['draft-text'].value, '');
    }
  }
  const app = await mount();
  app.nodes.reason.value = '😀'.repeat(20);
  app.submit();
  assert.match(app.nodes['form-status'].textContent, /Draft ready/);
});

test('conflicted recommendations cap at one when the endorsement weight changes', async () => {
  const app = await mount({ rules: { ...scoring, endorsement: 7, threshold: 28 } });
  app.nodes.recommendation.value = 'Strongly recommend (+7)';
  app.nodes.relationship.value = 'Author / coauthor';
  app.change('relationship');
  app.submit();
  assert.equal(app.nodes.recommendation.options[1].disabled, true);
  assert.equal(app.nodes.recommendation.value, 'Recommend (+1)');
  assert.match(app.nodes['draft-text'].value, /### Recommendation\n\nRecommend \(\+1\)/);
});

test('live GitHub handoff preserves the draft and avoids privileged label parameters', async () => {
  const app = await mount({ preview: false });
  app.submit();
  const target = new URL(app.nodes['submit-github'].href);
  assert.equal(target.origin, 'https://github.com');
  assert.equal(target.searchParams.get('body'), app.nodes['draft-text'].value);
  assert.equal(target.searchParams.has('labels'), false);
  assert.equal(app.nodes['submit-github'].hidden, false);
});

test('closed rounds prevent drafting and posting', async () => {
  const app = await mount({ preview: false, status: 'closed' });
  assert.equal(app.nodes['draft-button'].disabled, true);
  app.submit();
  assert.match(app.nodes['form-status'].textContent, /not open/);
  assert.equal(app.nodes['draft-text'].value, '');
});

test('a snapshot from different scoring rules shows no counts', async () => {
  const app = await mount({ snapshotRules: { ...scoring, endorsement: 2 } });
  assert.match(app.nodes.nominations.textContent, /could not be loaded/);
  assert.equal(app.nodes['nomination-tools'].hidden, true);
  assert.equal(app.nodes['snapshot-date'].textContent, 'Current nomination counts unavailable');
});

test('poll cards count endorsements independently of their weight and validate qualification', async () => {
  for (const rules of [scoring, { ...scoring, endorsement: 7, threshold: 28 }]) {
    const endorsements = Array.from({ length: 4 }, (_, index) => ({ login: `reader-${index}`, relationship: 'Independent reader', recommendation: `Strongly recommend (+${rules.endorsement})`, reason: 'A useful new way of thinking about this problem.', url: `https://github.com/flannseminars/flannseminars.github.io/issues/1#issuecomment-${index + 10}` }));
    const paper = { title: 'A nominated paper', authors: 'A. Researcher', topic: 'Theory', url: 'https://arxiv.org/abs/2401.01234', issueUrl: 'https://github.com/flannseminars/flannseminars.github.io/issues/1', score: rules.threshold, supporters: 4, strong: 4, eligible: true, endorsements };
    const app = await mount({ rules, papers: [paper] });
    assert.match(app.nodes.nominations.textContent, /4 strong endorsements/);
    assert.match(app.nodes.nominations.textContent, /Host checks pending/);
    const inconsistent = await mount({ rules, papers: [{ ...paper, score: rules.threshold - 1 }] });
    assert.match(inconsistent.nodes.nominations.textContent, /could not be loaded/);
    assert.equal(inconsistent.nodes['nomination-tools'].hidden, true);
  }
});
