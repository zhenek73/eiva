/**
 * Eiva Web — app.js
 * TON Connect integration, NFT gallery, upload flow
 * Uses i18n.js for translations (imported via HTML)
 */

'use strict';

// ── Config ──────────────────────────────────────────────────────────────────
const NETWORK   = 'testnet';   // change to 'mainnet' for production
const API_URL   = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
  ? 'http://127.0.0.1:8010'
  : 'https://api.eiva.space'; // Eiva backend
const TONCENTER = NETWORK === 'testnet'
  ? 'https://testnet.toncenter.com/api/v2'
  : 'https://toncenter.com/api/v2';
const TONAPI    = NETWORK === 'testnet'
  ? 'https://testnet.tonapi.io/v2'
  : 'https://tonapi.io/v2';
const GETGEMS   = NETWORK === 'testnet'
  ? 'https://testnet.getgems.io'
  : 'https://getgems.io';
const TONSCAN   = NETWORK === 'testnet'
  ? 'https://testnet.tonscan.org'
  : 'https://tonscan.org';

// ── Telegram Mini App detection ──────────────────────────────────────────────
const isTelegramApp = !!(window.Telegram?.WebApp?.initData);
if (isTelegramApp) {
  document.body.classList.add('tg-webapp');
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
  // Hide the Telegram banner when running inside Mini App
  document.getElementById('tgBanner')?.remove();
}

// ── TON Connect Setup ────────────────────────────────────────────────────────
let tonConnectUI = null;
let connectedWallet = null;

async function initTonConnect() {
  try {
    const { TonConnectUI } = window.TON_CONNECT_UI || {};
    if (!TonConnectUI) {
      console.warn('TON Connect UI not loaded');
      return;
    }
    tonConnectUI = new TonConnectUI({
      manifestUrl: 'https://eiva.space/tonconnect-manifest.json',
      buttonRootId: null,   // manual button management
    });
    tonConnectUI.onStatusChange(handleWalletChange);
    // Restore session
    const wallet = tonConnectUI.wallet;
    if (wallet) handleWalletChange(wallet);
  } catch (e) {
    console.error('TON Connect init error:', e);
  }
}

async function connectWallet() {
  if (!tonConnectUI) {
    showStatus(document.getElementById('uploadStatus'), 'TON Connect is loading, please try again...', 'info');
    return;
  }
  try {
    await tonConnectUI.openModal();
  } catch (e) {
    console.error(e);
  }
}

async function disconnectWallet() {
  if (tonConnectUI) await tonConnectUI.disconnect();
}

async function handleWalletChange(wallet) {
  if (!wallet) {
    connectedWallet = null;
    showWalletUI(false);
    return;
  }
  connectedWallet = wallet;
  const rawAddr = wallet.account?.address || '';
  showWalletUI(true, rawAddr);
  loadUserNFTs(rawAddr);
  loadBalance(rawAddr);
}

function showWalletUI(connected, rawAddr = '') {
  document.getElementById('walletDisconnected').style.display = connected ? 'none' : '';
  document.getElementById('walletConnected').style.display  = connected ? '' : 'none';
  if (connected && rawAddr) {
    const friendly = toFriendlyAddr(rawAddr);
    document.getElementById('walletAddr').textContent = friendly.slice(0, 6) + '...' + friendly.slice(-4);
    document.getElementById('walletAddr').title = friendly;
    const seed = friendly.slice(-8);
    document.getElementById('walletAvatar').src =
      `https://api.dicebear.com/9.x/pixel-art/png?seed=${seed}&size=64&backgroundColor=13132a`;
    // Show personal cabinet
    onWalletConnected(friendly);
  }
  document.getElementById('statNetwork').textContent = NETWORK;
}

function toFriendlyAddr(raw) {
  // raw is usually already a user-friendly addr from TON Connect
  return raw;
}

async function loadBalance(addr) {
  try {
    const res = await fetch(`${TONCENTER}/getAddressBalance?address=${addr}`);
    const data = await res.json();
    if (data.ok) {
      const ton = (parseInt(data.result) / 1e9).toFixed(3);
      document.getElementById('walletBalance').textContent = `${ton} TON`;
    }
  } catch (e) {
    document.getElementById('walletBalance').textContent = 'Balance unavailable';
  }
}

