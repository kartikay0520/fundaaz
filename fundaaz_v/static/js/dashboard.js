// ══════════════════════════════════════
//  FUNDAAZ – dashboard.js  (v4 final)
// ══════════════════════════════════════

// ── Mobile sidebar ──
const sidebar   = document.querySelector('.sidebar');
const overlay   = document.querySelector('.sidebar-overlay');
const hamburger = document.querySelector('.hamburger');

function openSidebar() {
  sidebar && sidebar.classList.add('open');
  overlay && overlay.classList.add('open');
  hamburger && hamburger.classList.add('open');
  // Do NOT set body overflow:hidden — breaks Android scroll
}
function closeSidebar() {
  sidebar && sidebar.classList.remove('open');
  overlay && overlay.classList.remove('open');
  hamburger && hamburger.classList.remove('open');
}

hamburger && hamburger.addEventListener('click', () =>
  sidebar && sidebar.classList.contains('open') ? closeSidebar() : openSidebar()
);
overlay && overlay.addEventListener('click', closeSidebar);

let touchStartX = 0;
document.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, { passive: true });
document.addEventListener('touchend', e => {
  if (e.changedTouches[0].clientX - touchStartX < -60 &&
      sidebar && sidebar.classList.contains('open')) closeSidebar();
}, { passive: true });

// ── Tab switching ──
function switchTab(name) {
  document.querySelectorAll('.tab-page').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const page = document.getElementById('tab-' + name);
  if (page) page.style.display = 'block';
  document.querySelectorAll('.nav-item').forEach(n => {
    if ((n.getAttribute('onclick') || '').includes("'" + name + "'"))
      n.classList.add('active');
  });
  closeSidebar();
  if (name === 'performance' && typeof loadCharts === 'function') loadCharts('all');
}

// ── Table filter ──
function filterTable(input, tbodyId) {
  const q      = input.value.toLowerCase();
  const tbody  = document.getElementById(tbodyId);
  if (tbody) {
    Array.from(tbody.rows).forEach(row =>
      row.style.display = row.innerText.toLowerCase().includes(q) ? '' : 'none'
    );
  }
  const container = input.closest('.table-card');
  if (container) {
    container.querySelectorAll('.card-row').forEach(card =>
      card.style.display = card.innerText.toLowerCase().includes(q) ? '' : 'none'
    );
  }
}

// ── Edit student modal ──
function openEdit(id, name, cls, batch, subjects, parent, contact) {
  document.getElementById('edit-form').action = '/admin/students/edit/' + id;
  document.getElementById('e-name').value     = name;
  document.getElementById('e-class').value    = cls;
  document.getElementById('e-batch').value    = batch;
  document.getElementById('e-subjects').value = subjects;
  document.getElementById('e-parent').value   = parent;
  document.getElementById('e-contact').value  = contact;
  document.getElementById('edit-modal').style.display = 'flex';
}
function closeModal() {
  const m = document.getElementById('edit-modal');
  if (m) m.style.display = 'none';
}

// ── Edit test modal ──
function openEditTest(id, code, subject, marks, cls, batch, dt, chapter, topic) {
  document.getElementById('edit-test-form').action = '/admin/tests/edit/' + id;
  document.getElementById('et-code').value    = code;
  document.getElementById('et-subject').value = subject;
  document.getElementById('et-marks').value   = marks;
  document.getElementById('et-class').value   = cls;
  document.getElementById('et-batch').value   = batch;
  document.getElementById('et-date').value    = dt;
  document.getElementById('et-chapter').value = chapter || '';
  // Pre-load existing topics as chips
  loadChips(topic || '', 'edit-chip-wrap', 'edit-topic-input', 'et-topic');
  document.getElementById('edit-test-modal').style.display = 'flex';
}
function closeTestModal() {
  const m = document.getElementById('edit-test-modal');
  if (m) m.style.display = 'none';
}

// Close modals on backdrop click
document.addEventListener('click', e => {
  const sm = document.getElementById('edit-modal');
  if (sm && e.target === sm) closeModal();
  const tm = document.getElementById('edit-test-modal');
  if (tm && e.target === tm) closeTestModal();
});

