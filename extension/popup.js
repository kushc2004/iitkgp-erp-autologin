'use strict';

const $ = (id) => document.getElementById(id);
const els = {
  signin: $('signin'),
  open: $('open'),
  log: $('log'),
  error: $('error'),
  promptAnswer: $('prompt-answer'),
  questionText: $('question-text'),
  answerInput: $('answer-input'),
  otpPrompt: $('prompt-otp'),
  otpInput: $('otp-input'),
  roll: $('roll'),
  password: $('password'),
  gmail: $('gmail'),
  save: $('save'),
  saved: $('saved'),
};

let loadedSettings = null;
let currentState = null;

function render(state) {
  if (!state) return;
  currentState = state;

  const running = state.phase === 'running';
  els.signin.disabled = running || !!state.awaiting;
  els.signin.textContent = running ? 'Signing in...' : 'Sign in to ERP';

  els.promptAnswer.style.display = state.awaiting === 'answer' ? 'block' : 'none';
  if (state.awaiting === 'answer') {
    els.questionText.textContent = state.question || '';
    els.answerInput.focus();
  }

  els.otpPrompt.style.display = state.awaiting === 'otp' ? 'block' : 'none';
  if (state.awaiting === 'otp') els.otpInput.focus();

  const lines = state.log || [];
  els.log.textContent = lines.join('\n');
  els.log.scrollTop = els.log.scrollHeight;

  els.error.textContent = state.phase === 'error'
    ? (state.error || 'Something went wrong.')
    : '';
}

function send(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(message, (response) => resolve(response));
    } catch (e) {
      resolve(null);
    }
  });
}

async function refresh() {
  const response = await send({ type: 'snapshot' });
  if (!response) return;
  if (response.state) render(response.state);
  if (response.settings) fillSettings(response.settings);
}

// Fill the form only when it is still untouched, so typing is never clobbered
// by a background snapshot arriving mid-edit.
function fillSettings(settings) {
  loadedSettings = settings || {};
  if (els.roll.value || els.password.value) return;
  els.roll.value = loadedSettings.rollNumber || '';
  els.password.value = loadedSettings.password || '';
  els.gmail.value = String(loadedSettings.gmailAccount == null ? 0 : loadedSettings.gmailAccount);
}

async function saveClicked() {
  const settings = {
    rollNumber: els.roll.value.trim(),
    password: els.password.value,
    gmailAccount: Number(els.gmail.value) || 0,
    answers: (loadedSettings && loadedSettings.answers) || {},
  };
  await send({ type: 'save-settings', settings });
  els.saved.textContent = 'Saved - ready to sign in.';
  setTimeout(() => { els.saved.textContent = ''; }, 2500);
}

els.signin.addEventListener('click', async () => {
  els.signin.disabled = true;
  await send({ type: 'start-login' });
});

els.open.addEventListener('click', () => {
  send({ type: 'open-erp' });
});

const checkNow = $('check-now');
if (checkNow) checkNow.addEventListener('click', () => send({ type: 'check-now' }));

if (els.save) els.save.addEventListener('click', saveClicked);

document.querySelectorAll('[data-submit]').forEach((button) => {
  button.addEventListener('click', () => {
    const kind = button.dataset.submit;
    const input = kind === 'answer' ? els.answerInput : els.otpInput;
    const value = (input.value || '').trim();
    if (!value) return;
    send({ type: kind === 'answer' ? 'submit-answer' : 'submit-otp', value });
    input.value = '';
  });
});

[els.answerInput, els.otpInput].forEach((input) => {
  if (!input) return;
  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    const kind = input.id === 'answer-input' ? 'answer' : 'otp';
    const value = (input.value || '').trim();
    if (!value) return;
    send({ type: kind === 'answer' ? 'submit-answer' : 'submit-otp', value });
    input.value = '';
    event.preventDefault();
  });
});

chrome.runtime.onMessage.addListener((message) => {
  if (message && message.type === 'state-update') render(message.state);
});

refresh();
