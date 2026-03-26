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
function exitDemo() {
  window._demoMode = false;
  window._demoWallet = null;
  document.getElementById('cabinet').classList.add('hidden');
  document.getElementById('not-connected').classList.remove('hidden');
  document.getElementById('demo-badge').classList.add('hidden');
  // Hide exit demo button, show nothing (user not connected)
  const exitBtn = document.getElementById('exit-demo-btn');
  if (exitBtn) exitBtn.classList.add('hidden');
  clearChatLog();
}

async function loadDemoMode() {
  window._demoMode = true;
  window._demoWallet = 'demo';

  // Show cabinet, hide connect screen
  document.getElementById('not-connected').classList.add('hidden');
  document.getElementById('cabinet').classList.remove('hidden');
  document.getElementById('demo-badge').classList.remove('hidden');

  // Show exit-demo button in nav, hide disconnect button
  const exitBtn = document.getElementById('exit-demo-btn');
  if (exitBtn) exitBtn.classList.remove('hidden');
  const disconnectBtn = document.getElementById('disconnect-btn');
  if (disconnectBtn) disconnectBtn.classList.add('hidden');

  // Set avatar & name immediately (will update from API)
  document.getElementById('cab-name').textContent = 'Pavel Durov';
  document.getElementById('cab-avatar').src = 'images/avatars/durov.png';
  document.getElementById('cab-avatar').style.objectFit = 'cover';
  document.getElementById('cab-avatar').style.borderRadius = '50%';
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

  // Update mode toggle buttons
  const mode = p.mode || 'personal';
  window._currentMode = mode;
  updateModeUI(mode);

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
  const exitBtn = document.getElementById('exit-demo-btn');
  if (exitBtn) exitBtn.classList.add('hidden');
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

// ── Mode Switching ────────────────────────────────────────────────────────────
function updateModeUI(mode) {
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  if (document.getElementById('twin-mode')) {
    document.getElementById('twin-mode').textContent =
      mode === 'professional' ? 'Professional' : 'Personal';
  }
}

async function setMode(mode) {
  if (window._demoMode) return; // read-only in demo
  window._currentMode = mode;
  updateModeUI(mode);

  const walletAddr = window._walletAddr;
  if (!walletAddr) return;
  try {
    await fetch(`${API_URL}/api/set-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-wallet-address': walletAddr },
      body: JSON.stringify({ mode }),
    });
  } catch (e) { console.warn('setMode failed', e); }
}

// ── Hallucination Settings ────────────────────────────────────────────────────
async function saveHallucinationSettings() {
  // Demo mode: show info modal instead of saving
  if (window._demoMode) {
    document.getElementById('demo-lock-modal')?.classList.remove('hidden');
    return;
  }

  const settings = {
    show_uncertainty:      document.getElementById('ctrl-uncertainty')?.checked,
    refuse_low_confidence: document.getElementById('ctrl-refuse')?.checked,
    no_invent_memories:    document.getElementById('ctrl-no-invent')?.checked,
    custom_instructions:   document.getElementById('custom-instructions')?.value || '',
  };
  // Always save to localStorage as cache
  localStorage.setItem('hallucination_settings', JSON.stringify(settings));

  const btn = event?.target;
  const orig = btn?.textContent;

  // Push to API if wallet connected
  const walletAddr = window._walletAddr;
  if (walletAddr && !window._demoMode) {
    try {
      if (btn) btn.textContent = '⏳ Saving…';
      const res = await fetch(`${API_URL}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-wallet-address': walletAddr },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        if (btn) { btn.textContent = '✅ Saved!'; setTimeout(() => { btn.textContent = orig; }, 2000); }
      } else {
        if (btn) { btn.textContent = '⚠️ Saved locally'; setTimeout(() => { btn.textContent = orig; }, 2000); }
      }
    } catch (e) {
      if (btn) { btn.textContent = '⚠️ Saved locally'; setTimeout(() => { btn.textContent = orig; }, 2000); }
    }
  } else {
    if (btn) { btn.textContent = '✅ Saved!'; setTimeout(() => { btn.textContent = orig; }, 2000); }
  }
}

function loadHallucinationSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem('hallucination_settings') || '{}');
    if (document.getElementById('ctrl-uncertainty'))
      document.getElementById('ctrl-uncertainty').checked = saved.show_uncertainty ?? true;
    if (document.getElementById('ctrl-refuse'))
      document.getElementById('ctrl-refuse').checked = saved.refuse_low_confidence ?? false;
    if (document.getElementById('ctrl-no-invent'))
      document.getElementById('ctrl-no-invent').checked = saved.no_invent_memories ?? true;
    if (document.getElementById('custom-instructions') && saved.custom_instructions)
      document.getElementById('custom-instructions').value = saved.custom_instructions;
  } catch (e) { /* ignore */ }
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
    // Try to get source labels from metadata
    const labels = p.source_labels || [];
    renderSourcesList(p.sources || 0, labels);
  } catch (e) { /* ignore */ }
}

const SOURCE_TYPE_LABELS = {
  telegram_channel: '📢 Telegram channel',
  telegram_chat: '💬 Telegram chat',
  interview: '🎙 Interview',
  other: '📄 Document',
};