// ── Quick progress jump ──
function quickProgress(loginId) {
  window.location.href = '/admin/student-progress?q=' + encodeURIComponent(loginId);
}

// ── Auto-dismiss toast ──
document.addEventListener('DOMContentLoaded', () => {
  const banner = document.querySelector('.toast-banner');
  if (banner) {
    setTimeout(() => {
      banner.style.transition = 'opacity .4s';
      banner.style.opacity    = '0';
      setTimeout(() => banner.remove(), 400);
    }, 4000);
  }
});

// ══════════════════════════════════════
//  TOPIC CHIP / TAG INPUT SYSTEM
// ══════════════════════════════════════

// Initialise a chip input widget
// wrapId   = id of .chip-input-wrap div
// inputId  = id of the text <input> inside it
// hiddenId = id of the hidden <input> that stores CSV value for form submit
function initChipInput(wrapId, inputId, hiddenId) {
  const wrap   = document.getElementById(wrapId);
  const input  = document.getElementById(inputId);
  const hidden = document.getElementById(hiddenId);
  if (!wrap || !input || !hidden) return;

  // Click anywhere in wrap → focus text input
  wrap.addEventListener('click', () => input.focus());

  input.addEventListener('keydown', e => {
    // Add chip on Enter or comma
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addChip(input.value.trim().replace(/,$/, ''), wrap, input, hidden);
    }
    // Remove last chip on Backspace if input is empty
    if (e.key === 'Backspace' && input.value === '') {
      const chips = wrap.querySelectorAll('.chip');
      if (chips.length) chips[chips.length - 1].remove();
      syncHidden(wrap, hidden);
    }
  });

  // Also add chip when input loses focus (user clicks away)
  input.addEventListener('blur', () => {
    if (input.value.trim()) {
      addChip(input.value.trim(), wrap, input, hidden);
    }
  });
}

function addChip(text, wrap, input, hidden) {
  if (!text) return;
  // Avoid duplicates (case-insensitive)
  const existing = Array.from(wrap.querySelectorAll('.chip'))
    .map(c => c.dataset.value.toLowerCase());
  if (existing.includes(text.toLowerCase())) {
    input.value = '';
    return;
  }
  const chip = document.createElement('span');
  chip.className   = 'chip';
  chip.dataset.value = text;
  chip.innerHTML   = `${text} <button type="button" class="chip-remove" aria-label="Remove ${text}">×</button>`;
  chip.querySelector('.chip-remove').addEventListener('click', () => {
    chip.remove();
    syncHidden(wrap, hidden);
  });
  // Insert chip before the text input
  wrap.insertBefore(chip, input);
  input.value = '';
  syncHidden(wrap, hidden);
}

function syncHidden(wrap, hidden) {
  const vals = Array.from(wrap.querySelectorAll('.chip')).map(c => c.dataset.value);
  hidden.value = vals.join(', ');
}

// Pre-populate chips from an existing comma-separated value string
function loadChips(value, wrapId, inputId, hiddenId) {
  const wrap  = document.getElementById(wrapId);
  const input = document.getElementById(inputId);
  const hidden = document.getElementById(hiddenId);
  if (!wrap || !input || !hidden) return;
  // Clear existing chips
  wrap.querySelectorAll('.chip').forEach(c => c.remove());
  if (!value || !value.trim()) return;
  value.split(',').map(v => v.trim()).filter(Boolean).forEach(v => {
    addChip(v, wrap, input, hidden);
  });
}

// Init on page load
document.addEventListener('DOMContentLoaded', () => {
  initChipInput('create-chip-wrap', 'create-topic-input', 'create-topic-hidden');
  initChipInput('edit-chip-wrap',   'edit-topic-input',   'et-topic');
});


// ══════════════════════════════════════
//  ALL RESULTS TAB — FILTER ENGINE
// ══════════════════════════════════════

