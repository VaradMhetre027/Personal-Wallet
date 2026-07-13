/**
 * Personal Wallet Dashboard — Client-side Application
 * Connects to FastAPI backend at /api/v1
 */

const API = '/api/v1';
let token = localStorage.getItem('pw_token') || '';
let refreshToken = localStorage.getItem('pw_refresh') || '';
let currentUser = null;
let wallets = [];
let categories = [];
let currentPage = 'overview';
let txnPage = 1;
let categoryChart = null;

// ══════════════════════════════════════
//  API HELPER
// ══════════════════════════════════════

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401 && refreshToken) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${token}`;
      return fetch(`${API}${path}`, { ...options, headers });
    }
    handleLogout();
    throw new Error('Session expired');
  }

  return res;
}

async function tryRefreshToken() {
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (res.ok) {
      const data = await res.json();
      token = data.access_token;
      refreshToken = data.refresh_token;
      localStorage.setItem('pw_token', token);
      localStorage.setItem('pw_refresh', refreshToken);
      return true;
    }
  } catch (e) { /* ignore */ }
  return false;
}

// ══════════════════════════════════════
//  AUTH
// ══════════════════════════════════════

function switchAuthTab(tab) {
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  document.getElementById('login-form').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('register-form').style.display = tab === 'register' ? 'block' : 'none';
}

async function handleLogin(e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="loading-spinner"></div>';

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }

    const data = await res.json();
    token = data.access_token;
    refreshToken = data.refresh_token;
    localStorage.setItem('pw_token', token);
    localStorage.setItem('pw_refresh', refreshToken);

    showToast('Welcome back!', 'success');
    await enterDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Sign In</span>';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const btn = document.getElementById('register-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="loading-spinner"></div>';

  try {
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: document.getElementById('reg-name').value,
        username: document.getElementById('reg-username').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        phone: document.getElementById('reg-phone').value || null,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.detail;
      if (Array.isArray(msg)) throw new Error(msg.map(m => m.msg || m).join(', '));
      throw new Error(msg || 'Registration failed');
    }

    showToast('Account created! Please sign in.', 'success');
    switchAuthTab('login');
    document.getElementById('login-email').value = document.getElementById('reg-email').value;
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Create Account</span>';
  }
}

function handleLogout() {
  token = '';
  refreshToken = '';
  currentUser = null;
  localStorage.removeItem('pw_token');
  localStorage.removeItem('pw_refresh');
  document.getElementById('auth-view').style.display = '';
  document.getElementById('dashboard-view').style.display = 'none';
}

// ══════════════════════════════════════
//  DASHBOARD INIT
// ══════════════════════════════════════

async function enterDashboard() {
  document.getElementById('auth-view').style.display = 'none';
  document.getElementById('dashboard-view').style.display = 'flex';

  try {
    const res = await api('/auth/me');
    if (!res.ok) { handleLogout(); return; }
    currentUser = await res.json();

    document.getElementById('sidebar-username').textContent = currentUser.full_name;
    document.getElementById('user-avatar').textContent = currentUser.full_name.charAt(0).toUpperCase();
  } catch {
    handleLogout();
    return;
  }

  await Promise.all([loadWallets(), loadCategories()]);
  navigateTo('overview');
}

// ══════════════════════════════════════
//  NAVIGATION
// ══════════════════════════════════════

function navigateTo(page) {
  currentPage = page;
  document.querySelectorAll('.page-content').forEach(p => p.classList.add('hidden'));
  document.getElementById(`page-${page}`).classList.remove('hidden');

  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');

  const titles = {
    overview: ['Overview', "Welcome back! Here's your financial snapshot."],
    wallets: ['Wallets', 'Manage your wallets and track balances.'],
    transactions: ['Transactions', 'View and manage all your transactions.'],
    categories: ['Categories', 'Organize your spending by category.'],
  };
  const [title, sub] = titles[page] || ['', ''];
  document.getElementById('topbar-title').textContent = title;
  document.getElementById('topbar-subtitle').textContent = sub;

  // Load page data
  if (page === 'overview') loadOverview();
  else if (page === 'wallets') renderWallets();
  else if (page === 'transactions') loadTransactions();
  else if (page === 'categories') renderCategories();
}

function refreshCurrentPage() {
  loadWallets().then(() => loadCategories()).then(() => navigateTo(currentPage));
  showToast('Refreshed!', 'info');
}

// ══════════════════════════════════════
//  DATA LOADERS
// ══════════════════════════════════════

async function loadWallets() {
  try {
    const res = await api('/wallets');
    if (res.ok) {
      const data = await res.json();
      wallets = data.wallets || [];
      populateWalletDropdowns();
    }
  } catch (e) { console.error('Failed to load wallets', e); }
}

async function loadCategories() {
  try {
    const res = await api('/categories');
    if (res.ok) {
      categories = await res.json();
      populateCategoryDropdowns();
    }
  } catch (e) { console.error('Failed to load categories', e); }
}

function populateWalletDropdowns() {
  const selectors = ['txn-wallet', 'filter-wallet', 'transfer-from', 'transfer-to'];
  selectors.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const firstOpt = el.options[0];
    el.innerHTML = '';
    if (id === 'filter-wallet') {
      el.appendChild(new Option('All Wallets', ''));
    }
    wallets.forEach(w => {
      el.appendChild(new Option(`${w.name} (${w.balance_formatted})`, w.id));
    });
  });
}

function populateCategoryDropdowns() {
  const el = document.getElementById('txn-category');
  if (!el) return;
  el.innerHTML = '<option value="">No Category</option>';
  categories.forEach(c => {
    el.appendChild(new Option(c.name, c.id));
  });
}

// ══════════════════════════════════════
//  OVERVIEW PAGE
// ══════════════════════════════════════

async function loadOverview() {
  // Stats
  const totalBalance = wallets.reduce((sum, w) => sum + w.balance, 0);
  const walletCount = wallets.length;

  // Load transactions for stats
  let totalIncome = 0, totalExpense = 0, txnCount = 0, recentTxns = [];
  try {
    const res = await api('/transactions?per_page=10');
    if (res.ok) {
      const data = await res.json();
      totalIncome = data.total_income || 0;
      totalExpense = data.total_expense || 0;
      txnCount = data.total || 0;
      recentTxns = data.transactions || [];
    }
  } catch (e) { /* ignore */ }

  // Render stat cards
  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card indigo animate-in" style="animation-delay:0ms">
      <div class="stat-card-header">
        <div class="stat-card-icon">💰</div>
        <span class="stat-card-label">Total Balance</span>
      </div>
      <div class="stat-card-value">${formatAmount(totalBalance)}</div>
      <div class="stat-card-change up">${walletCount} wallet${walletCount !== 1 ? 's' : ''}</div>
    </div>
    <div class="stat-card green animate-in" style="animation-delay:80ms">
      <div class="stat-card-header">
        <div class="stat-card-icon">📈</div>
        <span class="stat-card-label">Total Income</span>
      </div>
      <div class="stat-card-value">${formatAmount(totalIncome)}</div>
      <div class="stat-card-change up">↑ Earnings</div>
    </div>
    <div class="stat-card red animate-in" style="animation-delay:160ms">
      <div class="stat-card-header">
        <div class="stat-card-icon">📉</div>
        <span class="stat-card-label">Total Expenses</span>
      </div>
      <div class="stat-card-value">${formatAmount(totalExpense)}</div>
      <div class="stat-card-change down">↓ Spending</div>
    </div>
    <div class="stat-card amber animate-in" style="animation-delay:240ms">
      <div class="stat-card-header">
        <div class="stat-card-icon">📋</div>
        <span class="stat-card-label">Transactions</span>
      </div>
      <div class="stat-card-value">${txnCount}</div>
      <div class="stat-card-change up">${categories.length} categories</div>
    </div>
  `;

  // Recent transactions
  renderTxnList('recent-txn-list', recentTxns.slice(0, 6));

  // Spending chart
  renderCategoryChart(recentTxns);

  // Wallets
  renderWalletCards('overview-wallets', wallets.slice(0, 4));
}

