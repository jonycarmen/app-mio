/**
 * app.js — Shell logic for the Capacitor wrapper app.
 *
 * Flow:
 *  1. On load → read saved serverUrl from Preferences / localStorage.
 *  2. If no URL saved → show Setup screen.
 *  3. If URL saved → show Loading screen, ping /api/health (or /),
 *     then redirect the WebView to serverUrl.
 *  4. If ping fails → show Error screen with retry + change-URL buttons.
 *
 * Capacitor plugins used:
 *  - @capacitor/preferences  (persistent key-value storage)
 *  - @capacitor/status-bar   (color + style)
 *  - @capacitor/app          (back-button handling on Android)
 *  - @capacitor/network      (online/offline detection)
 */

// ── Dynamic imports — Capacitor plugins are loaded at runtime ────────────────
// We use dynamic import() so the shell works in a plain browser too (for dev).

let Preferences, StatusBar, App, Network, Camera;

async function loadPlugins() {
  try {
    ({ Preferences } = await import('https://cdn.jsdelivr.net/npm/@capacitor/preferences@6/dist/esm/index.js'));
  } catch (_) { /* fallback to localStorage */ }

  try {
    ({ StatusBar } = await import('https://cdn.jsdelivr.net/npm/@capacitor/status-bar@6/dist/esm/index.js'));
  } catch (_) {}

  try {
    ({ App } = await import('https://cdn.jsdelivr.net/npm/@capacitor/app@6/dist/esm/index.js'));
  } catch (_) {}

  try {
    ({ Network } = await import('https://cdn.jsdelivr.net/npm/@capacitor/network@6/dist/esm/index.js'));
  } catch (_) {}

  try {
    ({ Camera } = await import('https://cdn.jsdelivr.net/npm/@capacitor/camera@6/dist/esm/index.js'));
  } catch (_) {}
}

// ── Storage helpers (Preferences → localStorage fallback) ────────────────────
const STORAGE_KEY = 'server_url';

async function getServerUrl() {
  if (Preferences) {
    const { value } = await Preferences.get({ key: STORAGE_KEY });
    return value || '';
  }
  return localStorage.getItem(STORAGE_KEY) || '';
}

async function saveServerUrl(url) {
  const clean = url.replace(/\/+$/, ''); // strip trailing slashes
  if (Preferences) {
    await Preferences.set({ key: STORAGE_KEY, value: clean });
  } else {
    localStorage.setItem(STORAGE_KEY, clean);
  }
  return clean;
}

async function clearServerUrl() {
  if (Preferences) {
    await Preferences.remove({ key: STORAGE_KEY });
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

// ── Screen management ─────────────────────────────────────────────────────────
const screens = {
  loading: document.getElementById('screen-loading'),
  setup:   document.getElementById('screen-setup'),
  error:   document.getElementById('screen-error'),
};

function showScreen(name) {
  Object.entries(screens).forEach(([key, el]) => {
    el.classList.toggle('screen-active', key === name);
  });
}

function setLoadingStatus(msg) {
  document.getElementById('loading-status').textContent = msg;
}

// ── Health check ──────────────────────────────────────────────────────────────
const HEALTH_PATHS = ['/api/health', '/user/login', '/'];
const TIMEOUT_MS   = 8000;

async function pingServer(baseUrl) {
  for (const path of HEALTH_PATHS) {
    try {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), TIMEOUT_MS);
      const res = await fetch(baseUrl + path, {
        method: 'HEAD',
        signal: controller.signal,
        cache: 'no-store',
      });
      clearTimeout(tid);
      if (res.ok || res.status === 302 || res.status === 401 || res.status === 403) {
        return { ok: true };
      }
    } catch (err) {
      // try next path
    }
  }
  return { ok: false };
}

// ── Redirect to server ────────────────────────────────────────────────────────
function redirectToServer(url) {
  // Replace the current page with the server URL.
  // Capacitor's WebView will load the server from here on.
  window.location.replace(url + '/user/login');
}

// ── Main connection flow ──────────────────────────────────────────────────────
async function connectToServer(url) {
  showScreen('loading');
  setLoadingStatus('Verificando conexión…');

  const result = await pingServer(url);

  if (result.ok) {
    setLoadingStatus('Conectado. Abriendo…');
    setTimeout(() => redirectToServer(url), 400);
  } else {
    showError(url, 'No se pudo conectar al servidor. Verifica que esté encendido y que estés en la misma red.');
  }
}

function showError(url, msg) {
  document.getElementById('error-message').textContent = msg;
  const urlEl = document.getElementById('error-url');
  urlEl.textContent = url ? 'URL: ' + url : '';
  showScreen('error');
}

