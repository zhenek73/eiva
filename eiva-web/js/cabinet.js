/**
 * Eiva Cabinet — cabinet.js
 * Handles: demo mode, tab navigation, chat, TonConnect, profile loading
 */

'use strict';

const API_URL = 'https://api.eiva.space';

// ── Tab navigation ────────────────────────────────────────────────────────────
function showTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  const content = document.getElementById('tab-' + name);
  if (content) content.classList.remove('hidden');
  // Mark button active (support both event-based and direct call)
  const activeBtn = btn || (typeof event !== 'undefined' && event?.target);
  if (activeBtn) activeBtn.classList.add('active');
}

// ── Demo Mode ─────────────────────────────────────────────────────────────────
async function loadDemoMode() {
  window._demoMode = true;
  window._demoWallet = 'demo';

  // Show cabinet, hide connect screen
  document.getElementById('not-connected').classList.add('hidden');
  document.getElementById('cabinet').classList.remove('hidden');
  document.getElementById('demo-badge').classList.remove('hidden');

  // Set avatar & name immediately (will update from API)
  document.getElementById('cab-name').textContent = 'Pavel Durov';
  document.getElementById('cab-avatar').src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=durov&backgroundColor=0d1117';
  document.getElementById('cab-wallet').textContent = '🎭 Demo Mode — no wallet connected';

  // Welcome message in chat
  clearChatLog();
  appendChatBubble('twin',
    "Hello. I'm Pavel Durov's AI twin, built from his public posts and interviews. Ask me anything about Telegram, privacy, blockchain, or my philosophy.",
    'HIGH ✅', 'Pavel Durov');

  // Fetch real demo profile from API
  try {
    const res = await fetch(`${API_URL}/api/demo/profile`);
    if (res.ok) {
      const p = await res.json();
      updateProfileUI(p);
    }
  } catch (e) {
    console.warn('Demo profile load failed, using defaults', e);
    updateProfileUI({
      twin_name: 'Pavel Durov',
      personality_summary: 'Tech visionary, privacy advocate',
      communication_style: 'Direct, philosophical, minimalist.',
      topics: ['privacy', 'freedom', 'TON', 'blockchain', 'Telegram', 'discipline'],
      messages_indexed: 60,
      sources: 1,
      tier: 'silver',
      mode: 'demo',
    });
  }
}

function updateProfileUI(p) {
  const el = id => document.getElementById(id);

  if (el('cab-name') && p.twin_name) el('cab-name').textContent = p.twin_name;
  if (el('twin-messages')) el('twin-messages').textContent = p.messages_indexed || '—';
  if (el('twin-sources'))  el('twin-sources').textContent  = p.sources || '—';
  if (el('twin-mode'))     el('twin-mode').textContent     = p.mode ? p.mode.charAt(0).toUpperCase() + p.mode.slice(1) : 'Demo';

  // Update personality traits
  if (p.topics?.length && el('traits-list')) {
    el('traits-list').innerHTML = p.topics.map(t => `<span class="trait">${t}</span>`).join('');
  }

  // Confidence bar
  const pct = p.messages_indexed > 500 ? 90 : p.messages_indexed > 100 ? 75 : p.messages_indexed > 50 ? 60 : 40;
  setTimeout(() => {
    if (el('overall-bar'))  el('overall-bar').style.width = pct + '%';
    if (el('overall-pct')) el('overall-pct').textContent  = pct + '%';
  }, 400);

  // NFT card name
  if (el('nft-name') && p.twin_name) el('nft-name').textContent = p.twin_name;
}

// ── TonConnect Wallet ─────────────────────────────────────────────────────────
let tonConnectUI = null;

async function initTonConnectCabinet() {
  try {
    const { TonConnectUI } = window.TON_CONNECT_UI || {};
    if (!TonConnectUI) return;

    tonConnectUI = new TonConnectUI({
      manifestUrl: 'https://eiva.space/tonconnect-manifest.json',
      buttonRootId: null,
    });

    tonConnectUI.onStatusChange(wallet => {
      if (wallet) onWalletConnected(wallet);
    });

    // Restore previous session
    if (tonConnectUI.wallet) onWalletConnected(tonConnectUI.wallet);
  } catch (e) {
    console.error('TonConnect init error:', e);
  }
}

async function connectWalletCabinet() {
  if (!tonConnectUI) {
    alert('TonConnect is loading, please try again in a moment.');
    return;
  }
  try {
    await tonConnectUI.openModal();
  } catch (e) {
    console.error(e);
  }
}

