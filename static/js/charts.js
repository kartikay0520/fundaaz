// ══════════════════════════════════════
//  charts.js  (v5 — topic analysis added)
// ══════════════════════════════════════

let trendChart   = null;
let subjectChart = null;
let topicChart   = null;

const COLORS = ['#2a9d5c','#1a6b3a','#4ade80','#0a3d1f','#6ee7b7',
                '#34d399','#16a34a','#166534','#059669','#047857'];

// ── Performance tab ──────────────────────────────────────────────
async function loadCharts(filter, btnEl) {
  if (btnEl) {
    document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
  }
  try {
    const res  = await fetch('/api/student/chart-data?filter=' + filter);
    const data = await res.json();
    renderSummary(data);
    renderTrendChart(data.trend);
    renderSubjectChart(data.subjects);
  } catch(e) { console.error('Chart error:', e); }
}

function renderSummary(data) {
  const box = document.getElementById('perf-summary');
  if (!box) return;
  const pcts = data.trend.map(d => d.pct);
  if (!pcts.length) {
    box.innerHTML = '<div class="perf-card"><div class="perf-pct" style="color:var(--gray)">—</div><div class="perf-label">No data</div></div>';
    return;
  }
  const avg  = (pcts.reduce((a,b)=>a+b,0)/pcts.length).toFixed(1);
  const best = Math.max(...pcts).toFixed(1);
  const low  = Math.min(...pcts).toFixed(1);
  const cls  = p => p>=75?'pct-high':p>=50?'pct-mid':'pct-low';
  box.innerHTML = `
    <div class="perf-card"><div class="perf-pct ${cls(avg)}">${avg}%</div><div class="perf-label">Average</div></div>
    <div class="perf-card"><div class="perf-pct pct-high">${best}%</div><div class="perf-label">Best</div></div>
    <div class="perf-card"><div class="perf-pct pct-low">${low}%</div><div class="perf-label">Lowest</div></div>
    <div class="perf-card"><div class="perf-pct" style="color:var(--g2)">${pcts.length}</div><div class="perf-label">Tests</div></div>`;
}

function renderTrendChart(trend) {
  const ctx = document.getElementById('trend-chart');
  if (!ctx) return;
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trend.map(d => d.label),
      datasets: [{
        label: 'Score %', data: trend.map(d => d.pct),
        fill: true, backgroundColor: 'rgba(42,157,92,0.10)',
        borderColor: '#2a9d5c', borderWidth: 2.5,
        pointBackgroundColor: '#1a6b3a', pointRadius: 5, tension: 0.4
      }]
    },
    options: chartOptions()
  });
}

function renderSubjectChart(subjects) {
  const ctx = document.getElementById('subject-chart');
  if (!ctx) return;
  if (subjectChart) subjectChart.destroy();
  subjectChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: subjects.map(s => s.subject),
      datasets: [{
        label: 'Average %', data: subjects.map(s => s.pct),
        backgroundColor: subjects.map((_,i) => COLORS[i % COLORS.length]),
        borderRadius: 7, borderSkipped: false
      }]
    },
    options: chartOptions()
  });
}

function chartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min:0, max:100, grid:{color:'#f0fdf4'},
           ticks:{callback:v=>v+'%', color:'#64748b', font:{size:11}} },
      x: { grid:{display:false},
           ticks:{color:'#64748b', font:{size:11}, maxRotation:40, minRotation:0} }
    },
    plugins: {
      legend: {display:false},
      tooltip: {callbacks:{label:ctx=>` ${ctx.raw}%`}}
    }
  };
}

// ── Topic Analysis tab ────────────────────────────────────────────
let _topicData = [];

async function loadTopicAnalysis() {
  try {
    const res  = await fetch('/api/student/chart-data?filter=all');
    const data = await res.json();
    _topicData = data.topics || [];
    renderTopicSummaryCards(data.subjects || []);
    renderTopicTable(_topicData);
    renderTopicChart(_topicData);
  } catch(e) { console.error('Topic error:', e); }
}

