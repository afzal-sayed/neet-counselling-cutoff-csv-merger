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
const hide = id => $(id).classList.add('hidden');
function show(id) {
  const node = $(id);
  node.classList.remove('hidden');
  node.classList.remove('section-enter');
  void node.offsetWidth;
  node.classList.add('section-enter');
}
function setStep(n) {
  document.querySelectorAll('.step').forEach(s => {
    const num = +s.dataset.step;
    s.classList.toggle('active', num === n);
    s.classList.toggle('done', num < n);
  });
  document.querySelectorAll('.step-track').forEach((t, i) => {
    t.classList.toggle('done', i + 1 < n);
  });
}

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
    const zone = document.querySelector(`.drop-zone[data-key="${key}"]`);
    const input = $(`input-${key}`);
    const card = document.querySelector(`.round-card[data-key="${key}"]`);

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
  const btn = $('theme-toggle');
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
  $('modal-no').onclick = () => hide('modal-overlay');
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
  setStep(2);
  hide('progress-section');
  show('review-section');
  matchDecisions = {};

  const summary = $('match-summary');
  const tbody = $('match-tbody');
  const bulkBtns = document.querySelector('.bulk-btns');
  const tableWrap = document.querySelector('.table-wrap');

  if (matches.length === 0) {
    summary.textContent = 'No fuzzy matches found. Click Confirm to generate output.';
    tbody.textContent = '';
    bulkBtns.style.display = 'none';
    tableWrap.style.display = 'none';
    return;
  }

  const conflictCount = matches.reduce((n, m) => n + m.courses.filter(c => c.conflict).length, 0);
  summary.textContent =
    `${matches.length} institute match${matches.length !== 1 ? 'es' : ''} for review` +
    (conflictCount ? ` | ${conflictCount} same-round conflict${conflictCount !== 1 ? 's' : ''} ⚠️` : '') +
    '. Expand groups to review courses, then confirm.';
  bulkBtns.style.display = '';
  tableWrap.style.display = '';
  tbody.textContent = '';

  matches.forEach(m => {
    matchDecisions[m.original] = { groupApproved: true, courseOverrides: {} };
    const hasConflict = m.courses.some(c => c.conflict);

    // ── Group header row ──
    const expandCell = el('td', { className: 'expand-cell', textContent: hasConflict ? '▼' : '▶' });

    const nameCell = el('td', { colSpan: 1 }, [
      el('span', { className: 'original-name', textContent: m.original }),
      el('span', { className: 'arrow-sep', textContent: ' → ' }),
      el('span', { className: 'canonical-name', textContent: m.matched }),
      ...(hasConflict ? [el('span', { className: 'conflict-badge', textContent: ' ⚠️' })] : []),
    ]);

    const variantRounds = [...new Set(m.courses.flatMap(c => c.rounds))].sort();
    const canonicalRoundsLabel = m.canonical_rounds && m.canonical_rounds.length
      ? `  |  canonical: ${m.canonical_rounds.join(', ')}`
      : '';
    const metaCell = el('td', { className: 'meta-cell',
      textContent: `${m.score.toFixed(1)}%  |  ${m.state}  |  ${m.courses.length} course${m.courses.length !== 1 ? 's' : ''}  |  variant: ${variantRounds.join(', ')}${canonicalRoundsLabel}` });

    const approveAllBtn = el('button', { textContent: '✓ Approve All', className: 'active-approve' });
    const rejectAllBtn  = el('button', { textContent: '✗ Reject All' });
    const actionCell = el('td', {}, [el('div', { className: 'action-toggle' }, [approveAllBtn, rejectAllBtn])]);

    const headerRow = el('tr', { className: 'match-group-header' + (hasConflict ? ' has-conflict' : '') },
      [expandCell, nameCell, metaCell, el('td'), actionCell]);

    // ── Course detail rows ──
    const detailRows = m.courses.map(c => {
      const courseLabel = el('td', { className: 'course-cell' + (c.conflict ? ' conflict-course' : '') }, [
        ...(c.conflict ? [el('span', { textContent: '⚠️ ' })] : []),
        el('span', { textContent: c.name }),
      ]);

      const badgeCell = el('td', { className: 'round-cell' },
        c.rounds.map(r => el('span', { className: 'round-badge', textContent: r })));

      const cApproveBtn = el('button', {
        textContent: c.conflict ? '✓ Merge' : '✓ Approve',
        className: 'active-approve course-action-btn',
      });
      cApproveBtn.dataset.course = c.name;
      cApproveBtn.dataset.action = 'approve';

      const cRejectBtn = el('button', {
        textContent: c.conflict ? '✗ Keep Both' : '✗ Reject',
        className: 'course-action-btn',
      });
      cRejectBtn.dataset.course = c.name;
      cRejectBtn.dataset.action = 'reject';

      const courseActionCell = el('td', {}, [el('div', { className: 'action-toggle' }, [cApproveBtn, cRejectBtn])]);

      const tr = el('tr', { className: 'course-row' + (c.conflict ? ' conflict-row' : '') },
        [el('td'), courseLabel, badgeCell, el('td'), courseActionCell]);

      tr.addEventListener('click', e => {
        const btn = e.target.closest('.course-action-btn');
        if (!btn) return;
        const action = btn.dataset.action;
        const courseName = btn.dataset.course;
        const groupDefault = matchDecisions[m.original].groupApproved;
        const [aBtn, rBtn] = tr.querySelectorAll('.course-action-btn');
        if (action === 'approve') {
          aBtn.classList.add('active-approve'); rBtn.classList.remove('active-reject');
          if (groupDefault) delete matchDecisions[m.original].courseOverrides[courseName];
          else matchDecisions[m.original].courseOverrides[courseName] = true;
        } else {
          rBtn.classList.add('active-reject'); aBtn.classList.remove('active-approve');
          if (!groupDefault) delete matchDecisions[m.original].courseOverrides[courseName];
          else matchDecisions[m.original].courseOverrides[courseName] = false;
        }
      });

      return tr;
    });

    // Start expanded only when there's a conflict
    detailRows.forEach(tr => { tr.style.display = hasConflict ? '' : 'none'; });

    // Expand/collapse on header click
    headerRow.addEventListener('click', e => {
      if (e.target.closest('button')) return;
      const expanded = detailRows[0]?.style.display !== 'none';
      detailRows.forEach(tr => { tr.style.display = expanded ? 'none' : ''; });
      expandCell.textContent = expanded ? '▶' : '▼';
    });

    // Approve All / Reject All for the group
    approveAllBtn.addEventListener('click', e => {
      e.stopPropagation();
      matchDecisions[m.original].groupApproved = true;
      matchDecisions[m.original].courseOverrides = {};
      approveAllBtn.classList.add('active-approve'); rejectAllBtn.classList.remove('active-reject');
      detailRows.forEach(tr => {
        tr.querySelectorAll('.course-action-btn[data-action="approve"]').forEach(b => b.classList.add('active-approve'));
        tr.querySelectorAll('.course-action-btn[data-action="reject"]').forEach(b => b.classList.remove('active-reject'));
      });
    });

    rejectAllBtn.addEventListener('click', e => {
      e.stopPropagation();
      matchDecisions[m.original].groupApproved = false;
      matchDecisions[m.original].courseOverrides = {};
      rejectAllBtn.classList.add('active-reject'); approveAllBtn.classList.remove('active-approve');
      detailRows.forEach(tr => {
        tr.querySelectorAll('.course-action-btn[data-action="reject"]').forEach(b => b.classList.add('active-reject'));
        tr.querySelectorAll('.course-action-btn[data-action="approve"]').forEach(b => b.classList.remove('active-approve'));
      });
    });

    tbody.appendChild(headerRow);
    detailRows.forEach(tr => tbody.appendChild(tr));
  });

  $('approve-all-btn').onclick = () => {
    pendingMatches.forEach(m => {
      matchDecisions[m.original].groupApproved = true;
      matchDecisions[m.original].courseOverrides = {};
    });
    document.querySelectorAll('.match-group-header button:first-child').forEach(b => b.classList.add('active-approve'));
    document.querySelectorAll('.match-group-header button:last-child').forEach(b => b.classList.remove('active-reject'));
    document.querySelectorAll('.course-action-btn[data-action="approve"]').forEach(b => b.classList.add('active-approve'));
    document.querySelectorAll('.course-action-btn[data-action="reject"]').forEach(b => b.classList.remove('active-reject'));
  };

  $('reject-all-btn').onclick = () => {
    pendingMatches.forEach(m => {
      matchDecisions[m.original].groupApproved = false;
      matchDecisions[m.original].courseOverrides = {};
    });
    document.querySelectorAll('.match-group-header button:last-child').forEach(b => b.classList.add('active-reject'));
    document.querySelectorAll('.match-group-header button:first-child').forEach(b => b.classList.remove('active-approve'));
    document.querySelectorAll('.course-action-btn[data-action="reject"]').forEach(b => b.classList.add('active-reject'));
    document.querySelectorAll('.course-action-btn[data-action="approve"]').forEach(b => b.classList.remove('active-approve'));
  };
}

// ── Finalize ───────────────────────────────────────────────────────
async function finalize() {
  hide('review-section');
  show('progress-section');
  setProgress(50, 'Generating final output...');

  const decisions = [];
  pendingMatches.forEach(m => {
    const dec = matchDecisions[m.original];
    decisions.push({ original: m.original, approved: dec.groupApproved });
    for (const [course, approved] of Object.entries(dec.courseOverrides)) {
      decisions.push({ original: m.original, course, approved });
    }
  });

  const resp = await fetch(`/finalize/${currentJobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decisions }),
  });
  if (!resp.ok) { showError('Finalize failed'); return; }

  setStep(3);
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
  setStep(1);
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