function renderSourcesList(count, labels = []) {
  const el = document.getElementById('sources-list');
  const paidCta = document.getElementById('source-paid-cta');
  const uploadForm = document.getElementById('source-upload-form');
  if (!el) return;

  if (count === 0) {
    el.innerHTML = `<p class="caption" style="opacity:.5;">${t('sources.noSources')}</p>`;
  } else {
    const items = Array.from({length: count}, (_, i) => {
      const label = labels[i];
      const typeName = label ? (SOURCE_TYPE_LABELS[label.type] || label.type) : '📂 Source';
      const comment = label?.comment ? ` — <span style="opacity:.6">${label.comment}</span>` : '';
      return `<div style="padding:12px 14px;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.15);border-radius:10px;margin-bottom:8px;font-size:13px;display:flex;align-items:center;gap:10px;">
        <span style="flex:1">${typeName} #${i+1}${comment}</span>
        <span style="font-size:11px;color:rgba(0,229,255,.7);background:rgba(0,229,255,.08);padding:3px 8px;border-radius:6px;">✅ Indexed</span>
      </div>`;
    }).join('');
    el.innerHTML = items;
  }

  // Show/hide upload form & paid CTA
  if (count >= MAX_SOURCES) {
    // Free tier maxed — hide upload form, show paid CTA
    if (uploadForm) uploadForm.style.display = 'none';
    if (paidCta) paidCta.style.display = '';
  } else {
    if (uploadForm) uploadForm.style.display = '';
    if (paidCta) paidCta.style.display = 'none';
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
  const sourceType = document.getElementById('source-type')?.value || 'telegram_channel';
  const sourceComment = document.getElementById('source-comment')?.value || '';

  btn.disabled = true;
  btn.textContent = '⏳ Uploading...';
  statusEl.textContent = t('sources.uploading');
  statusEl.style.color = 'rgba(0,229,255,.8)';

  try {
    const formData = new FormData();
    formData.append('file', _selectedSourceFile);
    formData.append('wallet_address', walletAddr);
    formData.append('source_type', sourceType);
    formData.append('source_comment', sourceComment);

    const res = await fetch(`${API_URL}/api/upload`, {
      method: 'POST',
      headers: { 'x-wallet-address': walletAddr },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    statusEl.textContent = `✅ ${data.message || 'Source uploaded!'} ${data.messages_indexed ? `(${data.messages_indexed} messages indexed)` : ''}`;
    statusEl.style.color = 'rgba(0,229,255,.9)';
    btn.textContent = '✅ Done';
    _selectedSourceFile = null;
    document.getElementById('source-selected').style.display = 'none';
    if (document.getElementById('source-comment')) document.getElementById('source-comment').value = '';

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

// ── Paid source modal ─────────────────────────────────────────────────────────
function openPaidSourceModal() {
  const modal = document.getElementById('paid-source-modal');
  if (!modal) return;
  const shortEl = document.getElementById('modal-wallet-short');
  if (shortEl && window._walletAddr) {
    const addr = window._walletAddr;
    shortEl.textContent = addr.slice(0, 8);
  }
  modal.classList.remove('hidden');
}
function closePaidSourceModal() {
  document.getElementById('paid-source-modal')?.classList.add('hidden');
}
function openTonPayment() {
  // Open TonConnect payment flow if available
  if (window.tonConnectUI) {
    alert('TON payment integration coming soon. Please send 1 TON manually to unlock the 3rd slot.');
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

  // Load saved hallucination settings
  loadHallucinationSettings();

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
window.setMode = setMode;
window.loadHallucinationSettings = loadHallucinationSettings;
window.openPaidSourceModal = openPaidSourceModal;
window.closePaidSourceModal = closePaidSourceModal;
window.openTonPayment = openTonPayment;
window.exitDemo = exitDemo;
window.closeDemoLockModal = closeDemoLockModal;
window.openAvatarPicker = openAvatarPicker;
window.handleAvatarSelect = handleAvatarSelect;

// ── Demo lock modal ────────────────────────────────────────────────────────────
function closeDemoLockModal() {
  document.getElementById('demo-lock-modal')?.classList.add('hidden');
}

// ── Avatar Upload ─────────────────────────────────────────────────────────────
function openAvatarPicker() {
  if (window._demoMode) return; // no avatar change in demo
  document.getElementById('avatar-file-input')?.click();
}

async function handleAvatarSelect(input) {
  const file = input?.files?.[0];
  if (!file) return;

  const walletAddr = window._walletAddr;
  if (!walletAddr) return;

  // Preview immediately
  const reader = new FileReader();
  reader.onload = (e) => {
    const avatar = document.getElementById('cab-avatar');
    if (avatar) avatar.src = e.target.result;
  };
  reader.readAsDataURL(file);

  // Upload to API
  try {
    const formData = new FormData();
    formData.append('avatar', file);
    const res = await fetch(`${API_URL}/api/avatar`, {
      method: 'POST',
      headers: { 'x-wallet-address': walletAddr },
      body: formData,
    });
    if (!res.ok) console.warn('Avatar upload failed');
  } catch (e) { console.warn('Avatar upload error', e); }
}
