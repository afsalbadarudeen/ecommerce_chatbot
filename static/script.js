'use strict';

/* ── State (never written to any storage) ───────────────────── */
let messages       = [];     // conversation history for this session
let turnstileToken = null;   // single-use token; consumed on each send
let widgetId       = null;   // Turnstile widget handle for reset
let isSending      = false;  // prevents concurrent requests

/* ── DOM refs ────────────────────────────────────────────────── */
const chatArea   = document.getElementById('chat-area');
const welcomeEl  = document.getElementById('welcome');
const inputEl    = document.getElementById('message-input');
const sendBtn    = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const brandEl    = document.getElementById('brand');

/* ── Bootstrap: fetch public config then init Turnstile ──────── */
async function initTurnstile() {
  let siteKey  = '1x00000000000000000000AA'; // Cloudflare always-pass test key
  let companyName = 'ShopNest Support';

  try {
    const res = await fetch('/config');
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.turnstile_site_key) siteKey    = cfg.turnstile_site_key;
      if (cfg.company_name)       companyName = cfg.company_name + ' Support';
    }
  } catch { /* keep defaults */ }

  brandEl.textContent = companyName;
  document.title      = companyName;

  widgetId = turnstile.render('#turnstile-container', {
    sitekey: siteKey,
    size: 'compact',
    theme: 'light',
    callback(token) {
      turnstileToken = token;
      refreshSendBtn();
    },
    'expired-callback'() { turnstileToken = null; refreshSendBtn(); },
    'error-callback'()   { turnstileToken = null; refreshSendBtn(); },
  });
}

// Cloudflare calls this global after its script loads (?onload=onTurnstileReady)
window.onTurnstileReady = initTurnstile;

/* ── Send button state ───────────────────────────────────────── */
function refreshSendBtn() {
  sendBtn.disabled = isSending || !turnstileToken || inputEl.value.trim() === '';
}

/* ── UI helpers ──────────────────────────────────────────────── */
function escapeHtml(str) {
  const el = document.createElement('div');
  el.textContent = str;
  return el.innerHTML;
}

function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function setWelcomeVisible(visible) {
  welcomeEl.style.display = visible ? '' : 'none';
}

function autoResize() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
}

function appendBubble(role, text) {
  const row    = document.createElement('div');
  row.className = `message ${role}`;
  const bubble  = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
}

function appendError(text) {
  const el = document.createElement('div');
  el.className  = 'error-notice';
  el.textContent = text;
  chatArea.appendChild(el);
  scrollToBottom();
}

function showTyping() {
  const row    = document.createElement('div');
  row.id        = 'typing-row';
  row.className = 'message assistant typing';
  row.innerHTML = '<div class="bubble">'
    + '<span class="dot"></span>'
    + '<span class="dot"></span>'
    + '<span class="dot"></span>'
    + '</div>';
  chatArea.appendChild(row);
  scrollToBottom();
}

function removeTyping() {
  document.getElementById('typing-row')?.remove();
}

/* ── Error text by HTTP status ───────────────────────────────── */
function errorText(status) {
  if (status === 429) return "You've reached your daily message limit. Please try again tomorrow.";
  if (status === 400) return "Your message is too long. Please shorten it and try again.";
  if (status === 403) return "Verification failed. Please refresh the page and try again.";
  return "Something went wrong. Please try again in a moment.";
}

/* ── Core send logic ─────────────────────────────────────────── */
async function handleSend() {
  const text = inputEl.value.trim();
  if (!text || !turnstileToken || isSending) return;

  // Consume the token and lock the UI immediately
  const token    = turnstileToken;
  turnstileToken = null;
  isSending      = true;
  refreshSendBtn();

  // Show the user's bubble right away
  setWelcomeVisible(false);
  appendBubble('user', text);
  inputEl.value = '';
  autoResize();

  // Build the payload — user message not yet committed to `messages`
  const pendingMsg = { role: 'user', content: text };
  const body       = JSON.stringify({
    messages:        [...messages, pendingMsg],
    turnstile_token: token,
  });

  showTyping();

  try {
    const res  = await fetch('/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    });

    let data = {};
    try { data = await res.json(); } catch { /* malformed body */ }

    removeTyping();

    if (res.ok) {
      // Commit both turns to history only on success
      messages.push(pendingMsg, { role: 'assistant', content: data.reply ?? '' });
      appendBubble('assistant', data.reply ?? '');
    } else {
      appendError(errorText(res.status));
    }
  } catch {
    removeTyping();
    appendError("Network error. Please check your connection and try again.");
  } finally {
    isSending = false;
    // Ask Turnstile for a fresh token; callback will re-enable the button
    if (widgetId !== null) turnstile.reset(widgetId);
  }
}

/* ── New conversation ────────────────────────────────────────── */
function newConversation() {
  messages = [];

  // Clear chat area — keep the welcome element in the DOM, remove everything else
  [...chatArea.children].forEach(el => { if (el !== welcomeEl) el.remove(); });
  setWelcomeVisible(true);

  inputEl.value = '';
  autoResize();

  turnstileToken = null;
  isSending      = false;
  refreshSendBtn();

  if (widgetId !== null) turnstile.reset(widgetId);
}

/* ── Event listeners ─────────────────────────────────────────── */
sendBtn.addEventListener('click', handleSend);

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

inputEl.addEventListener('input', () => {
  autoResize();
  refreshSendBtn();
});

newChatBtn.addEventListener('click', newConversation);