// ══════════════════════════════════════
//  WALLETS PAGE
// ══════════════════════════════════════

function renderWallets() {
  renderWalletCards('wallets-list', wallets);
}

function renderWalletCards(containerId, walletList) {
  const container = document.getElementById(containerId);
  if (!walletList.length) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">👛</div>
        <p class="empty-state-text">No wallets yet. Create your first wallet!</p>
        <button class="btn btn-primary btn-sm" onclick="openModal('wallet-modal')">+ Create Wallet</button>
      </div>`;
    return;
  }

  container.innerHTML = walletList.map((w, i) => `
    <div class="wallet-card ${w.is_frozen ? 'frozen' : ''} animate-in" style="animation-delay:${i * 60}ms">
      <div class="wallet-card-header">
        <span class="wallet-type-badge">${w.is_frozen ? '🔒 Frozen' : w.wallet_type}</span>
        ${w.is_default ? '<span class="wallet-default-star" title="Default wallet">⭐</span>' : ''}
      </div>
      <div class="wallet-balance">${w.balance_formatted}</div>
      <div class="wallet-name">${w.name}</div>
      <div class="wallet-actions">
        <button class="btn btn-ghost btn-sm" onclick="toggleFreezeWallet('${w.id}', ${w.is_frozen})">
          ${w.is_frozen ? '🔓 Unfreeze' : '🔒 Freeze'}
        </button>
        <button class="btn btn-ghost btn-sm" onclick="openTransferModal('${w.id}')">↔️ Transfer</button>
      </div>
    </div>
  `).join('');
}

async function createWallet(e) {
  e.preventDefault();
  try {
    const res = await api('/wallets', {
      method: 'POST',
      body: JSON.stringify({
        name: document.getElementById('wallet-name').value,
        wallet_type: document.getElementById('wallet-type').value,
        currency: document.getElementById('wallet-currency').value,
        is_default: document.getElementById('wallet-default').checked,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create wallet');
    }

    showToast('Wallet created!', 'success');
    closeModal('wallet-modal');
    document.getElementById('wallet-name').value = '';
    await loadWallets();
    navigateTo(currentPage);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function toggleFreezeWallet(id, isFrozen) {
  try {
    const action = isFrozen ? 'unfreeze' : 'freeze';
    const res = await api(`/wallets/${id}/${action}`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to ${action} wallet`);

    showToast(`Wallet ${action}d!`, 'success');
    await loadWallets();
    navigateTo(currentPage);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openTransferModal(fromId) {
  openModal('transfer-modal');
  setTimeout(() => {
    document.getElementById('transfer-from').value = fromId;
  }, 50);
}