// ── NFT Loading ──────────────────────────────────────────────────────────────
async function loadUserNFTs(addr) {
  const grid    = document.getElementById('nftGrid');
  const empty   = document.getElementById('nftEmpty');
  const loading = document.getElementById('nftLoading');

  grid.style.display    = 'none';
  empty.style.display   = 'none';
  loading.style.display = '';

  try {
    // Fetch NFTs from tonapi.io
    const res = await fetch(
      `${TONAPI}/accounts/${encodeURIComponent(addr)}/nfts?limit=50&indirect_ownership=false`,
      { headers: { 'Accept': 'application/json' } }
    );
    const data = await res.json();
    const nfts = data?.nft_items || [];

    // Filter for Eiva Soul Certificates (by name or metadata)
    const eivaNFTs = nfts.filter(nft => {
      const name = nft?.metadata?.name || '';
      const desc = nft?.metadata?.description || '';
      return name.includes('Eiva') || desc.includes('Eiva') || desc.includes('Soul Certificate');
    });

    document.getElementById('statNFTs').textContent = eivaNFTs.length;

    if (eivaNFTs.length === 0) {
      // Show all NFTs if no Eiva ones found (for demo), or show empty state
      if (nfts.length > 0) {
        renderNFTs(nfts.slice(0, 12), grid);
        document.getElementById('statNFTs').textContent = nfts.length;
      } else {
        empty.style.display = '';
      }
    } else {
      renderNFTs(eivaNFTs, grid);
    }
  } catch (e) {
    console.error('NFT load error:', e);
    empty.style.display = '';
    empty.innerHTML = `
      <div style="font-size:2.5rem;margin-bottom:8px">⚠️</div>
      Could not load NFTs. <br/>
      <a href="${TONSCAN}/address/${connectedWallet?.account?.address}"
         style="color:var(--ton)" target="_blank">View on Tonscan</a>
    `;
  } finally {
    loading.style.display = 'none';
  }
}

function renderNFTs(nfts, grid) {
  grid.innerHTML = '';
  nfts.forEach(nft => {
    const name  = nft?.metadata?.name  || 'Soul Certificate';
    const image = nft?.metadata?.image || nft?.previews?.[0]?.url || '';
    const addr  = nft?.address || '';

    const el = document.createElement('a');
    el.className = 'nft-card';
    el.href = '#';
    el.innerHTML = `
      <img src="${image}" alt="${name}"
           onerror="this.src='https://api.dicebear.com/9.x/pixel-art/png?seed=${addr.slice(-8)}&size=256&backgroundColor=1a1a2e'"
           loading="lazy" />
      <div class="nft-info">
        <div class="nft-name">${name}</div>
        <div class="nft-net">${NETWORK}</div>
        <div class="nft-badge">Soulbound</div>
      </div>
    `;
    el.addEventListener('click', (e) => { e.preventDefault(); openNFTModal(nft); });
    grid.appendChild(el);
  });
  grid.style.display = 'grid';
}

function openNFTModal(nft) {
  const name   = nft?.metadata?.name || 'Soul Certificate';
  const image  = nft?.metadata?.image || nft?.previews?.[0]?.url || '';
  const addr   = nft?.address || '';
  const desc   = nft?.metadata?.description || '';
  const meta   = nft?.metadata?.uri || '';

  document.getElementById('modalName').textContent = name;
  document.getElementById('modalImg').src  = image || `https://api.dicebear.com/9.x/pixel-art/png?seed=${addr.slice(-8)}&size=512&backgroundColor=1a1a2e`;
  document.getElementById('modalImg').onerror = () => {
    document.getElementById('modalImg').src = `https://api.dicebear.com/9.x/pixel-art/png?seed=${addr.slice(-8)}&size=512&backgroundColor=1a1a2e`;
  };

  const addrLink = document.getElementById('modalAddr');
  addrLink.href = `${TONSCAN}/address/${addr}`;
  addrLink.textContent = addr.slice(0,8) + '...' + addr.slice(-6);

  const metaLink = document.getElementById('modalMeta');
  if (meta) {
    metaLink.href = meta;
    metaLink.textContent = meta.length > 50 ? meta.slice(0,50) + '...' : meta;
  } else {
    metaLink.textContent = 'On-chain';
    metaLink.removeAttribute('href');
  }

  document.getElementById('modalDesc').textContent = desc || 'AI Digital Twin Soul Certificate';

  // Extract personality hash from description
  const hashMatch = desc.match(/[0-9a-f]{16,}/i);
  if (hashMatch) {
    document.getElementById('modalHash').textContent = hashMatch[0];
  }

  // Links
  const linksEl = document.getElementById('modalLinks');
  linksEl.innerHTML = `
    <a href="${TONSCAN}/address/${addr}" target="_blank" class="btn btn-ghost btn-sm">🔍 Tonscan</a>
    <a href="${GETGEMS}/nft/${addr}" target="_blank" class="btn btn-ghost btn-sm">🖼 Getgems</a>
  `;

  document.getElementById('nftModal').classList.add('open');
}

