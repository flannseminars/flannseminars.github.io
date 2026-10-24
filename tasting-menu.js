/* Public contributions are posted on GitHub by their authors. No votes live in localStorage. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const form = $('nomination-form');
  let config;
  let papers = [];
  let supporting = null;
  let draft = '';
  const repositoryPattern = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
  const relationships = ['Independent reader', 'Author / coauthor', 'Other conflict of interest'];
  const base = 'Recommend (+1)';
  const strong = 'Strongly recommend (+2)';

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function safeURL(value) {
    try {
      const url = new URL(value);
      const host = url.hostname.toLowerCase().replace(/\.$/, '');
      const local = !host.includes('.') || /\.(local|localhost|internal|test|invalid|example)$/.test(host);
      const privateIPv4 = /^(0|10|127)\./.test(host) || /^169\.254\./.test(host) || /^192\.168\./.test(host) || /^172\.(1[6-9]|2\d|3[01])\./.test(host);
      return url.protocol === 'https:' && !url.username && !url.password && !url.port && !local && !privateIPv4 && !/[\s\\]/.test(value) ? url.href : null;
    } catch (_) { return null; }
  }

  function repoURL(path) { return `https://github.com/${config.repository}/${path}`; }
  function discussionURL(value) {
    const safe = safeURL(value);
    if (!safe) return null;
    const url = new URL(safe);
    return url.origin === 'https://github.com' && url.pathname.startsWith(`/${config.repository}/issues/`) ? safe : null;
  }

  function externalLink(url, label, className) {
    const a = element('a', label, className);
    a.href = url;
    return a;
  }

  function roundOpen() {
    if (!config || config.preview || config.edition.status !== 'open') return false;
    const now = Date.now();
    const opens = Date.parse(config.edition.opens);
    let closes = Date.parse(config.edition.closes);
    if (/^\d{4}-\d{2}-\d{2}$/.test(config.edition.closes || '')) closes += 86400000 - 1;
    return Number.isFinite(opens) && Number.isFinite(closes) && now >= opens && now <= closes;
  }

  function dateLabel(date) {
    return new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  }

  function deadlineLabel(value) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${dateLabel(value)}, 23:59 UTC`;
    return new Date(value).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC';
  }

  function renderBoard() {
    const query = $('paper-search').value.trim().toLowerCase();
    const filter = $('paper-filter').value;
    const filtered = papers.filter(paper => `${paper.title} ${paper.authors} ${paper.topic}`.toLowerCase().includes(query) && (filter === 'all' || (filter === 'eligible' ? paper.eligible : !paper.eligible)));
    const board = $('nominations');
    board.replaceChildren();
    $('nomination-tools').hidden = !papers.length;
    if (!filtered.length) {
      const empty = element('div', undefined, 'tm-empty');
      empty.append(element('strong', papers.length ? 'No papers match this view.' : 'The first table is still being set.'));
      empty.append(element('p', papers.length ? 'Try another title, author, or filter.' : config.preview ? 'No community nominations have been collected for this preview.' : 'No nominations in the latest published snapshot. New contributions appear after the next organizer update.'));
      if (!papers.length) empty.append(externalLink('#nominate', config.preview ? 'Try the nomination draft →' : 'Prepare a nomination →', 'tm-text-link'));
      board.append(empty);
      return;
    }
    for (const paper of filtered) {
      const article = element('article', undefined, 'tm-nomination');
      const title = element('h3');
      const paperURL = safeURL(paper.url);
      title.append(paperURL ? externalLink(paperURL, paper.title) : element('span', paper.title));
      article.append(title, element('p', `${paper.authors} · ${paper.topic}`, 'tm-note'));
      const stats = element('div', undefined, 'tm-stats');
      stats.append(element('span', `${paper.supporters} ${paper.supporters === 1 ? 'reader' : 'readers'}`), element('span', `${paper.strong} strong ${paper.strong === 1 ? 'recommendation' : 'recommendations'}`), element('span', `${paper.score} ${paper.score === 1 ? 'point' : 'points'}`), element('span', paper.eligible ? 'Ready for editorial review' : 'Gathering independent support'));
      article.append(stats);
      const details = element('details');
      details.append(element('summary', 'Read the recommendations'));
      const quotes = element('div', undefined, 'tm-quotes');
      for (const endorsement of paper.endorsements) {
        const quote = element('blockquote');
        quote.append(element('p', endorsement.reason));
        const cite = element('cite', `${endorsement.login} · ${endorsement.relationship} · ${endorsement.recommendation}`);
        const original = discussionURL(endorsement.url);
        if (original) cite.append(document.createTextNode(' · '), externalLink(original, 'Original'));
        quote.append(cite);
        if (endorsement.checked) quote.append(element('p', `Read or checked: ${endorsement.checked}`, 'tm-note'));
        if (endorsement.caveat) quote.append(element('p', `Caveat: ${endorsement.caveat}`, 'tm-note'));
        quotes.append(quote);
      }
      details.append(quotes);
      article.append(details);
      const actions = element('div', undefined, 'tm-actions');
      const thread = discussionURL(paper.issueUrl);
      if (thread) {
        actions.append(externalLink(thread, 'Public discussion ↗', 'tm-text-link'));
        if (roundOpen()) {
          const button = element('button', 'Add your recommendation →', 'tm-button secondary');
          button.type = 'button';
          button.addEventListener('click', () => supportPaper(paper));
          actions.append(button);
        }
      }
      article.append(actions);
      board.append(article);
    }
  }

  function setMode(paper) {
    supporting = paper;
    const ids = ['paper-title', 'paper-url', 'paper-authors', 'paper-published', 'paper-topic'];
    ids.forEach(id => {
      $(id).closest('.tm-field').hidden = Boolean(paper);
      $(id).disabled = Boolean(paper);
    });
    $('form-mode').textContent = paper ? `Recommending: ${paper.title}` : config.preview ? 'Try the nomination draft' : config.edition.title;
    $('draft-button').textContent = paper ? 'Preview recommendation →' : 'Preview nomination →';
    $('draft-panel').hidden = true;
    $('form-status').textContent = '';
  }

  function supportPaper(paper) {
    setMode(paper);
    $('nominate').scrollIntoView({ behavior: 'smooth', block: 'start' });
    $('relationship').focus({ preventScroll: true });
  }

  function updateWeight() {
    const independent = $('relationship').value === relationships[0];
    $('recommendation').options[1].disabled = !independent;
    if (!independent) $('recommendation').value = base;
    const isStrong = independent && $('recommendation').value === strong;
    $('reason').minLength = isStrong ? 120 : 1;
    $('checked').required = isStrong;
    $('checked').minLength = isStrong ? 60 : 0;
    $('caveat').required = isStrong;
    $('caveat').minLength = isStrong ? 40 : 0;
    $('weight-note').textContent = !independent ? 'Authors, coauthors, and other conflicts count as +1 at most and cannot satisfy independent-support requirements.' : isStrong ? 'For +2: at least 120 characters on why, 60 on what you checked, and 40 on a caveat.' : 'A +1 needs a reason. A strong +2 needs all three notes below.';
    $('draft-panel').hidden = true;
  }

  // Keep user-entered headings from impersonating the structured fields below.
  function markdownValue(value) { return String(value).trim().replace(/^#{1,6}\s/gm, match => `\\${match}`); }
  function section(title, value) { return `### ${title}\n\n${markdownValue(value || '_No response_')}\n\n`; }

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!config) return;
    if (!config.preview && !roundOpen()) {
      $('form-status').textContent = 'This round is not open. The organizers will announce the next nomination window.';
      $('draft-panel').hidden = true;
      return;
    }
    const values = Object.fromEntries(new FormData(form).entries());
    if (!supporting && !safeURL(values.url)) {
      $('form-status').textContent = 'Please use a public HTTPS paper link.';
      $('paper-url').focus();
      return;
    }
    // Whitespace and placeholders are checked again by the importer.
    if (!values.reason.trim() || (values.recommendation === strong && [Array.from(values.reason.trim()).length < 120, Array.from(values.checked.trim()).length < 60, Array.from(values.caveat.trim()).length < 40].some(Boolean))) {
      $('form-status').textContent = 'Please complete the recommendation notes. A strong recommendation needs 120 / 60 / 40 characters in the three fields.';
      return;
    }
    draft = '<!-- flann-tasting-menu -->\n\nI understand this contribution is public and may be quoted by FLaNN with attribution.\n\n';
    if (!supporting) {
      draft += section('Edition', config.edition.id) + section('Paper title', values.title) + section('Paper URL', values.url) + section('Authors', values.authors) + section('Published', values.published) + section('Topic', values.topic);
    }
    draft += section('Relationship', values.relationship) + section('Recommendation', values.recommendation) + section('Why read it?', values.reason) + section('What have you read or checked?', values.checked) + section('Caveat or limitation', values.caveat);
    $('draft-text').value = draft;
    $('draft-panel').hidden = false;
    $('submit-github').hidden = true;
    $('open-thread').hidden = true;
    $('reset-mode').hidden = !supporting;
    $('form-status').textContent = 'Draft ready. Nothing has been submitted or counted.';
    if (config.preview) {
      $('draft-help').textContent = 'Preview only: copy or review this draft. Public posting will be enabled when the pilot opens.';
    } else if (supporting) {
      $('draft-help').textContent = 'Copy this draft, open the paper’s public discussion, and paste it as a new comment. Posting on GitHub is a separate step and requires a GitHub account.';
      $('open-thread').href = discussionURL(supporting.issueUrl);
      $('open-thread').hidden = false;
    } else {
      const params = new URLSearchParams({ title: `[Tasting Menu] ${values.title}`, body: draft });
      let url = repoURL('issues/new') + '?' + params;
      const longDraft = url.length > 7500;
      if (longDraft) url = repoURL('issues/new') + '?' + new URLSearchParams({ title: `[Tasting Menu] ${values.title}` });
      $('submit-github').href = url;
      $('submit-github').hidden = false;
      $('draft-help').textContent = longDraft ? 'This draft is long: copy it, then paste it into the GitHub issue body. Review and submit there with your GitHub account.' : 'Review the prefilled issue on GitHub, then submit it with your GitHub account. An organizer checks its label and eligibility before the next website snapshot.';
    }
    $('draft-panel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  $('copy-draft').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(draft);
      $('form-status').textContent = 'Draft copied. Nothing has been submitted.';
    } catch (_) {
      $('draft-text').focus();
      $('draft-text').select();
      $('form-status').textContent = 'Select and copy the draft above. Automatic clipboard access is unavailable.';
    }
  });
  $('reset-mode').addEventListener('click', () => setMode(null));
  $('relationship').addEventListener('change', updateWeight);
  $('recommendation').addEventListener('change', updateWeight);
  form.addEventListener('input', event => {
    if (event.target.id !== 'draft-text') {
      $('draft-panel').hidden = true;
      $('form-status').textContent = '';
    }
  });
  $('paper-search').addEventListener('input', renderBoard);
  $('paper-filter').addEventListener('change', renderBoard);

  async function readJSON(path) {
    const response = await fetch(path, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Unable to load ${path}`);
    return response.json();
  }

  async function init() {
    $('draft-button').disabled = true;
    try {
      config = await readJSON('data/tasting-menu.json');
      if (!repositoryPattern.test(config.repository) || typeof config.preview !== 'boolean' || !config.edition) throw new Error('Invalid round configuration');
      if (!config.preview) {
        $('preview-notice').hidden = true;
        $('edition-label').textContent = config.edition.title;
        $('form-mode').textContent = config.edition.title;
        $('form-explanation').textContent = roundOpen() ? `Nominations are open until ${deadlineLabel(config.edition.closes)}. Paper window: ${config.edition.paperWindow}. Prepare a draft here, then review and post it on GitHub. A GitHub account is required.` : 'This round is not open for submissions. The organizers will announce the next nomination window.';
      }
      $('draft-button').disabled = !config.preview && !roundOpen();
      updateWeight();
      const snapshot = await readJSON('data/tasting-menu-nominations.json');
      if (snapshot.edition !== config.edition.id || !Array.isArray(snapshot.papers)) throw new Error('Nomination snapshot is for a different edition');
      papers = snapshot.papers;
      $('snapshot-date').textContent = snapshot.updatedAt ? `Snapshot: ${dateLabel(snapshot.updatedAt)} · ${config.edition.title}` : config.preview ? 'Pilot round · not open yet' : `${config.edition.title} · awaiting first snapshot`;
      renderBoard();
    } catch (error) {
      const board = $('nominations');
      board.replaceChildren();
      const empty = element('div', undefined, 'tm-empty');
      empty.append(element('strong', 'The nomination board could not be loaded.'), element('p', 'Please refresh, or read the public discussion on GitHub. No counts are shown until the current snapshot is available.'));
      empty.append(externalLink('https://github.com/flannseminars/flannseminars.github.io/issues?q=is%3Aissue+label%3Atasting-menu', 'Read public nominations ↗', 'tm-text-link'));
      board.append(empty);
      if (!config) $('form-status').textContent = 'The round configuration is unavailable. Please refresh before preparing a draft.';
    }
  }
  init();
})();
