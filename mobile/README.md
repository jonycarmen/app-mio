# Mi App — Aplicación Móvil (Capacitor)

Wrapper nativo Android/iOS que carga la interfaz web del servidor FastAPI existente.
La app **no contiene el servidor**; solo se conecta a él. El usuario configura la URL la primera vez.

---

## Estructura del proyecto

```
mobile/
├── package.json          # Dependencias npm + Capacitor
├── capacitor.config.ts   # Configuración Capacitor
├── www/                  # Shell web (cargada por el WebView nativo)
│   ├── index.html        # Pantalla de config + loading + redirect
│   ├── css/app.css       # Estilos de la shell
│   └── js/app.js         # Lógica de conexión, plugins, cámara
├── android-patches/      # Archivos de configuración para Android
│   ├── AndroidManifest.xml
│   ├── strings.xml
│   └── build.gradle.reference
├── ios-patches/          # Archivos de configuración para iOS
│   └── Info.plist.patch
└── README.md             # Este archivo
```

Después de ejecutar `npx cap add android` y `npx cap add ios`, Capacitor creará las
carpetas `android/` e `ios/` automáticamente.

---

## Requisitos

| Herramienta | Versión mínima | Para |
|---|---|---|
| Node.js | 18 LTS | npm / Capacitor CLI |
| Android Studio | Hedgehog (2023.1) o superior | Build Android |
| JDK | 17 | Gradle |
| Xcode | 15+ | Build iOS (solo macOS) |
| CocoaPods | 1.13+ | Dependencias iOS |
| macOS | Ventura 13+ | Solo para iOS |

---

## Instalación y configuración inicial

```bash
# Desde la carpeta mobile/
cd mobile

# 1. Instalar dependencias
npm install

# 2. Añadir plataformas (solo la primera vez)
npm run add:android      # genera mobile/android/
npm run add:ios          # genera mobile/ios/   (solo macOS)

# 3. Aplicar parches de configuración
#    Android:
cp android-patches/AndroidManifest.xml android/app/src/main/AndroidManifest.xml
cp android-patches/strings.xml         android/app/src/main/res/values/strings.xml

#    iOS: abre ios/App/App/Info.plist en un editor y añade las claves de ios-patches/Info.plist.patch

# 4. Sincronizar archivos web con las plataformas
npm run sync:android
npm run sync:ios         # solo macOS
```

---

## Configurar la URL del servidor

### Durante el desarrollo (live-reload)

Edita `capacitor.config.ts` y descomenta el bloque `server`:

```typescript
server: {
  url: 'http://192.168.1.100:8000',   // IP de tu máquina con el servidor FastAPI
  cleartext: true,
}
```

Luego sincroniza:

```bash
npm run sync:android
```

### En producción (URL configurada por el usuario en la app)

Deja el bloque `server` comentado. La shell `www/index.html` pedirá la URL al usuario
la primera vez que abra la app y la guardará en el almacenamiento local del dispositivo.

---

## Android — Generar APK / AAB

### APK de debug (instalación directa)

```bash
npm run sync:android
npm run open:android       # abre Android Studio
```

Desde Android Studio:
- **Run > Run 'app'** → instala en dispositivo/emulador conectado.
- **Build > Build Bundle(s) / APK(s) > Build APK(s)** → genera APK de debug.
  - Ruta: `android/app/build/outputs/apk/debug/app-debug.apk`

### APK firmado para distribución

1. Genera un keystore (una sola vez):

```bash
keytool -genkey -v \
  -keystore mi-app-release.jks \
  -alias mi-app \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

2. Agrega la configuración de firma en `android/app/build.gradle`:

```groovy
android {
    signingConfigs {
        release {
            storeFile file('../../mi-app-release.jks')
            storePassword 'TU_CONTRASEÑA_KEYSTORE'
            keyAlias 'mi-app'
            keyPassword 'TU_CONTRASEÑA_KEY'
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
        }
    }
}
```

3. Genera el APK firmado:

```bash
cd android
./gradlew assembleRelease
```

APK generado: `android/app/build/outputs/apk/release/app-release.apk`

Para Google Play Store usa AAB:

```bash
./gradlew bundleRelease
# android/app/build/outputs/bundle/release/app-release.aab
```

### Instalar APK en un dispositivo Android

```bash
# Con adb (Android Debug Bridge, incluido en Android Studio):
adb install android/app/build/outputs/apk/debug/app-debug.apk