function renderTopicSummaryCards(subjects) {
  const box = document.getElementById('topic-summary-cards');
  if (!box) return;
  if (!subjects.length) {
    box.innerHTML = '';
    return;
  }
  box.innerHTML = subjects.map(s => {
    const cls = s.pct>=75?'pct-high':s.pct>=50?'pct-mid':'pct-low';
    return `<div class="stat-card">
      <div class="stat-icon">📚</div>
      <div class="stat-val ${cls}">${s.pct}%</div>
      <div class="stat-label">${s.subject}</div>
    </div>`;
  }).join('');
}

function renderTopicTable(topics) {
  const tbody    = document.getElementById('topic-tbody');
  const cardBox  = document.getElementById('topic-cards');
  const emptyBox = document.getElementById('topic-empty');
  if (!tbody) return;

  if (!topics.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">No topic data yet</td></tr>';
    if (emptyBox) emptyBox.style.display = 'block';
    return;
  }
  if (emptyBox) emptyBox.style.display = 'none';

  const strength = p => p >= 75
    ? '<span class="strength-strong">✓ Strong</span>'
    : p >= 50
      ? '<span class="strength-avg">~ Average</span>'
      : '<span class="strength-weak">✗ Needs Work</span>';

  // Parse label "Chapter › Topic" back into parts
  tbody.innerHTML = topics.map(t => {
    const parts   = t.label.split(' › ');
    const chapter = parts[0] || '—';
    const topic   = parts[1] || '—';
    return `<tr class="topic-table-row" data-subject="${t.subject}">
      <td>${t.subject}</td>
      <td>${chapter}</td>
      <td>${topic}</td>
      <td style="text-align:center">${t.tests||1}</td>
      <td><span class="pct ${t.pct>=75?'pct-high':t.pct>=50?'pct-mid':'pct-low'}">${t.pct}%</span></td>
      <td>${strength(t.pct)}</td>
    </tr>`;
  }).join('');

  // Mobile cards
  if (cardBox) {
    cardBox.innerHTML = topics.map(t => {
      const parts   = t.label.split(' › ');
      const chapter = parts[0] || '—';
      const topic   = parts[1] || '—';
      const sClass  = t.pct>=75?'topic-strong':t.pct>=50?'topic-avg':'topic-weak';
      return `<div class="card-row topic-card-row" data-subject="${t.subject}">
        <div class="card-row-title">${chapter} › ${topic}</div>
        <div class="card-row-grid">
          <div class="card-row-item"><span class="lbl">Subject</span>${t.subject}</div>
          <div class="card-row-item"><span class="lbl">Score</span>
            <span class="pct ${t.pct>=75?'pct-high':t.pct>=50?'pct-mid':'pct-low'}">${t.pct}%</span>
          </div>
          <div class="card-row-item"><span class="lbl">Strength</span>
            <span class="topic-badge ${sClass}">${t.pct>=75?'Strong':t.pct>=50?'Average':'Needs Work'}</span>
          </div>
        </div>
      </div>`;
    }).join('');
  }
}

function renderTopicChart(topics) {
  const wrap = document.getElementById('topic-chart-wrap');
  const ctx  = document.getElementById('topic-chart');
  if (!ctx || !topics.length) { if(wrap) wrap.style.display='none'; return; }
  if (wrap) wrap.style.display = 'block';
  if (topicChart) topicChart.destroy();

  const labels = topics.map(t => {
    const parts = t.label.split(' › ');
    return parts[1] || parts[0];
  });

  topicChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Score %',
        data: topics.map(t => t.pct),
        backgroundColor: topics.map(t =>
          t.pct>=75 ? 'rgba(22,163,74,.75)' :
          t.pct>=50 ? 'rgba(217,119,6,.75)' :
                     'rgba(220,38,38,.75)'),
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      ...chartOptions(),
      plugins: {
        legend: {display:false},
        tooltip: {callbacks:{label: ctx => ` ${ctx.raw}% — ${topics[ctx.dataIndex]?.subject}`}}
      }
    }
  });
}

function filterTopicTable() {
  const subj = document.getElementById('ta-subject-filter')?.value || '';
  document.querySelectorAll('.topic-table-row').forEach(r => {
    r.style.display = (!subj || r.dataset.subject === subj) ? '' : 'none';
  });
  document.querySelectorAll('.topic-card-row').forEach(r => {
    r.style.display = (!subj || r.dataset.subject === subj) ? '' : 'none';
  });
}

