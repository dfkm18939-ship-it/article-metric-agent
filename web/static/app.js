// web/static/app.js
// 职责：前端逻辑（对话渲染、API 调用、图表初始化、澄清处理）
// 无框架依赖，原生 JS

const API = {
  query:   '/api/query',
  clarify: '/api/clarify',
  metrics: '/api/metrics',
};

// ── 状态 ──────────────────────────────────────────────────
// 使用 crypto.randomUUID 生成会话 ID，并持久化到 localStorage
function getOrCreateUserId() {
  const stored = localStorage.getItem('metric_agent_user_id');
  if (stored) return stored;
  const id = 'user_' + (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36));
  localStorage.setItem('metric_agent_user_id', id);
  return id;
}

const state = {
  userId:        getOrCreateUserId(),
  lastQuery:     '',
  chartInstance: null,
};

// ── DOM 引用 ──────────────────────────────────────────────
const chatContainer = document.getElementById('chat');
const inputEl       = document.getElementById('user-input');
const sendBtn       = document.getElementById('send-btn');

// ── 初始化 ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  appendBotMessage(
    '<p>👋 您好！我是数据指标智能助手。<br>请输入您的数据问题，例如：<em>今年签发了多少稿件？</em></p>'
  );

  // 快捷按钮
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      inputEl.value = btn.textContent;
      sendQuery();
    });
  });

  // 发送按钮 & Enter
  sendBtn.addEventListener('click', sendQuery);
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(); }
  });
});

// ── 发送查询 ──────────────────────────────────────────────
async function sendQuery() {
  const query = inputEl.value.trim();
  if (!query) return;

  state.lastQuery = query;
  inputEl.value   = '';
  setSendDisabled(true);

  appendUserMessage(query);
  const loadingId = appendLoading();

  try {
    const res  = await fetch(API.query, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ query, user_id: state.userId }),
    });
    const data = await res.json();
    removeLoading(loadingId);
    handleResponse(data);
  } catch (err) {
    removeLoading(loadingId);
    appendBotMessage(`<p class="anomaly-warning">❌ 请求失败：${err.message}</p>`);
  } finally {
    setSendDisabled(false);
    inputEl.focus();
  }
}

// ── 响应处理 ──────────────────────────────────────────────
function handleResponse(data) {
  if (data.type === 'clarify') {
    appendBotMessage(data.html || data.message || '请选择查询口径');
    // 绑定澄清按钮事件
    setTimeout(bindClarifyButtons, 50);
    return;
  }

  if (data.type === 'error') {
    appendBotMessage(
      `<p class="anomaly-warning">⚠️ ${data.message}</p>` +
      (data.fix_suggestion ? `<p style="font-size:12px;color:#6b7280;margin-top:6px;">${data.fix_suggestion}</p>` : '')
    );
    return;
  }

  if (data.type === 'result') {
    renderResult(data);
    return;
  }

  appendBotMessage('<p>收到响应，但格式未知。</p>');
}

// ── 渲染结果卡片 ──────────────────────────────────────────
function renderResult(data) {
  const chartId = 'chart-' + Date.now();
  const timeRange = data.time_range || {};
  const timeLabel = timeRange.start
    ? `${timeRange.start} 至 ${timeRange.end}`
    : '';
  const chart    = data.chart || {};
  const isCard   = chart.chart_type === 'card';
  const cardVal  = chart.card_value ?? extractSingleValue(data.data);
  const sqlEscaped = escapeHtml(data.sql || '');

  let chartSection = '';
  if (!isCard && chart.echarts_option) {
    chartSection = `<div class="chart-area" id="${chartId}"></div>`;
  }

  const cardSection = isCard
    ? `<div class="big-number">${cardVal}<span class="unit">篇</span></div>`
    : '';

  const html = `
<div class="result-card">
  <div class="metric-header">
    <span class="metric-name">📊 ${escapeHtml(data.caliber || '稿件签发通过量')}</span>
    <span class="caliber-badge">已签发口径</span>
    ${timeLabel ? `<span class="time-badge">📅 ${timeLabel}</span>` : ''}
    ${data.anomaly?.is_anomaly ? '<span style="color:#dc2626;font-size:12px;">⚠️ 异常</span>' : ''}
  </div>
  ${cardSection}
  ${chartSection}
  <div>${data.summary_html || ''}</div>
  <div class="sql-toggle" onclick="toggleSQL(this)">🔍 查看 SQL ▾</div>
  <div class="sql-block">
    <pre>${sqlEscaped}</pre>
  </div>
</div>`;

  appendBotMessage(html);

  // 初始化 ECharts（若有）
  if (!isCard && chart.echarts_option && chartId) {
    setTimeout(() => initChart(chartId, chart.echarts_option), 100);
  }
}