# O copia el APK al dispositivo y ábrelo desde el gestor de archivos.
# Necesitas habilitar "Instalar apps de fuentes desconocidas" en Ajustes > Seguridad.
```

---

## iOS — Generar IPA (solo macOS con Xcode)

```bash
npm run sync:ios
npm run open:ios           # abre Xcode
```

### Build para dispositivo físico

1. En Xcode: selecciona tu dispositivo en el selector de destino (arriba a la izquierda).
2. **Product > Run** (⌘R) → instala y ejecuta directamente.
3. Necesitas una cuenta de Apple Developer (gratuita para desarrollo en dispositivo propio).

### Build para distribución (App Store / TestFlight)

1. Configura el equipo de firma en Xcode:
   - Selecciona el proyecto `App` en el navegador.
   - **Signing & Capabilities** → elige tu equipo (Apple Developer Program requerido).
   - Asegúrate de que el Bundle Identifier coincida: `com.miapp.portal`.

2. Genera el archivo:
   - Selecciona **Any iOS Device** como destino.
   - **Product > Archive** → abre el Organizer cuando termina.
   - **Distribute App > App Store Connect** → sigue el asistente.

3. El IPA se sube a App Store Connect para distribución por TestFlight o App Store.

### Instalar IPA en dispositivo sin App Store (desarrollo)

```bash
# Con Apple Configurator 2 (macOS) o directamente desde Xcode Devices.
# O exportar un IPA de desarrollo en Xcode Organizer > Distribute > Development.
```

---

## Funcionalidades nativas implementadas

| Funcionalidad | Plugin | Estado |
|---|---|---|
| Configuración de URL del servidor | Preferences | ✅ Activo |
| Pantalla de carga / splash | SplashScreen | ✅ Activo |
| Status bar personalizada (azul) | StatusBar | ✅ Activo |
| Botón atrás Android | App | ✅ Activo |
| Cámara / galería para foto de perfil | Camera | ✅ Listo (llama a `window.MiApp.pickPhoto()`) |
| Deep links `miapp://` | Intent-filter / URL scheme | ✅ Configurado |
| Notificaciones push | PushNotifications | ⚙️ Preparado (requiere configurar FCM/APNs) |
| Detector de red | Network | ✅ Activo (reintento automático) |

### Usar la cámara desde el servidor FastAPI

En cualquier página del servidor, llama a la API nativa desde JavaScript:

```javascript
// Desde una página HTML servida por FastAPI:
const base64Img = await window.MiApp?.pickPhoto(false); // false = cámara, true = galería
if (base64Img) {
  // base64Img = "data:image/jpeg;base64,..."
  // Muéstrala o envíala al servidor con fetch/FormData
}
```

### Deep links

- Android: abre automáticamente si el dispositivo tiene la app instalada.
- iOS: configura Universal Links o usa el esquema `miapp://`.

Ejemplo: un enlace de invitación `miapp://invite/TOKEN` puede redirigirse a
`http://TU_SERVIDOR/register/TOKEN` dentro de la app.

---

## Scripts npm disponibles

```bash
npm run sync:android     # Copia www/ → android/ y actualiza plugins
npm run sync:ios         # Copia www/ → ios/ y actualiza plugins
npm run open:android     # Abre Android Studio
npm run open:ios         # Abre Xcode
npm run run:android      # Ejecuta en dispositivo/emulador Android conectado
npm run run:ios          # Ejecuta en dispositivo/simulador iOS
npm run doctor           # Diagnóstico del entorno Capacitor
```

---

## Notas de seguridad para producción

1. **Usar HTTPS**: el servidor debe tener un certificado TLS válido.
2. **Deshabilitar cleartext traffic**:
   - Android: elimina `android:usesCleartextTraffic="true"` del `AndroidManifest.xml`.
   - iOS: cambia `NSAllowsArbitraryLoads` a `false` en `Info.plist`.
3. **Comentar el bloque `server`** en `capacitor.config.ts` para producción.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| La app no carga la URL | Verifica que el servidor esté corriendo y en la misma red. Comprueba la IP con `ipconfig` (Windows) o `ifconfig` (Linux/macOS). |
| Error `net::ERR_CLEARTEXT_NOT_PERMITTED` (Android) | Asegúrate de que `android:usesCleartextTraffic="true"` está en el Manifest. |
| Error `ATS` en iOS | Verifica que `NSAllowsArbitraryLoads` está en `Info.plist`. |
| La cámara no abre | Comprueba que los permisos `NSCameraUsageDescription` están en Info.plist (iOS) y `CAMERA` en el Manifest (Android). |
| `npx cap sync` falla | Ejecuta `npm install` primero y verifica que Android Studio / Xcode están instalados. |
| Gradle build falla con JDK error | Instala JDK 17 y configura `JAVA_HOME`. |
