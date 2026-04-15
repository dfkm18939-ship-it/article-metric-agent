// app.js — 前端交互逻辑（稿件指标智能助手）

const API_BASE = '';
let currentUserId = 'user_001';
let lastOriginalQuery = '';
let chartInstance = null;

// ── 初始化 ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('queryInput');
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });

  // Register resize listener once at init time
  window.addEventListener('resize', () => {
    if (chartInstance) chartInstance.resize();
  });
});

// ── 快捷问题 ───────────────────────────────────────────────────
function quickQuery(text) {
  document.getElementById('queryInput').value = text;
  sendQuery();
}

// ── 发送查询 ───────────────────────────────────────────────────
async function sendQuery() {
  const input = document.getElementById('queryInput');
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  input.style.height = 'auto';

  appendUserMessage(query);
  showLoading();

  try {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, user_id: currentUserId }),
    });
    const data = await res.json();
    hideLoading();

    if (data.type === 'result') {
      renderResult(data);
    } else if (data.type === 'clarify') {
      lastOriginalQuery = data.original_query || query;
      renderClarify(data);
    } else {
      renderError(data.message || '查询失败，请重试');
    }
  } catch (err) {
    hideLoading();
    renderError(`请求失败：${err.message}`);
  }
}

// ── 发送澄清选择 ────────────────────────────────────────────────
async function handleClarifyChoice(choice) {
  appendUserMessage(`选择：${choice}`);
  showLoading();

  try {
    const res = await fetch(`${API_BASE}/api/clarify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        choice,
        user_id: currentUserId,
        original_query: lastOriginalQuery,
      }),
    });
    const data = await res.json();
    hideLoading();

    if (data.type === 'result') {
      renderResult(data);
    } else {
      renderError(data.message || '查询失败');
    }
  } catch (err) {
    hideLoading();
    renderError(`请求失败：${err.message}`);
  }
}

// ── 渲染用户消息 ────────────────────────────────────────────────
function appendUserMessage(text) {
  const chatArea = document.getElementById('chatArea');
  const msg = document.createElement('div');
  msg.className = 'message user-message';
  msg.innerHTML = `
    <div class="message-avatar">👤</div>
    <div class="message-bubble">${escapeHtml(text)}</div>
  `;
  chatArea.appendChild(msg);
  scrollToBottom();
}

// ── 渲染查询结果 ────────────────────────────────────────────────
function renderResult(data) {
  const chatArea = document.getElementById('chatArea');
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message assistant-message';

  const chartId = 'chart_' + Date.now();
  const metricName = data.metric_name || '稿件签发通过量';
  const caliber = data.caliber || '签发量';
  const timeExpr = data.time_expression || '';
  const timeRange = data.time_range || {};
  const sql = data.sql || '';
  const validation = data.validation || {};

  // 提取核心数值
  let mainValue = 0;
  if (data.data && data.data.length === 1) {
    const firstRow = data.data[0];
    mainValue = Object.values(firstRow)[0];
  } else if (data.data && data.data.length > 0) {
    mainValue = data.data.reduce((sum, row) => {
      const v = Object.values(row).find(x => typeof x === 'number');
      return sum + (v || 0);
    }, 0);
  }

  const chartType = data.chart_config ? data.chart_config.type : 'stat_card';
  const hasChart = chartType !== 'stat_card' && data.chart_config && data.chart_config.echarts_option;

  // SQL 验证徽章
  const sqlReview = validation.sql_review || {};
  const sqlBadge = sqlReview.passed !== false
    ? '<span class="badge badge-success">✅ SQL 验证通过</span>'
    : '<span class="badge badge-warning">⚠️ SQL 已修正</span>';

  const displayReview = validation.display_review || {};
  const displayBadge = displayReview.accurate !== false
    ? '<span class="badge badge-success">✅ 展示准确</span>'
    : '<span class="badge badge-warning">⚠️ 展示有偏差</span>';

  msgDiv.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="result-card">
      <div class="result-header">
        <div class="result-title">${escapeHtml(metricName)}</div>
        <div class="result-caliber">口径：${escapeHtml(caliber)} · ${escapeHtml(timeExpr)}</div>
      </div>
      <div class="result-body">

        <!-- 核心数值 -->
        ${!hasChart ? `
        <div class="stat-block">
          <span class="stat-value">${formatNumber(mainValue)}</span>
          <span class="stat-unit">篇</span>
          <div class="stat-label">${escapeHtml(metricName)}</div>
          <div class="stat-time">${timeRange.start || ''} 至 ${timeRange.end || ''}</div>
        </div>
        ` : ''}

        <!-- 图表 -->
        ${hasChart ? `<div class="chart-container" id="${chartId}"></div>` : ''}

        <!-- 文字总结 -->
        <div class="summary-block">${data.summary_html || ''}</div>

        <!-- SQL 展开 -->
        ${sql ? `
        <div class="sql-toggle" onclick="toggleSql(this)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M9 3l11 9-11 9V3z" fill="currentColor"/></svg>
          查看 SQL
        </div>
        <div class="sql-block"><code>${escapeHtml(sql)}</code></div>
        ` : ''}

        <!-- 验证徽章 -->
        <div class="validation-row">
          ${sqlBadge}
          ${displayBadge}
          <span class="badge badge-success">⚡ Claude + GPT + Gemini</span>
        </div>

      </div>
    </div>
  `;

  chatArea.appendChild(msgDiv);
  scrollToBottom();

  // 初始化图表
  if (hasChart) {
    setTimeout(() => initChart(chartId, data.chart_config.echarts_option), 100);
  }
}

// ── 渲染澄清选项 ────────────────────────────────────────────────
function renderClarify(data) {
  const chatArea = document.getElementById('chatArea');
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message assistant-message';

  const options = data.options || [];
  const optionsHtml = options.map(opt => `
    <button class="clarify-btn" onclick="handleClarifyChoice('${escapeHtml(opt.key)}')">
      <span class="clarify-key">${escapeHtml(opt.key)}</span>
      <span>${escapeHtml(opt.label)}</span>
    </button>
  `).join('');

  msgDiv.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="clarify-card">
      <div class="clarify-title">🤔 ${escapeHtml(data.message || '请选择您想查的指标：')}</div>
      <div class="clarify-options">${optionsHtml}</div>
    </div>
  `;
  chatArea.appendChild(msgDiv);
  scrollToBottom();
}

// ── 渲染错误 ────────────────────────────────────────────────────
function renderError(message) {
  const chatArea = document.getElementById('chatArea');
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message assistant-message';
  msgDiv.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="message-bubble" style="border-left:3px solid #ea4335">
      <p>⚠️ ${escapeHtml(message)}</p>
    </div>
  `;
  chatArea.appendChild(msgDiv);
  scrollToBottom();
}

// ── 初始化 ECharts ──────────────────────────────────────────────
function initChart(containerId, option) {
  const dom = document.getElementById(containerId);
  if (!dom || !option) return;
  if (chartInstance) chartInstance.dispose();
  chartInstance = echarts.init(dom);
  chartInstance.setOption(option);
}

// ── SQL 展开/收起 ───────────────────────────────────────────────
function toggleSql(el) {
  const sqlBlock = el.nextElementSibling;
  if (!sqlBlock) return;
  const isVisible = sqlBlock.classList.contains('visible');
  sqlBlock.classList.toggle('visible', !isVisible);
  el.querySelector('svg').style.transform = isVisible ? '' : 'rotate(90deg)';
}

// ── Loading ─────────────────────────────────────────────────────
let stepTimer = null;
function showLoading() {
  document.getElementById('loadingOverlay').style.display = 'flex';
  document.getElementById('sendBtn').disabled = true;
  const steps = ['step1', 'step2', 'step3', 'step4'];
  let i = 0;
  steps.forEach(s => {
    const el = document.getElementById(s);
    if (el) el.className = 'step';
  });
  if (stepTimer) clearInterval(stepTimer);
  stepTimer = setInterval(() => {
    if (i > 0) {
      const prev = document.getElementById(steps[i - 1]);
      if (prev) prev.className = 'step done';
    }
    if (i < steps.length) {
      const cur = document.getElementById(steps[i]);
      if (cur) cur.className = 'step active';
      i++;
    } else {
      clearInterval(stepTimer);
    }
  }, 800);
}

function hideLoading() {
  if (stepTimer) clearInterval(stepTimer);
  document.getElementById('loadingOverlay').style.display = 'none';
  document.getElementById('sendBtn').disabled = false;
}

// ── 工具函数 ────────────────────────────────────────────────────
function scrollToBottom() {
  const chatArea = document.getElementById('chatArea');
  setTimeout(() => { chatArea.scrollTop = chatArea.scrollHeight; }, 50);
}

function formatNumber(n) {
  if (n === null || n === undefined) return '0';
  return Number(n).toLocaleString('zh-CN');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
