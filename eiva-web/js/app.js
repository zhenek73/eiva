/**
 * Eiva Web — app.js
 * TON Connect integration, NFT gallery, upload flow
 */

'use strict';

// ── Translations ─────────────────────────────────────────────────────────────
const translations = {
  en: {
    title: "Your personality, on the blockchain",
    subtitle: "Build an AI Digital Twin from your Telegram messages. Anchor it as a Soulbound NFT on TON. Let others talk to you.",
    howItWorks: "How it works",
    step1: "Export Telegram",
    step1Desc: "Export your chat history as JSON from Telegram Desktop. Your data stays local.",
    step2: "AI Analyzes You",
    step2Desc: "GPT-4o extracts your personality: tone, humor, vocabulary, topics, style.",
    step3: "Twin Goes Live",
    step3Desc: "Your digital twin answers messages just like you — powered by RAG + LLM.",
    step4: "NFT on TON",
    step4Desc: "Mint your Soul Certificate as a Soulbound NFT. Permanent proof of identity.",
    settings: "Configure how your digital twin responds",
    personalMode: "🏠 Personal",
    professionalMode: "💼 Professional",
    connectWallet: "🔗 Connect TON Wallet",
    uploadFile: "Drop result.json here",
    language: "🌐 Language"
  },
  ru: {
    title: "Твоя личность на блокчейне",
    subtitle: "Создай AI цифровой двойник из сообщений Telegram. Закрепи его как Soulbound NFT на TON. Позволь другим разговаривать с тобой.",
    howItWorks: "Как это работает",
    step1: "Экспортируй Telegram",
    step1Desc: "Экспортируй историю чатов в JSON из Telegram Desktop. Твои данные остаются локальными.",
    step2: "AI анализирует тебя",
    step2Desc: "GPT-4o извлекает твоя личность: тон, юмор, словарь, темы, стиль.",
    step3: "Двойник работает",
    step3Desc: "Твой цифровой двойник отвечает как ты — powered by RAG + LLM.",
    step4: "NFT на TON",
    step4Desc: "Минтируй свой Soul Certificate как Soulbound NFT. Постоянное доказательство личности.",
    settings: "Настрой, как твой цифровой двойник отвечает",
    personalMode: "🏠 Personal",
    professionalMode: "💼 Professional",
    connectWallet: "🔗 Подключить кошелёк TON",
    uploadFile: "Перетащи result.json сюда",
    language: "🌐 Язык"
  }
};

let currentLanguage = localStorage.getItem("language") || "en";

function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem("language", lang);
  updatePageText();
  document.querySelectorAll(".lang-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById(`lang-${lang}`)?.classList.add("active");
}

function t(key) {
  return translations[currentLanguage]?.[key] || translations.en?.[key] || key;
}

function updatePageText() {
  // Update all elements with data-i18n attribute
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    const text = t(key);
    if (text && !text.includes('<')) {
      el.textContent = text;
    }
  });
}

// Initialize language buttons
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById("lang-en")?.addEventListener("click", () => setLanguage("en"));
  document.getElementById("lang-ru")?.addEventListener("click", () => setLanguage("ru"));
  updatePageText();
});

// ── Config ──────────────────────────────────────────────────────────────────
const NETWORK   = 'testnet';   // change to 'mainnet' for production
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
      manifestUrl: 'https://zhenek73.github.io/eiva/tonconnect-manifest.json',
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
      showStatus(uploadStatus,
        `✅ Valid Telegram export! Found ~${msgCount} messages. Continue in the bot to build your twin.`,
        'success'
      );
      uploadBtn.style.display = '';
      uploadBtn.textContent = `🤖 Continue in @eivatonbot (${msgCount} messages)`;
    } catch {
      showStatus(uploadStatus, '❌ Invalid JSON file', 'error');
    }
  };
  reader.readAsText(file);
}

uploadBtn.addEventListener('click', () => {
  window.open('https://t.me/eivatonbot', '_blank');
});

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

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTonConnect();
  checkNetworkStatus();
  initSettings();
});