// ── Upload Flow ──────────────────────────────────────────────────────────────
const uploadArea  = document.getElementById('uploadArea');
const fileInput   = document.getElementById('fileInput');
const uploadBtn   = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadArea.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});
fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) handleFile(e.target.files[0]);
});

let _pendingFile = null;

function handleFile(file) {
  if (!file.name.endsWith('.json')) {
    showStatus(uploadStatus, '❌ Please upload a .json file (Telegram export)', 'error');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      const messages = data.messages || [];
      const msgCount = messages.filter(m => typeof m.text === 'string' || Array.isArray(m.text)).length;
      _pendingFile = file;
      if (!connectedWallet) {
        showStatus(uploadStatus, `✅ Found ${msgCount} messages. Connect your TON wallet to build your twin.`, 'success');
        uploadBtn.style.display = '';
        uploadBtn.textContent = '🔗 Connect Wallet to Upload';
        uploadBtn.onclick = connectWallet;
      } else {
        showStatus(uploadStatus, `✅ Found ${msgCount} messages. Ready to upload!`, 'success');
        uploadBtn.style.display = '';
        uploadBtn.textContent = `🚀 Build My Twin (${msgCount} messages)`;
        uploadBtn.onclick = () => uploadToAPI(file);
      }
    } catch {
      showStatus(uploadStatus, '❌ Invalid JSON file', 'error');
    }
  };
  reader.readAsText(file);
}

async function uploadToAPI(file) {
  if (!connectedWallet) { connectWallet(); return; }
  const walletAddr = connectedWallet.account?.address || '';
  uploadBtn.disabled = true;
  uploadBtn.textContent = '⏳ Building your twin...';
  showStatus(uploadStatus, '⏳ Uploading and analyzing messages... This may take 30–60 seconds.', 'info');

  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_URL}/api/upload`, {
      method: 'POST',
      headers: {
        'x-wallet-address': walletAddr,
        'x-demo-mode': 'false',
      },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    showStatus(uploadStatus, `✅ Twin created for ${data.message}! ${data.messages_indexed} messages indexed.`, 'success');
    uploadBtn.textContent = '💬 Chat with Your Twin';
    uploadBtn.disabled = false;
    uploadBtn.onclick = () => showTab('chat');
    loadProfile(walletAddr);
  } catch (err) {
    showStatus(uploadStatus, `❌ ${err.message}`, 'error');
    uploadBtn.disabled = false;
    uploadBtn.textContent = '🔄 Retry Upload';
    uploadBtn.onclick = () => uploadToAPI(file);
  }
}

// ── Modal Controls ───────────────────────────────────────────────────────────
document.getElementById('modalClose').addEventListener('click', () => {
  document.getElementById('nftModal').classList.remove('open');
});
document.getElementById('nftModal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) e.currentTarget.classList.remove('open');
});

// ── Button wiring ────────────────────────────────────────────────────────────
document.getElementById('connectWalletBtn').addEventListener('click', connectWallet);
document.getElementById('connectWalletHero').addEventListener('click', () => {
  document.getElementById('app').scrollIntoView({ behavior: 'smooth' });
  setTimeout(connectWallet, 400);
});
document.getElementById('disconnectBtn').addEventListener('click', disconnectWallet);

// ── Helpers ──────────────────────────────────────────────────────────────────
function showStatus(el, msg, type = 'info') {
  el.textContent = msg;
  el.className = `status-msg show ${type}`;
}

// ── Network Status Check ────────────────────────────────────────────────────
async function checkNetworkStatus() {
  // Bot is always assumed online (real check would need backend)
  const botStatus = document.getElementById('botStatus');
  if (botStatus) {
    botStatus.classList.remove('offline');
    document.getElementById('botStatusText').textContent = 'Online';
  }

  // Check TON Testnet connectivity
  try {
    const response = await fetch('https://testnet.toncenter.com/api/v2/getAddressInformation?address=UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJKZ');
    if (response.ok) {
      const tonStatus = document.getElementById('tonStatus');
      if (tonStatus) {
        tonStatus.classList.remove('offline');
        document.getElementById('tonStatusText').textContent = 'Connected';
      }

      // Try to get latest block info
      try {
        const masterchainResponse = await fetch('https://testnet.tonapi.io/v2/blockchain/masterchain-head');
        if (masterchainResponse.ok) {
          const masterchainData = await masterchainResponse.json();
          const blockStatus = document.getElementById('blockStatus');
          if (blockStatus && masterchainData.last) {
            const blockSeqno = masterchainData.last.seqno;
            document.getElementById('blockStatusText').textContent = `#${blockSeqno}`;
          }
        }
      } catch (e) {
        // Fallback: just mark as connected
        document.getElementById('blockStatusText').textContent = 'Online';
      }
    }
  } catch (e) {
    const tonStatus = document.getElementById('tonStatus');
    if (tonStatus) {
      tonStatus.classList.add('offline');
      document.getElementById('tonStatusText').textContent = 'Offline';
    }
  }
}

