import { CapacitorConfig } from '@capacitor/cli';

/**
 * Capacitor configuration for the FastAPI wrapper app.
 *
 * SERVER_URL is intentionally left as an empty string here because
 * the user sets it at runtime from the in-app settings screen.
 * The www/index.html shell reads localStorage and redirects.
 *
 * For a quick local test, you can override with:
 *   server: { url: 'http://192.168.1.100:8000', cleartext: true }
 * but remove it before generating a production build.
 */
const config: CapacitorConfig = {
  appId: 'com.miapp.portal',
  appName: 'Mi App',
  webDir: 'www',
  // ---------------------------------------------------------------------------
  // Uncomment the block below ONLY for live-reload / local development.
  // Replace the IP with the machine that is running the FastAPI server.
  // ---------------------------------------------------------------------------
  // server: {
  //   url: 'http://192.168.1.100:8000',
  //   cleartext: true,   // allows HTTP (non-HTTPS) on Android
  // },
  // ---------------------------------------------------------------------------
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#1e40af',   // blue-800 — match app brand color
      androidSplashResourceName: 'splash',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',               // white text on colored background
      backgroundColor: '#1e40af',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    Camera: {
      // Plugin is registered; permissions will be requested on first use
    },
  },
  android: {
    allowMixedContent: true,       // allows HTTP resources on HTTPS page in dev
    captureInput: true,
    webContentsDebuggingEnabled: false, // set true for dev debugging
  },
  ios: {
    contentInset: 'automatic',
    scrollEnabled: true,
    limitsNavigationsToAppBoundDomains: false, // allow any domain (user sets URL)
  },
};

export default config;