// ── ECharts 初始化 ─────────────────────────────────────────
function initChart(elId, option) {
  const el = document.getElementById(elId);
  if (!el || typeof echarts === 'undefined') return;
  const instance = echarts.init(el);
  instance.setOption(option);
  window.addEventListener('resize', () => instance.resize());
}

// ── 澄清按钮绑定 ──────────────────────────────────────────
function bindClarifyButtons() {
  document.querySelectorAll('.clarify-btn:not([data-bound])').forEach(btn => {
    btn.setAttribute('data-bound', '1');
    btn.addEventListener('click', async () => {
      const choice   = btn.getAttribute('data-label') || 'A';
      const metricId = btn.getAttribute('data-metric-id') || '';
      appendUserMessage(`我选择 ${choice}（${btn.querySelector('strong')?.textContent || metricId}）`);

      const loadingId = appendLoading();
      setSendDisabled(true);

      try {
        const res  = await fetch(API.clarify, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({
            choice,
            user_id:       state.userId,
            original_query: state.lastQuery,
          }),
        });
        const data = await res.json();
        removeLoading(loadingId);
        handleResponse(data);
      } catch (err) {
        removeLoading(loadingId);
        appendBotMessage(`<p class="anomaly-warning">❌ 请求失败：${err.message}</p>`);
      } finally {
        setSendDisabled(false);
      }
    });
  });
}

// ── SQL 展开/折叠 ─────────────────────────────────────────
function toggleSQL(toggleEl) {
  const block = toggleEl.nextElementSibling;
  if (!block) return;
  const isOpen = block.style.display === 'block';
  block.style.display = isOpen ? 'none' : 'block';
  toggleEl.textContent = isOpen ? '🔍 查看 SQL ▾' : '🔍 隐藏 SQL ▲';
}

// ── DOM 辅助 ──────────────────────────────────────────────
function appendUserMessage(text) {
  // User input is plain text — must NOT be rendered as HTML
  const row = document.createElement('div');
  row.className = 'msg-row user';
  const avatar = document.createElement('div');
  avatar.className = 'avatar user';
  avatar.textContent = '👤';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;  // safe: textContent never interprets HTML
  row.appendChild(avatar);
  row.appendChild(bubble);
  chatContainer.appendChild(row);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return row;
}

function appendBotMessage(html) {
  appendMessage(html, 'bot');
}

function appendMessage(html, role) {
  const row = document.createElement('div');
  row.className = `msg-row ${role}`;

  const emoji = role === 'user' ? '👤' : '🤖';
  row.innerHTML = `
    <div class="avatar ${role}">${emoji}</div>
    <div class="bubble">${html}</div>`;
  chatContainer.appendChild(row);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return row;
}

function appendLoading() {
  const id  = 'loading-' + Date.now();
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.id        = id;
  row.innerHTML = `
    <div class="avatar bot">🤖</div>
    <div class="bubble">
      <div class="loading-dots"><span></span><span></span><span></span></div>
    </div>`;
  chatContainer.appendChild(row);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return id;
}

function removeLoading(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function setSendDisabled(disabled) {
  sendBtn.disabled = disabled;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function extractSingleValue(data) {
  if (!data || !data.length) return 0;
  const first = data[0];
  for (const key of ['signed_count', 'count', 'total', 'value']) {
    if (key in first) return first[key] ?? 0;
  }
  const vals = Object.values(first);
  return vals[0] ?? 0;
}