async function transferFunds(e) {
  e.preventDefault();
  try {
    const res = await api('/wallets/transfer', {
      method: 'POST',
      body: JSON.stringify({
        from_wallet_id: document.getElementById('transfer-from').value,
        to_wallet_id: document.getElementById('transfer-to').value,
        amount: Math.round(parseFloat(document.getElementById('transfer-amount').value) * 100),
        description: document.getElementById('transfer-note').value || null,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Transfer failed');
    }

    showToast('Transfer successful!', 'success');
    closeModal('transfer-modal');
    await loadWallets();
    navigateTo(currentPage);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ══════════════════════════════════════
//  TRANSACTIONS PAGE
// ══════════════════════════════════════

async function loadTransactions() {
  const typeFilter = document.getElementById('filter-type')?.value || '';
  const walletFilter = document.getElementById('filter-wallet')?.value || '';
  let url = `/transactions?page=${txnPage}&per_page=15`;
  if (typeFilter) url += `&type=${typeFilter}`;
  if (walletFilter) url += `&wallet_id=${walletFilter}`;

  try {
    const res = await api(url);
    if (res.ok) {
      const data = await res.json();
      renderTxnList('full-txn-list', data.transactions || []);
      renderPagination(data);
    }
  } catch (e) { console.error('Failed to load transactions', e); }
}

function renderTxnList(containerId, txns) {
  const container = document.getElementById(containerId);
  if (!txns.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">💸</div>
        <p class="empty-state-text">No transactions yet.</p>
      </div>`;
    return;
  }

  container.innerHTML = txns.map((t, i) => {
    const icon = t.type === 'income' ? '↗️' : t.type === 'expense' ? '↙️' : '↔️';
    const sign = t.type === 'income' ? '+' : t.type === 'expense' ? '−' : '';
    const dateStr = formatDate(t.transaction_date);
    return `
      <li class="txn-item animate-in" style="animation-delay:${i * 30}ms">
        <div class="txn-icon ${t.type}">${icon}</div>
        <div class="txn-details">
          <div class="txn-desc">${t.description || t.type.charAt(0).toUpperCase() + t.type.slice(1)}</div>
          <div class="txn-category">${t.category_name || 'Uncategorized'}</div>
        </div>
        <div>
          <div class="txn-amount ${t.type}">${sign}${t.amount_formatted}</div>
          <div class="txn-date">${dateStr}</div>
        </div>
      </li>`;
  }).join('');
}

function renderPagination(data) {
  const container = document.getElementById('txn-pagination');
  if (data.total_pages <= 1) { container.innerHTML = ''; return; }

  let html = `<button class="pagination-btn" onclick="goToPage(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''}>‹</button>`;

  for (let p = 1; p <= data.total_pages; p++) {
    if (data.total_pages > 7 && Math.abs(p - data.page) > 2 && p !== 1 && p !== data.total_pages) {
      if (p === data.page - 3 || p === data.page + 3) html += '<span class="pagination-info">...</span>';
      continue;
    }
    html += `<button class="pagination-btn ${p === data.page ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
  }

  html += `<button class="pagination-btn" onclick="goToPage(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''}>›</button>`;
  container.innerHTML = html;
}

function goToPage(page) {
  txnPage = page;
  loadTransactions();
}

async function createTransaction(e) {
  e.preventDefault();
  try {
    const amountFloat = parseFloat(document.getElementById('txn-amount').value);
    const dateVal = document.getElementById('txn-date').value;

    const body = {
      wallet_id: document.getElementById('txn-wallet').value,
      type: document.getElementById('txn-type').value,
      amount: Math.round(amountFloat * 100),
      description: document.getElementById('txn-description').value || null,
      category_id: document.getElementById('txn-category').value || null,
    };
    if (dateVal) body.transaction_date = new Date(dateVal).toISOString();

    const res = await api('/transactions', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to add transaction');
    }

    showToast('Transaction added!', 'success');
    closeModal('txn-modal');
    document.getElementById('txn-amount').value = '';
    document.getElementById('txn-description').value = '';
    await loadWallets();
    navigateTo(currentPage);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function exportCSV() {
  try {
    const res = await api('/transactions/export?format=csv');
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('CSV exported!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ══════════════════════════════════════
//  CATEGORIES PAGE
// ══════════════════════════════════════

function renderCategories() {
  const container = document.getElementById('categories-list');
  container.innerHTML = categories.map((c, i) => `
    <div class="category-card animate-in" style="animation-delay:${i * 25}ms">
      <div class="category-icon" style="background:${c.color || '#6366f1'}22; color:${c.color || '#6366f1'}">
        ${getCategoryEmoji(c.icon)}
      </div>
      <div>
        <div class="category-name">${c.name}</div>
        <div class="category-type">${c.type}</div>
      </div>
    </div>
  `).join('');
}

async function createCategory(e) {
  e.preventDefault();
  try {
    const res = await api('/categories', {
      method: 'POST',
      body: JSON.stringify({
        name: document.getElementById('cat-name').value,
        type: document.getElementById('cat-type').value,
        color: document.getElementById('cat-color').value,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create category');
    }

    showToast('Category created!', 'success');
    closeModal('category-modal');
    document.getElementById('cat-name').value = '';
    await loadCategories();
    navigateTo(currentPage);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ══════════════════════════════════════
//  CHART
// ══════════════════════════════════════

function renderCategoryChart(txns) {
  const canvas = document.getElementById('category-chart');
  if (!canvas) return;

  // Aggregate expenses by category
  const catMap = {};
  txns.filter(t => t.type === 'expense').forEach(t => {
    const name = t.category_name || 'Uncategorized';
    catMap[name] = (catMap[name] || 0) + t.amount;
  });

  const labels = Object.keys(catMap);
  const data = Object.values(catMap);

  if (!labels.length) {
    labels.push('No expenses yet');
    data.push(1);
  }

  const colors = [
    '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f59e0b',
    '#10b981', '#06b6d4', '#3b82f6', '#f97316', '#14b8a6',
    '#a855f7', '#e11d48', '#84cc16', '#0ea5e9', '#d946ef',
  ];

  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#94a3b8',
            padding: 12,
            font: { family: 'Inter', size: 12 },
            usePointStyle: true,
            pointStyleWidth: 10,
          },
        },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          cornerRadius: 8,
          padding: 12,
          titleFont: { family: 'Inter', weight: 600 },
          bodyFont: { family: 'Inter' },
          callbacks: {
            label: ctx => {
              const val = ctx.parsed;
              return ` ${formatAmount(val)}`;
            }
          }
        }
      }
    }
  });
}

// ══════════════════════════════════════
//  MODALS
// ══════════════════════════════════════

function openModal(id) {
  document.getElementById(id).classList.add('active');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('active');
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('active');
  });
});

// ══════════════════════════════════════
//  TOASTS
// ══════════════════════════════════════

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ'}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(60px)';
    toast.style.transition = '300ms ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ══════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════

function formatAmount(paise) {
  const value = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(value);
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const now = new Date();
  const diff = now - d;

  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;

  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getCategoryEmoji(iconName) {
  const emojiMap = {
    'utensils': '🍽️', 'car': '🚗', 'shopping-bag': '🛍️',
    'heart-pulse': '❤️', 'graduation-cap': '🎓', 'gamepad': '🎮',
    'bolt': '⚡', 'shield': '🛡️', 'plane': '✈️', 'trending-up': '📈',
    'home': '🏠', 'repeat': '🔁', 'scissors': '✂️', 'gift': '🎁',
    'help-circle': '❓', 'banknote': '💵', 'laptop': '💻',
    'piggy-bank': '🐷', 'coins': '🪙', 'building': '🏢',
    'hand-heart': '🤝', 'rotate-ccw': '↩️', 'plus-circle': '➕',
    'arrow-right-left': '↔️',
  };
  return emojiMap[iconName] || '📂';
}

// ══════════════════════════════════════
//  BOOT
// ══════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
  if (token) {
    try {
      const res = await api('/auth/me');
      if (res.ok) {
        await enterDashboard();
        return;
      }
    } catch { /* ignore */ }
  }
  // Show auth view
  document.getElementById('auth-view').style.display = '';
  document.getElementById('dashboard-view').style.display = 'none';
});
