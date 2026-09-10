# CloudPulse — Android client

A single-Activity Kotlin app. No architecture framework on purpose: the interesting part of this repository is
the backend and the deployment, and a reader should be able to follow the client in one screen.

## Structure

```
android/
├── app/src/main/
│   ├── java/com/juancarlosburgos/cloudpulse/MainActivity.kt   # UI + networking (the whole client)
│   ├── res/layout/activity_main.xml                           # Material 3 dark layout
│   ├── res/drawable/ic_launcher_foreground.xml                # adaptive icon (vector)
│   └── AndroidManifest.xml                                    # INTERNET permission only
├── app/build.gradle.kts                                       # AGP 8.13, Kotlin 2.2, compileSdk 36
└── gradle.properties
```

## Design decisions

| Decision | Reason |
|---|---|
| Views + XML instead of Compose | Zero extra compiler configuration; the layout is inspectable in the repository as XML |
| OkHttp + `org.json`, no Retrofit/Moshi | Three endpoints and a flat JSON object do not justify a code-generation layer |
| Coroutines with `Dispatchers.IO` | Network work off the main thread without a callback pyramid; the UI updates on `Dispatchers.Main` |
| 8-second connect/read timeouts | A dead backend must surface as an explicit offline state in seconds, not as a spinner |
| 15-second auto-refresh while foregrounded, cancelled in `onPause` | Live data without leaking work while the user is elsewhere |
| Missing JSON field renders `—` | The UI degrades field by field; it never crashes on an unexpected payload |
| API base URL injected at build time (`-PapiUrl=…`) | The same source builds against local, staging or production hosts; no rebuild of logic, no hardcoded IPs |

## Build

```bash
# requires JDK 17 and Android SDK platform 36 + build-tools 36.0.0
echo "sdk.dir=$ANDROID_HOME" > local.properties

./gradlew assembleDebug                                    # debug APK
./gradlew bundleRelease -PapiUrl=https://api.example.com    # signed AAB for Google Play
```

Release signing reads `play-package/keys/keystore.properties` (git-ignored). Without it, the release build is
produced unsigned — which is the correct behaviour for a fork.

## Requirements

- `minSdk 26` (Android 8.0) — covers adaptive icons without shipping legacy PNG densities
- `targetSdk 36`, only the `INTERNET` permission, no ads/analytics SDKs