function arApply() {
  const studentId = document.getElementById('ar-student')?.value  || '';
  const cls       = document.getElementById('ar-class')?.value    || '';
  const batch     = document.getElementById('ar-batch')?.value    || '';
  const subject   = document.getElementById('ar-subject')?.value  || '';
  const testCode  = document.getElementById('ar-testcode')?.value || '';
  const dateFrom  = document.getElementById('ar-date-from')?.value || '';
  const dateTo    = document.getElementById('ar-date-to')?.value   || '';
  const pctMin    = document.getElementById('ar-pct-min')?.value;
  const pctMax    = document.getElementById('ar-pct-max')?.value;

  let visible = 0;

  // Desktop rows
  document.querySelectorAll('#ar-tbody tr[data-pct]').forEach(row => {
    const show = arMatch(row, studentId, cls, batch, subject, testCode, dateFrom, dateTo, pctMin, pctMax);
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });

  // Mobile cards
  document.querySelectorAll('.card-table .card-row[data-pct]').forEach(card => {
    const show = arMatch(card, studentId, cls, batch, subject, testCode, dateFrom, dateTo, pctMin, pctMax);
    card.style.display = show ? '' : 'none';
  });

  // Update count
  const total   = document.querySelectorAll('#ar-tbody tr[data-pct]').length;
  const countEl = document.getElementById('ar-count');
  const headEl  = document.getElementById('ar-heading-count');
  const emptyEl = document.getElementById('ar-empty');

  if (countEl) countEl.textContent = total ? `Showing ${visible} of ${total}` : '';
  if (headEl)  headEl.textContent  = total ? `(${visible} of ${total})` : '';
  if (emptyEl) emptyEl.style.display = (visible === 0 && total > 0) ? 'block' : 'none';
}

function arMatch(el, studentId, cls, batch, subject, testCode, dateFrom, dateTo, pctMin, pctMax) {
  if (studentId && el.dataset.studentId !== studentId) return false;
  if (cls       && el.dataset.class     !== cls)       return false;
  if (batch     && el.dataset.batch     !== batch)     return false;
  if (subject   && el.dataset.subject   !== subject)   return false;
  if (testCode  && el.dataset.testcode  !== testCode)  return false;
  if (dateFrom  && el.dataset.date      <  dateFrom)   return false;
  if (dateTo    && el.dataset.date      >  dateTo)     return false;
  const pct = parseFloat(el.dataset.pct) || 0;
  if (pctMin !== '' && pctMin !== undefined && pct < parseFloat(pctMin)) return false;
  if (pctMax !== '' && pctMax !== undefined && pct > parseFloat(pctMax)) return false;
  return true;
}

function arQuick(type) {
  // Reset % fields
  const pMin = document.getElementById('ar-pct-min');
  const pMax = document.getElementById('ar-pct-max');
  if (pMin) pMin.value = '';
  if (pMax) pMax.value = '';

  // Set range by category
  const ranges = {
    top:     [90,  100],
    above:   [75,  89.9],
    average: [50,  74.9],
    poor:    [33,  49.9],
    fail:    [0,   32.9],
    all:     [null, null],
  };
  const [lo, hi] = ranges[type] || [null, null];
  if (lo !== null && pMin) pMin.value = lo;
  if (hi !== null && pMax) pMax.value = hi;

  // Update button active states
  ['all','top','above','average','poor','fail'].forEach(id => {
    const btn = document.getElementById('ar-qf-' + id);
    if (btn) btn.classList.toggle('active', id === type);
  });

  arApply();
}

function arClearAll() {
  ['ar-student','ar-class','ar-batch','ar-subject','ar-testcode'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['ar-date-from','ar-date-to','ar-pct-min','ar-pct-max'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['all','top','above','average','poor','fail'].forEach(id => {
    const btn = document.getElementById('ar-qf-' + id);
    if (btn) btn.classList.toggle('active', id === 'all');
  });
  arApply();
}

// Auto-init count when tab is visible
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    const rows   = document.querySelectorAll('#ar-tbody tr[data-pct]');
    const headEl = document.getElementById('ar-heading-count');
    if (headEl && rows.length) headEl.textContent = `(${rows.length} total)`;
    const countEl = document.getElementById('ar-count');
    if (countEl && rows.length) countEl.textContent = `${rows.length} total results`;
  }, 150);
});

// ══════════════════════════════════════
//  NOTICE BOARD
// ══════════════════════════════════════

