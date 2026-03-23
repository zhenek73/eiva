/**
 * Eiva Cabinet Page Logic
 * Handles tab navigation, demo mode, and settings
 */

function showTab(name) {
  // Hide all tabs
  document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
  // Remove active from all tab buttons
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

  // Show selected tab
  const content = document.getElementById('tab-' + name);
  if (content) content.classList.remove('hidden');

  // Mark button as active
  if (event?.target) {
    event.target.classList.add('active');
  }
}

function loadDemoMode() {
  document.getElementById('not-connected').classList.add('hidden');
  document.getElementById('cabinet').classList.remove('hidden');
  document.getElementById('demo-badge').classList.remove('hidden');
  document.getElementById('cab-name').textContent = 'Pavel Durov';
  document.getElementById('cab-avatar').src = 'https://api.dicebear.com/7.x/avataaars/svg?seed=durov&backgroundColor=0d1117';
  document.getElementById('cab-wallet').textContent = 'Demo Mode — no wallet connected';

  // Animate confidence bar
  setTimeout(() => {
    const bar = document.getElementById('overall-bar');
    const pct = document.getElementById('overall-pct');
    if (bar) bar.style.width = '87%';
    if (pct) pct.textContent = '87%';
  }, 400);
}

function addPreset(text) {
  const ta = document.getElementById('custom-instructions');
  if (ta) {
    ta.value = (ta.value ? ta.value + '\n' : '') + text;
  }
}

function saveHallucinationSettings() {
  const settings = {
    show_uncertainty: document.getElementById('ctrl-uncertainty')?.checked,
    refuse_low_confidence: document.getElementById('ctrl-refuse')?.checked,
    no_invent_memories: document.getElementById('ctrl-no-invent')?.checked,
    custom_instructions: document.getElementById('custom-instructions')?.value
  };
  localStorage.setItem('hallucination_settings', JSON.stringify(settings));
  const btn = event?.target;
  if (btn) {
    btn.textContent = '✅ Saved!';
    setTimeout(() => { btn.textContent = t('hall.save'); }, 2000);
  }
}

function mintDurovNFT() {
  const btn = document.getElementById('mint-durov-btn');
  if (btn) {
    btn.textContent = t('demo.mintingMsg');
    btn.disabled = true;
  }
  // Redirect to bot which handles actual minting
  setTimeout(() => {
    window.open('https://t.me/eivatonbot?start=mint_durov', '_blank');
    if (btn) {
      btn.textContent = '✅ Check Telegram!';
      btn.disabled = false;
    }
  }, 1500);
}

// Wallet connection simulation (for demo)
document.addEventListener('DOMContentLoaded', () => {
  const connectBtn = document.getElementById('connect-wallet-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', () => {
      // In production this would use @tonconnect/ui
      // For demo: simulate connection
      const addr = 'UQ' + Math.random().toString(36).substring(2, 20).toUpperCase();
      document.getElementById('not-connected').classList.add('hidden');
      document.getElementById('cabinet').classList.remove('hidden');
      document.getElementById('cab-wallet').textContent = addr.substring(0, 20) + '...';

      setTimeout(() => {
        const bar = document.getElementById('overall-bar');
        const pct = document.getElementById('overall-pct');
        if (bar) bar.style.width = '62%';
        if (pct) pct.textContent = '62%';
      }, 400);
    });
  }
});
