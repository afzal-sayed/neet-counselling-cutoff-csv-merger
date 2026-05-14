// ── Constants ──────────────────────────────────────────────────────
const ROUND_META = [
  { key: 'round1', label: 'Round 1', subtitle: 'First Round' },
  { key: 'round2', label: 'Round 2', subtitle: 'Second Round' },
  { key: 'round3', label: 'Round 3', subtitle: 'Third Round' },
  { key: 'round4', label: 'Round 4', subtitle: 'Stray Vacancy' },
  { key: 'round5', label: 'Round 5', subtitle: 'Sp. Stray Vacancy' },
];

// ── State ──────────────────────────────────────────────────────────
let files = {};
let currentJobId = null;
let pollInterval = null;
let pendingMatches = [];
let matchDecisions = {};

// ── DOM Helpers ────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => $(id).classList.remove('hidden');
const hide = id => $(id).classList.add('hidden');

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'className') node.className = v;
    else if (k === 'textContent') node.textContent = v;
    else if (k.startsWith('data-')) node.dataset[k.slice(5)] = v;
    else node[k] = v;
  }
  children.forEach(c => node.appendChild(c));
  return node;
}

// ── Build Upload Cards ─────────────────────────────────────────────
function buildCards() {
  const grid = $('rounds-grid');
  grid.textContent = '';

  ROUND_META.forEach(({ key, label, subtitle }) => {
    const hiddenInput = el('input', { type: 'file', id: `input-${key}`, accept: '.xlsx,.xls,.csv' });
    hiddenInput.dataset.key = key;
    hiddenInput.style.display = 'none';

    const dropZone = el('div', { className: 'drop-zone' },
      [el('span', { textContent: 'Drop file here or ' }),
       el('u', { textContent: 'browse' })]);
    dropZone.dataset.key = key;

    const fname = el('span', { className: 'file-name' });
    fname.dataset.fname = key;
    const clearBtn = el('button', { className: 'clear-btn', textContent: '✕', title: 'Remove' });
    clearBtn.dataset.clear = key;
    const fileInfo = el('div', { className: 'file-info hidden' }, [fname, clearBtn]);
    fileInfo.dataset.info = key;

    const card = el('div', { className: 'round-card' }, [
      el('div', { className: 'card-label', textContent: `${label} — ${subtitle}` }),
      dropZone,
      fileInfo,
      hiddenInput,
    ]);
    card.dataset.key = key;
    grid.appendChild(card);
  });

  attachCardListeners();
}

function attachCardListeners() {
  ROUND_META.forEach(({ key }) => {
    const zone  = document.querySelector(`.drop-zone[data-key="${key}"]`);
    const input = $(`input-${key}`);
    const card  = document.querySelector(`.round-card[data-key="${key}"]`);

    zone.addEventListener('click', () => input.click());
    input.addEventListener('change', () => { if (input.files[0]) setFile(key, input.files[0]); });

    zone.addEventListener('dragover', e => { e.preventDefault(); card.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => card.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      card.classList.remove('drag-over');
      if (e.dataTransfer.files[0]) setFile(key, e.dataTransfer.files[0]);
    });

    document.querySelector(`.clear-btn[data-clear="${key}"]`)
      .addEventListener('click', () => clearFile(key));
  });
}