// ── Setup form ────────────────────────────────────────────────────────────────
async function handleSaveUrl() {
  const input   = document.getElementById('server-url');
  const errEl   = document.getElementById('setup-error');
  const checkEl = document.getElementById('setup-checking');
  const btn     = document.getElementById('btn-save-url');

  errEl.classList.add('hidden');
  checkEl.classList.remove('hidden');
  btn.disabled = true;

  let url = input.value.trim();

  // Basic validation
  if (!url) {
    errEl.textContent = 'Por favor introduce la URL del servidor.';
    errEl.classList.remove('hidden');
    checkEl.classList.add('hidden');
    btn.disabled = false;
    return;
  }

  // Auto-add http:// if missing
  if (!/^https?:\/\//i.test(url)) {
    url = 'http://' + url;
    input.value = url;
  }

  // Validate URL format
  try { new URL(url); } catch (_) {
    errEl.textContent = 'URL inválida. Ejemplo: http://192.168.1.100:8000';
    errEl.classList.remove('hidden');
    checkEl.classList.add('hidden');
    btn.disabled = false;
    return;
  }

  checkEl.querySelector('.spinner-sm + *') // update label
  const ping = await pingServer(url);

  checkEl.classList.add('hidden');

  if (!ping.ok) {
    errEl.textContent = 'No se pudo conectar. Verifica la URL, que el servidor esté encendido y en la misma red.';
    errEl.classList.remove('hidden');
    btn.disabled = false;
    return;
  }

  const clean = await saveServerUrl(url);
  await connectToServer(clean);
  btn.disabled = false;
}

// ── Status bar ────────────────────────────────────────────────────────────────
async function configureStatusBar() {
  if (!StatusBar) return;
  try {
    await StatusBar.setBackgroundColor({ color: '#1e40af' });
    await StatusBar.setStyle({ style: 'DARK' });
    await StatusBar.show();
  } catch (_) {}
}

// ── Android back button ───────────────────────────────────────────────────────
function registerBackButton() {
  if (!App) return;
  App.addListener('backButton', ({ canGoBack }) => {
    if (!canGoBack) {
      App.exitApp();
    }
  });
}

// ── Network change listener ───────────────────────────────────────────────────
async function watchNetwork(savedUrl) {
  if (!Network) return;
  Network.addListener('networkStatusChange', async (status) => {
    if (status.connected && savedUrl) {
      // Back online — try to reconnect automatically
      const current = screens.error.classList.contains('screen-active');
      if (current) {
        await connectToServer(savedUrl);
      }
    }
  });
}

// ── Camera helper (exposed globally for server-side JS to call) ───────────────
window.MiApp = {
  /**
   * Opens the camera or gallery, returns a base64 JPEG string.
   * Called from the FastAPI frontend via window.MiApp.pickPhoto().
   */
  async pickPhoto(fromGallery = false) {
    if (!Camera) return null;
    try {
      const { CameraResultType, CameraSource } = await import('https://cdn.jsdelivr.net/npm/@capacitor/camera@6/dist/esm/index.js');
      const photo = await Camera.getPhoto({
        quality: 80,
        allowEditing: true,
        resultType: CameraResultType.Base64,
        source: fromGallery ? CameraSource.Photos : CameraSource.Camera,
      });
      return 'data:image/jpeg;base64,' + photo.base64String;
    } catch (err) {
      console.warn('Camera error:', err);
      return null;
    }
  },

  /**
   * Exposes the saved server URL so pages loaded from the server
   * can read it if needed.
   */
  async getServerUrl() {
    return await getServerUrl();
  },

  /**
   * Forces the app back to the Setup screen.
   * Can be called from a settings page on the server side.
   */
  async resetServerUrl() {
    await clearServerUrl();
    window.location.reload();
  },
};

// ── Bootstrap ─────────────────────────────────────────────────────────────────
async function init() {
  await loadPlugins();
  await configureStatusBar();
  registerBackButton();

  const savedUrl = await getServerUrl();

  if (!savedUrl) {
    showScreen('setup');
    return;
  }

  await watchNetwork(savedUrl);
  await connectToServer(savedUrl);
}

// ── Event listeners ───────────────────────────────────────────────────────────

// Setup form
document.getElementById('btn-save-url').addEventListener('click', handleSaveUrl);
document.getElementById('server-url').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') handleSaveUrl();
});

// Error screen — retry
document.getElementById('btn-retry').addEventListener('click', async () => {
  const url = await getServerUrl();
  if (url) {
    await connectToServer(url);
  } else {
    showScreen('setup');
  }
});

// Error screen — change URL
document.getElementById('btn-change-url').addEventListener('click', async () => {
  await clearServerUrl();
  showScreen('setup');
});

// Floating settings button (shown when app is running — not used by shell itself
// but kept so server-side pages can show it via postMessage or direct DOM)
document.getElementById('btn-settings-float').addEventListener('click', async () => {
  await clearServerUrl();
  window.location.reload();
});

// Start
document.addEventListener('DOMContentLoaded', init);
