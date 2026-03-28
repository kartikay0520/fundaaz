// ══════════════════════════════════════
//  FUNDAAZ – admin_charts.js  (v5)
//  Topic chart removed — table only
// ══════════════════════════════════════

let adminTrendChart   = null;
let adminSubjectChart = null;

const ADM_COLORS = ['#2a9d5c','#1a6b3a','#4ade80','#0a3d1f',
                    '#6ee7b7','#34d399','#16a34a','#166534'];

async function loadAdminCharts(studentId) {
  try {
    const res  = await fetch(`/api/admin/student-chart/${studentId}`);
    const data = await res.json();
    renderAdminTrend(data.trend);
    renderAdminSubject(data.subjects);
    // Show topic section (table only) if topic data exists
    const topicSec = document.getElementById('admin-topic-section');
    if (topicSec) topicSec.style.display = (data.topics||[]).length ? 'block' : 'none';
  } catch(e) { console.error('Admin chart error:', e); }
}

function renderAdminTrend(trend) {
  const ctx = document.getElementById('admin-trend-chart');
  if (!ctx) return;
  if (adminTrendChart) adminTrendChart.destroy();
  adminTrendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trend.map(d => d.label),
      datasets: [{
        label: 'Score %', data: trend.map(d => d.pct),
        fill: true, backgroundColor: 'rgba(42,157,92,0.10)',
        borderColor: '#2a9d5c', borderWidth: 2.5,
        pointBackgroundColor: '#1a6b3a', pointRadius: 6, tension: 0.4
      }]
    },
    options: admChartOpts()
  });
}

function renderAdminSubject(subjects) {
  const ctx = document.getElementById('admin-subject-chart');
  if (!ctx) return;
  if (adminSubjectChart) adminSubjectChart.destroy();
  adminSubjectChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: subjects.map(s => s.subject),
      datasets: [{
        label: 'Average %', data: subjects.map(s => s.pct),
        backgroundColor: subjects.map((_,i) => ADM_COLORS[i % ADM_COLORS.length]),
        borderRadius: 7, borderSkipped: false
      }]
    },
    options: admChartOpts()
  });
}

function admChartOpts() {
  return {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { min:0, max:100, grid:{color:'#f0fdf4'},
           ticks:{callback:v=>v+'%', color:'#64748b'} },
      x: { grid:{display:false}, ticks:{color:'#64748b'} }
    },
    plugins: {
      legend: {display:false},
      tooltip: {callbacks:{label:ctx=>` ${ctx.raw}%`}}
    }
  };
}