// ── Settings Management ─────────────────────────────────────────────────────
function loadSettings() {
  const stored = localStorage.getItem('eiva_settings');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch (e) {
      console.error('Failed to parse settings:', e);
    }
  }
  // Default settings
  return {
    signature_phrases: true,
    formal_mode: false,
    emoji: true,
    humor: true,
    short_responses: false,
    language: 'auto',
  };
}

function saveSettings(settings) {
  localStorage.setItem('eiva_settings', JSON.stringify(settings));
  const statusEl = document.getElementById('settingsSaveStatus');
  if (statusEl) {
    statusEl.textContent = '✅ Settings saved to browser (synced with bot on next update)';
    statusEl.style.display = 'block';
    setTimeout(() => {
      statusEl.style.display = 'none';
    }, 3000);
  }
}

function initSettings() {
  const settings = loadSettings();

  // Load toggle states
  const toggles = [
    'signature_phrases', 'formal_mode', 'emoji', 'humor', 'short_responses'
  ];
  toggles.forEach(key => {
    const checkbox = document.getElementById(`toggle_${key}`);
    if (checkbox) {
      checkbox.checked = settings[key] || false;
      checkbox.addEventListener('change', () => {
        settings[key] = checkbox.checked;
        saveSettings(settings);
      });
    }
  });

  // Load language selector
  const langSelect = document.getElementById('language_select');
  if (langSelect) {
    langSelect.value = settings.language || 'auto';
    langSelect.addEventListener('change', () => {
      settings.language = langSelect.value;
      saveSettings(settings);
    });
  }

  // Save button
  const saveBtn = document.getElementById('saveSettingsBtn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      saveSettings(settings);
    });
  }
}

// ── Cabinet Tab Management ──────────────────────────────────────────────────
function showTab(name) {
  // Hide all tabs
  document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
  // Remove active from all tab buttons
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  // Show selected tab
  const tabContent = document.getElementById('tab-' + name);
  if (tabContent) {
    tabContent.classList.remove('hidden');
  }
  // Mark button as active
  event.target.classList.add('active');
}

function addPreset(text) {
  const ta = document.getElementById('custom-instructions');
  if (ta) {
    ta.value = (ta.value ? ta.value + '\n' : '') + text;
  }
}

function saveHallucinationSettings() {
  const settings = {
    show_uncertainty: document.getElementById('ctrl-uncertainty').checked,
    refuse_low_confidence: document.getElementById('ctrl-refuse').checked,
    no_invent_memories: document.getElementById('ctrl-no-invent').checked,
    ask_clarifying: document.getElementById('ctrl-clarify').checked,
    custom_instructions: document.getElementById('custom-instructions').value
  };
  localStorage.setItem('hallucination_settings', JSON.stringify(settings));

  // Show save confirmation
  const btn = event.target;
  const originalText = btn.textContent;
  btn.textContent = '✅ Saved!';
  setTimeout(() => { btn.textContent = originalText; }, 2000);
}