// Notice type config
const NB_CONFIG = {
  text:  { icon:'📝', label:'Announcement', bar:'' },
  image: { icon:'🖼️', label:'Image',        bar:'' },
  event: { icon:'📅', label:'Event',        bar:'nb-event-bar' },
  award: { icon:'🏆', label:'Award',        bar:'nb-award-bar' },
  alert: { icon:'🔔', label:'Alert',        bar:'nb-alert-bar' },
};

// ── Student: fetch and render notices ──
async function loadNotices() {
  const loading = document.getElementById('nb-loading');
  const empty   = document.getElementById('nb-empty');
  const list    = document.getElementById('nb-list');
  if (!list) return;

  try {
    const res     = await fetch('/api/notices');
    const notices = await res.json();

    if (loading) loading.style.display = 'none';

    if (!notices.length) {
      if (empty) empty.style.display = 'block';
      return;
    }

    list.innerHTML = notices.map(n => renderStudentCard(n)).join('');
  } catch(e) {
    if (loading) loading.textContent = 'Could not load notices.';
    console.error('Notice load error:', e);
  }
}

function renderStudentCard(n) {
  const cfg   = NB_CONFIG[n.type] || NB_CONFIG.text;
  const date  = n.created_at ? n.created_at.slice(0,10) : '';
  const extra = cfg.bar ? ` ${cfg.bar}` : '';

  let imgHtml = '';
  if (n.image_url) {
    imgHtml = `<img class="nb-student-img" src="${n.image_url}" alt="${escHtml(n.title)}" loading="lazy">`;
  }

  let contentHtml = '';
  if (n.content) {
    contentHtml = `<div class="nb-student-content">${escHtml(n.content).replace(/\n/g,'<br>')}</div>`;
  }

  return `
    <div class="nb-student-card${extra}">
      <div class="nb-student-header">
        <div class="nb-icon nb-icon-${n.type}">${cfg.icon}</div>
        <div>
          <div class="nb-student-title">${escHtml(n.title)}</div>
          <div class="nb-student-date">${cfg.label} · ${date}</div>
        </div>
      </div>
      ${contentHtml}
      ${imgHtml}
    </div>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// Auto-load notices when switching to noticeboard tab
const _nbOrigSwitch = switchTab;
window.switchTab = function(name) {
  _nbOrigSwitch(name);
  if (name === 'noticeboard') loadNotices();
};

// ── Admin: show/hide image field on add form ──
function toggleImageField(type) {
  const field = document.getElementById('nb-image-field');
  if (field) field.style.display = (type === 'image') ? 'block' : 'none';
}

function toggleEditImageField(type) {
  const sec = document.getElementById('ne-image-section');
  if (sec) sec.style.display = (type === 'image') ? 'block' : 'none';
}

// ── Admin: open edit modal ──
function openNoticeEdit(id, type, title, content, order, active, imagePath) {
  const form = document.getElementById('notice-edit-form');
  if (form) form.action = '/admin/notices/edit/' + id;

  const el = (i) => document.getElementById(i);
  if (el('ne-type'))    { el('ne-type').value = type; toggleEditImageField(type); }
  if (el('ne-title'))     el('ne-title').value   = title;
  if (el('ne-content'))   el('ne-content').value = content;
  if (el('ne-order'))     el('ne-order').value   = order;
  if (el('ne-active'))    el('ne-active').checked = !!active;

  // Show current image preview if exists
  const imgSec     = el('ne-current-image');
  const imgPreview = el('ne-current-img-preview');
  if (imgSec && imgPreview) {
    if (imagePath) {
      imgPreview.src          = '/static/uploads/notices/' + imagePath;
      imgSec.style.display    = 'block';
    } else {
      imgSec.style.display    = 'none';
    }
  }
  // Reset remove checkbox
  if (el('ne-remove-img')) el('ne-remove-img').checked = false;

  const modal = document.getElementById('notice-edit-modal');
  if (modal) modal.style.display = 'flex';
}

function closeNoticeModal() {
  const modal = document.getElementById('notice-edit-modal');
  if (modal) modal.style.display = 'none';
}

// Close on backdrop click
document.addEventListener('click', e => {
  const modal = document.getElementById('notice-edit-modal');
  if (modal && e.target === modal) closeNoticeModal();
});