function onWalletConnected(wallet) {
  const rawAddr = wallet.account?.address || '';
  window._demoMode = false;
  window._walletAddr = rawAddr;

  document.getElementById('not-connected').classList.add('hidden');
  document.getElementById('cabinet').classList.remove('hidden');
  document.getElementById('demo-badge').classList.add('hidden');

  // Show disconnect button, hide demo badge
  const disconnectBtn = document.getElementById('disconnect-btn');
  if (disconnectBtn) disconnectBtn.classList.remove('hidden');

  const short = rawAddr.slice(0, 6) + '...' + rawAddr.slice(-4);
  document.getElementById('cab-wallet').textContent = '🔗 ' + short;
  document.getElementById('cab-name').textContent = 'My Twin';

  // Load real profile
  loadProfileForWallet(rawAddr);
  // Load sources count
  loadSourcesCount(rawAddr);
}

async function disconnectWallet() {
  try {
    if (tonConnectUI) await tonConnectUI.disconnect();
  } catch (e) { /* ignore */ }
  window._walletAddr = null;
  window._demoMode = false;

  document.getElementById('cabinet').classList.add('hidden');
  document.getElementById('not-connected').classList.remove('hidden');

  const disconnectBtn = document.getElementById('disconnect-btn');
  if (disconnectBtn) disconnectBtn.classList.add('hidden');
}

async function loadProfileForWallet(walletAddr) {
  try {
    const res = await fetch(`${API_URL}/api/profile`, {
      headers: { 'x-wallet-address': walletAddr }
    });
    if (!res.ok) return; // no twin yet — that's fine
    const p = await res.json();
    updateProfileUI(p);
  } catch (e) {
    console.warn('Profile load error:', e);
  }
}

// ── Chat with Twin ─────────────────────────────────────────────────────────────
function clearChatLog() {
  const log = document.getElementById('chat-log');
  if (log) log.innerHTML = '';
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const msg = input?.value?.trim();
  if (!msg) return;

  const isDemo = !!window._demoMode;
  const walletAddr = window._walletAddr || 'demo';

  if (!isDemo && walletAddr === 'demo') {
    appendChatBubble('twin', '⚠️ Please connect your TON wallet or use Demo mode first.', '', 'EIVA');
    return;
  }

  input.value = '';
  appendChatBubble('user', msg);

  // Typing indicator
  const typingId = 'typing-' + Date.now();
  appendChatBubble('twin', '...', '', isDemo ? 'Pavel Durov' : 'Your Twin', typingId);

  try {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        wallet_address: walletAddr,
        demo_mode: isDemo,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Chat error');

    // Replace typing indicator with real reply
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    appendChatBubble('twin', data.reply, data.confidence, data.twin_name);
  } catch (err) {
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    appendChatBubble('twin', `⚠️ ${err.message}`, 'LOW ⚠️', 'Error');
  }
}