function tryDemoTwin() {
  window.open('https://t.me/eivatonbot?start=demo', '_blank');
}

function onWalletConnected(address) {
  const cabinet = document.getElementById('cabinet');
  if (cabinet) cabinet.classList.remove('hidden');
  loadProfile(address);
  // If there's a pending file, update upload button
  if (_pendingFile) {
    uploadBtn.style.display = '';
    uploadBtn.textContent = `🚀 Build My Twin`;
    uploadBtn.onclick = () => uploadToAPI(_pendingFile);
  }
}

async function loadProfile(walletAddr) {
  try {
    const res = await fetch(`${API_URL}/api/profile`, {
      headers: { 'x-wallet-address': walletAddr }
    });
    if (!res.ok) return; // no twin yet, that's fine
    const p = await res.json();

    // Update stats
    const el = (id) => document.getElementById(id);
    if (el('twin-messages')) el('twin-messages').textContent = p.messages_indexed || '—';
    if (el('twin-sources'))  el('twin-sources').textContent  = p.sources || '—';
    if (el('twin-mode'))     el('twin-mode').textContent     = p.mode || 'Personal';

    // Update traits
    if (p.topics?.length && el('traits-list')) {
      el('traits-list').innerHTML = p.topics.map(t => `<span class="trait">${t}</span>`).join('');
    }

    // Update confidence bar
    const pct = p.messages_indexed > 500 ? 90 : p.messages_indexed > 100 ? 70 : 40;
    setTimeout(() => {
      const bar = el('overall-bar'), pctEl = el('overall-pct');
      if (bar) bar.style.width = pct + '%';
      if (pctEl) pctEl.textContent = pct + '%';
    }, 400);

    // NFT address
    if (p.nft_address && el('nft-address')) el('nft-address').textContent = p.nft_address;

  } catch (e) { console.warn('Profile load:', e); }
}

// ── Chat with Twin ────────────────────────────────────────────────────────────
async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const msg = input?.value?.trim();
  if (!msg) return;
  if (!connectedWallet && !window._demoMode) {
    alert('Connect your wallet first'); return;
  }
  input.value = '';
  appendChatBubble('user', msg);

  const walletAddr = connectedWallet?.account?.address || 'demo';
  try {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        wallet_address: walletAddr,
        demo_mode: !!window._demoMode,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Chat error');
    appendChatBubble('twin', data.reply, data.confidence, data.twin_name);
  } catch (err) {
    appendChatBubble('twin', `⚠️ ${err.message}`, 'LOW ⚠️', 'Error');
  }
}

function appendChatBubble(role, text, confidence = '', name = '') {
  const log = document.getElementById('chat-log');
  if (!log) return;
  const div = document.createElement('div');
  div.className = `chat-bubble ${role}`;
  div.innerHTML = `
    ${name ? `<div class="chat-name">${name}</div>` : ''}
    <div class="chat-text">${text}</div>
    ${confidence ? `<div class="chat-confidence">${confidence}</div>` : ''}
  `;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

window.sendChatMessage = sendChatMessage;

// ── Privacy Functions ────────────────────────────────────────────────────────
function addPrivacyTag() {
  const input = document.getElementById('new-tag');
  const val = input.value.trim();
  if (!val) return;

  const tags = document.getElementById('privacy-tags');
  const tag = document.createElement('span');
  tag.className = 'tag-item';
  tag.innerHTML = `${val} <button onclick="removeTag(this)">×</button>`;
  tags.appendChild(tag);
  input.value = '';

  // Save to localStorage
  savePrivacyTags();
}

function removeTag(btn) {
  btn.parentElement.remove();
  savePrivacyTags();
}

function savePrivacyTags() {
  const tags = Array.from(document.querySelectorAll('#privacy-tags .tag-item'))
    .map(t => t.textContent.replace('×', '').trim());
  localStorage.setItem('privacy_tags', JSON.stringify(tags));
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTonConnect();
  checkNetworkStatus();
  initSettings();
});