// Auto-load topic analysis when tab opens
const _origSwitch = window.switchTab;
window.switchTab = function(name) {
  _origSwitch(name);
  if (name === 'topic-analysis') loadTopicAnalysis();
  if (name === 'noticeboard')    loadNotices();
  if (name === 'performance')    loadCharts('all');
  if (name === 'history') {
    const rows = document.querySelectorAll('#stu-hist-tbody tr[data-pct]');
    const h = document.getElementById('stu-heading-count');
    if (h && rows.length) h.textContent = '('+rows.length+' total)';
  }
};

// ── Student history tab filter ────────────────────────────────────
function stuApplyFilters() {
  const subj    = document.getElementById('sf-subject')?.value  || '';
  const code    = document.getElementById('sf-code')?.value     || '';
  const chapter = document.getElementById('sf-chapter')?.value  || '';
  const dfrom   = document.getElementById('sf-date-from')?.value || '';
  const dto     = document.getElementById('sf-date-to')?.value   || '';
  const pMin    = document.getElementById('sf-pct-min')?.value;
  const pMax    = document.getElementById('sf-pct-max')?.value;

  let visible = 0;
  const rows  = document.querySelectorAll('#stu-hist-tbody tr[data-pct]');
  rows.forEach(row => {
    const show = stuMatch(row, subj, code, chapter, dfrom, dto, pMin, pMax);
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  document.querySelectorAll('.card-table .card-row[data-pct]').forEach(card => {
    card.style.display = stuMatch(card, subj, code, chapter, dfrom, dto, pMin, pMax) ? '' : 'none';
  });

  const total   = rows.length;
  const countEl = document.getElementById('stu-filter-count');
  const headEl  = document.getElementById('stu-heading-count');
  const emptyEl = document.getElementById('stu-hist-empty');
  if (countEl) countEl.textContent = total ? `Showing ${visible} of ${total}` : '';
  if (headEl)  headEl.textContent  = total ? `(${visible} of ${total})` : '';
  if (emptyEl) emptyEl.style.display = (visible===0 && total>0) ? 'block' : 'none';
}

function stuMatch(el, subj, code, chapter, dfrom, dto, pMin, pMax) {
  if (subj    && el.dataset.subject !== subj)   return false;
  if (code    && el.dataset.code    !== code)   return false;
  if (chapter && el.dataset.chapter !== chapter) return false;
  if (dfrom   && el.dataset.date    <  dfrom)   return false;
  if (dto     && el.dataset.date    >  dto)     return false;
  const pct = parseFloat(el.dataset.pct) || 0;
  if (pMin !== '' && pMin !== undefined && pct < parseFloat(pMin)) return false;
  if (pMax !== '' && pMax !== undefined && pct > parseFloat(pMax)) return false;
  return true;
}

function stuQuick(type) {
  const pMin = document.getElementById('sf-pct-min');
  const pMax = document.getElementById('sf-pct-max');
  if (pMin) pMin.value = '';
  if (pMax) pMax.value = '';
  const ranges = {
    top:[90,100], above:[75,89.9], average:[50,74.9],
    poor:[33,49.9], fail:[0,32.9], all:[null,null]
  };
  const [lo,hi] = ranges[type] || [null,null];
  if (lo !== null && pMin) pMin.value = lo;
  if (hi !== null && pMax) pMax.value = hi;
  ['all','top','above','average','poor','fail'].forEach(id => {
    const btn = document.getElementById('sf-qf-' + id);
    if (btn) btn.classList.toggle('active', id === type);
  });
  stuApplyFilters();
}

function stuClearFilters() {
  ['sf-subject','sf-code','sf-chapter'].forEach(id => {
    const el = document.getElementById(id); if(el) el.value='';
  });
  ['sf-date-from','sf-date-to','sf-pct-min','sf-pct-max'].forEach(id => {
    const el = document.getElementById(id); if(el) el.value='';
  });
  ['all','top','above','average','poor','fail'].forEach(id => {
    const btn = document.getElementById('sf-qf-'+id);
    if(btn) btn.classList.toggle('active', id==='all');
  });
  stuApplyFilters();
}