function setFile(key, file) {
  files[key] = file;
  const card = document.querySelector(`.round-card[data-key="${key}"]`);
  card.classList.add('has-file');
  document.querySelector(`[data-info="${key}"]`).classList.remove('hidden');
  document.querySelector(`[data-fname="${key}"]`).textContent =
    `${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
}

function clearFile(key) {
  delete files[key];
  document.querySelector(`.round-card[data-key="${key}"]`).classList.remove('has-file');
  document.querySelector(`[data-info="${key}"]`).classList.add('hidden');
  $(`input-${key}`).value = '';
}

// ── Theme Toggle ───────────────────────────────────────────────────
function initTheme() {
  const btn  = $('theme-toggle');
  const html = document.documentElement;
  const update = t => {
    html.dataset.theme = t;
    btn.textContent = t === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('theme', t);
  };
  const saved = localStorage.getItem('theme');
  if (saved) update(saved);
  btn.addEventListener('click', () =>
    update(html.dataset.theme === 'dark' ? 'light' : 'dark'));
}

// ── Missing Rounds Modal ───────────────────────────────────────────
function showMissingModal(missing, onConfirm) {
  $('modal-msg').textContent =
    `Missing: ${missing.join(', ')}. Results may be incomplete. Continue anyway?`;
  show('modal-overlay');
  $('modal-yes').onclick = () => { hide('modal-overlay'); onConfirm(); };
  $('modal-no').onclick  = () => hide('modal-overlay');
}

// ── Upload & Processing ────────────────────────────────────────────
async function startProcessing() {
  const uploaded = Object.keys(files);
  if (uploaded.length < 4) {
    const missing = ROUND_META.filter(r => !uploaded.includes(r.key)).map(r => r.label);
    showMissingModal(missing, doUpload);
    return;
  }
  doUpload();
}

async function doUpload() {
  hide('upload-section');
  show('progress-section');
  setProgress(0, 'Uploading files...');

  const form = new FormData();
  for (const [key, file] of Object.entries(files))
    form.append(key, file, file.name);

  const resp = await fetch('/process', { method: 'POST', body: form });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) { showError(body.error || 'Upload failed'); return; }
  currentJobId = body.job_id;
  pollInterval = setInterval(poll, 800);
}

async function poll() {
  const resp = await fetch(`/status/${currentJobId}`);
  if (!resp.ok) { showError('Status check failed'); return; }
  const data = await resp.json();
  setProgress(data.progress, data.stage);
  if (data.status === 'review') {
    clearInterval(pollInterval);
    pendingMatches = data.fuzzy_matches || [];
    showReview(pendingMatches);
  } else if (data.status === 'error') {
    clearInterval(pollInterval);
    showError(data.error || 'Processing failed');
  }
}

function setProgress(pct, stage) {
  $('progress-fill').style.width = `${pct}%`;
  $('progress-pct').textContent = `${pct}%`;
  $('stage-label').textContent = stage;
}

// ── Conflict Review ────────────────────────────────────────────────
function showReview(matches) {
  hide('progress-section');
  show('review-section');
  matchDecisions = {};

  const summary   = $('match-summary');
  const tbody     = $('match-tbody');
  const bulkBtns  = document.querySelector('.bulk-btns');
  const tableWrap = document.querySelector('.table-wrap');

  if (matches.length === 0) {
    summary.textContent = 'No fuzzy matches found. Click Confirm to generate output.';
    tbody.textContent = '';
    bulkBtns.style.display  = 'none';
    tableWrap.style.display = 'none';
    return;
  }

  summary.textContent =
    `${matches.length} fuzzy match${matches.length > 1 ? 'es' : ''} found. Review and approve before generating.`;
  bulkBtns.style.display  = '';
  tableWrap.style.display = '';
  tbody.textContent = '';

  matches.forEach((m, i) => {
    matchDecisions[i] = 'approve';

    const approveBtn = el('button', { textContent: '✓ Approve', className: 'active-approve' });
    approveBtn.dataset.idx    = i;
    approveBtn.dataset.action = 'approve';

    const rejectBtn = el('button', { textContent: '✗ Reject' });
    rejectBtn.dataset.idx    = i;
    rejectBtn.dataset.action = 'reject';

    const actionDiv = el('div', { className: 'action-toggle' }, [approveBtn, rejectBtn]);

    const tr = el('tr', {}, [
      el('td', { textContent: m.original }),
      el('td', { textContent: m.matched  }),
      el('td', { textContent: `${Number(m.score).toFixed(2)}%` }),
      el('td', { textContent: m.round   }),
      el('td', { textContent: m.state   }),
      el('td', {}, [actionDiv]),
    ]);
    tbody.appendChild(tr);
  });

  tbody.addEventListener('click', e => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const idx = +btn.dataset.idx;
    matchDecisions[idx] = btn.dataset.action;
    tbody.querySelectorAll(`button[data-idx="${idx}"]`).forEach(b => {
      b.classList.remove('active-approve', 'active-reject');
    });
    btn.classList.add(`active-${btn.dataset.action}`);
  });

  $('approve-all-btn').onclick = () => bulkDecision('approve', matches.length);
  $('reject-all-btn').onclick  = () => bulkDecision('reject',  matches.length);
}

function bulkDecision(action, count) {
  for (let i = 0; i < count; i++) matchDecisions[i] = action;
  document.querySelectorAll('.action-toggle button').forEach(btn => {
    btn.classList.remove('active-approve', 'active-reject');
    if (btn.dataset.action === action) btn.classList.add(`active-${action}`);
  });
}

// ── Finalize ───────────────────────────────────────────────────────
async function finalize() {
  hide('review-section');
  show('progress-section');
  setProgress(50, 'Generating final output...');

  const confirmed = pendingMatches
    .map((m, i) => matchDecisions[i] === 'approve'
      ? { original: m.original, canonical: m.matched }
      : null)
    .filter(Boolean);

  const resp = await fetch(`/finalize/${currentJobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed_matches: confirmed }),
  });
  if (!resp.ok) { showError('Finalize failed'); return; }

  hide('progress-section');
  show('download-section');
}

// ── Download ───────────────────────────────────────────────────────
function triggerDownload(format) {
  const a = document.createElement('a');
  a.href = `/download/${currentJobId}?format=${format}`;
  a.download = `neet_pg_2025_all_rounds.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ── Error ──────────────────────────────────────────────────────────
function showError(msg) {
  hide('progress-section');
  hide('review-section');
  $('error-msg').textContent = msg;
  show('error-section');
}

// ── Reset ──────────────────────────────────────────────────────────
function resetUI() {
  files = {};
  currentJobId = null;
  pendingMatches = [];
  matchDecisions = {};
  clearInterval(pollInterval);
  buildCards();
  ['progress-section', 'review-section', 'download-section', 'error-section'].forEach(hide);
  show('upload-section');
}

// ── Init ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  buildCards();
  $('generate-btn').addEventListener('click', startProcessing);
  $('confirm-btn').addEventListener('click', finalize);
  $('download-csv').addEventListener('click', () => triggerDownload('csv'));
  $('download-xlsx').addEventListener('click', () => triggerDownload('xlsx'));
  $('home-btn').addEventListener('click', resetUI);
  $('retry-btn').addEventListener('click', resetUI);
});