function appendChatBubble(role, text, confidence = '', name = '', id = '') {
  const log = document.getElementById('chat-log');
  if (!log) return;

  // Clear placeholder text on first message
  const placeholder = log.querySelector('[data-placeholder]');
  if (placeholder) placeholder.remove();

  const div = document.createElement('div');
  div.className = `chat-bubble ${role}`;
  if (id) div.id = id;
  div.innerHTML = `
    ${name ? `<div class="chat-name">${name}</div>` : ''}
    <div class="chat-text">${text.replace(/\n/g, '<br>')}</div>
    ${confidence ? `<div class="chat-confidence">${confidence}</div>` : ''}
  `;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

// ── Hallucination Settings ────────────────────────────────────────────────────
function addPreset(text) {
  const ta = document.getElementById('custom-instructions');
  if (ta) ta.value = (ta.value ? ta.value + '\n' : '') + text;
}

function saveHallucinationSettings() {
  const settings = {
    show_uncertainty:      document.getElementById('ctrl-uncertainty')?.checked,
    refuse_low_confidence: document.getElementById('ctrl-refuse')?.checked,
    no_invent_memories:    document.getElementById('ctrl-no-invent')?.checked,
    custom_instructions:   document.getElementById('custom-instructions')?.value,
  };
  localStorage.setItem('hallucination_settings', JSON.stringify(settings));
  const btn = event?.target;
  if (btn) {
    const orig = btn.textContent;
    btn.textContent = '✅ Saved!';
    setTimeout(() => { btn.textContent = orig; }, 2000);
  }
}

// ── Upload Sources ────────────────────────────────────────────────────────────
const MAX_SOURCES = 2;
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

let _selectedSourceFile = null;

async function loadSourcesCount(walletAddr) {
  try {
    const res = await fetch(`${API_URL}/api/profile`, {
      headers: { 'x-wallet-address': walletAddr }
    });
    if (!res.ok) return;
    const p = await res.json();
    renderSourcesList(p.sources || 0);
  } catch (e) { /* ignore */ }
}

function renderSourcesList(count) {
  const el = document.getElementById('sources-list');
  if (!el) return;
  if (count === 0) {
    el.innerHTML = `<p class="caption" style="opacity:.5" data-i18n="sources.noSources">${t('sources.noSources')}</p>`;
  } else {
    const items = Array.from({length: count}, (_, i) =>
      `<div style="padding:10px 14px;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.15);border-radius:8px;margin-bottom:8px;font-size:13px;">
        📂 Source ${i + 1} <span style="opacity:.5;margin-left:8px;">✅ Indexed</span>
       </div>`
    ).join('');
    el.innerHTML = items;
  }

  // Disable upload area if at max
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('source-file-input');
  const statusEl = document.getElementById('source-status');
  if (count >= MAX_SOURCES) {
    if (uploadArea) { uploadArea.style.opacity = '.4'; uploadArea.style.pointerEvents = 'none'; }
    if (fileInput) fileInput.disabled = true;
    if (statusEl) statusEl.textContent = t('sources.maxReached');
    statusEl.style.color = 'rgba(255,165,0,.8)';
  }
}

function handleSourceDrop(e) {
  e.preventDefault();
  document.getElementById('upload-area').classList.remove('drag-over');
  const file = e.dataTransfer?.files?.[0];
  if (file) selectSourceFile(file);
}

function handleSourceFileSelect(input) {
  const file = input?.files?.[0];
  if (file) selectSourceFile(file);
}

function selectSourceFile(file) {
  const statusEl = document.getElementById('source-status');

  if (!file.name.endsWith('.json')) {
    statusEl.textContent = t('sources.errJson');
    statusEl.style.color = '#ff6b6b';
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    statusEl.textContent = t('sources.errSize');
    statusEl.style.color = '#ff6b6b';
    return;
  }

  _selectedSourceFile = file;
  const kb = (file.size / 1024).toFixed(0);
  document.getElementById('source-filename').textContent = file.name;
  document.getElementById('source-filesize').textContent = `${kb} KB`;
  document.getElementById('source-selected').style.display = '';
  document.getElementById('source-upload-btn').style.display = '';
  statusEl.textContent = '';
}

async function uploadSource() {
  const walletAddr = window._walletAddr;
  if (!walletAddr || window._demoMode) {
    document.getElementById('source-status').textContent = t('sources.errNoWallet');
    return;
  }
  if (!_selectedSourceFile) {
    document.getElementById('source-status').textContent = t('sources.errNoFile');
    return;
  }

  const btn = document.getElementById('source-upload-btn');
  const statusEl = document.getElementById('source-status');
  btn.disabled = true;
  btn.textContent = '⏳ Uploading...';
  statusEl.textContent = t('sources.uploading');
  statusEl.style.color = 'rgba(0,229,255,.8)';

  try {
    const formData = new FormData();
    formData.append('file', _selectedSourceFile);
    formData.append('wallet_address', walletAddr);

    const res = await fetch(`${API_URL}/api/upload`, {
      method: 'POST',
      headers: { 'x-wallet-address': walletAddr },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    statusEl.textContent = `✅ ${data.message || 'Source uploaded!'} ${data.messages_indexed ? `(${data.messages_indexed} messages)` : ''}`;
    statusEl.style.color = 'rgba(0,229,255,.9)';
    btn.textContent = '✅ Done';
    _selectedSourceFile = null;
    document.getElementById('source-selected').style.display = 'none';

    // Refresh profile + sources count
    loadProfileForWallet(walletAddr);
    loadSourcesCount(walletAddr);
  } catch (err) {
    statusEl.textContent = `❌ ${err.message}`;
    statusEl.style.color = '#ff6b6b';
    btn.disabled = false;
    btn.textContent = t('sources.upload');
  }
}

// ── Mint Demo NFT ─────────────────────────────────────────────────────────────
function mintDurovNFT() {
  const btn = document.getElementById('mint-durov-btn');
  if (btn) { btn.textContent = '⏳ Opening Telegram...'; btn.disabled = true; }
  setTimeout(() => {
    window.open('https://t.me/eivatonbot?start=mint_durov', '_blank');
    if (btn) { btn.textContent = '✅ Check Telegram!'; btn.disabled = false; }
  }, 800);
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Wire connect button
  const connectBtn = document.getElementById('connect-wallet-btn');
  if (connectBtn) connectBtn.addEventListener('click', connectWalletCabinet);

  // Init TonConnect (for real wallet connect)
  initTonConnectCabinet();

  // Enter key in chat
  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') sendChatMessage();
    });
  }
});

// Expose globally for onclick= attributes in HTML
window.showTab = showTab;
window.loadDemoMode = loadDemoMode;
window.sendChatMessage = sendChatMessage;
window.addPreset = addPreset;
window.saveHallucinationSettings = saveHallucinationSettings;
window.mintDurovNFT = mintDurovNFT;
window.connectWalletCabinet = connectWalletCabinet;
window.disconnectWallet = disconnectWallet;
window.handleSourceDrop = handleSourceDrop;
window.handleSourceFileSelect = handleSourceFileSelect;
window.uploadSource = uploadSource;
