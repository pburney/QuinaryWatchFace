# Android dev environment setup (Toussaint)

Identical toolchain to [BinaryWatchFace](https://github.com/pburney/BinaryWatchFace)
— this project was scaffolded directly from it, same machine, same SDK. Full
detail lives in that repo's `SETUP.md`; this is the short version plus
anything Quinary-specific.

**Android Studio** (`~/bin/android-studio`) provisioned `~/Android/Sdk` —
platform `android-37.0`, build-tools `36.0.0`, `platform-tools` (`adb`).
`local.properties` (gitignored) points at it:
```
sdk.dir=/home/developer/Android/Sdk
```

**Gradle wrapper is committed** (`./gradlew`, `gradle/wrapper/`, pinned to
8.9) — no manual Gradle install needed.

## Build

```bash
cd /data/BUSINESS/Burnilab/QuinaryWatchFace
./gradlew :app:assembleDebug
# -> app/build/outputs/apk/debug/app-debug.apk
```

Use the **debug** build for sideloading — same reasoning as BinaryWatchFace
(a fully unsigned release APK fails `INSTALL_PARSE_FAILED_NO_CERTIFICATES`;
AGP's debug keystore installs fine on real devices; release signing for Play
Store submission is a separate, later step).

## Install on the Pixel Watch (wireless — no USB port)

```bash
# Watch: Settings -> System -> About -> tap "Build number" 7x to unlock
#        Developer options, then enable "ADB debugging" and
#        "Wireless debugging" -> "Pair new device" for a pairing IP:port + code
ADB=/home/developer/Android/Sdk/platform-tools/adb
$ADB pair <watch-ip>:<pair-port>      # 6-digit code shown on watch
$ADB devices -l                        # confirms it (often auto-connects via mDNS)
$ADB install -r app/build/outputs/apk/debug/app-debug.apk
```
On the watch: long-press the current face -> **+ Add** -> **Quinary** -> tap
the gear to toggle theme / row labels (cheat mode).

**Wireless adb has been flaky in practice** — if a connection drops mid
session, `adb kill-server && adb start-server && adb mdns services` usually
rediscovers the watch, then `adb connect <ip>:<port>` with the freshly
reported address (the port changes each reconnect, don't reuse a cached one).

## Validating watchface.xml offline

Same validator as BinaryWatchFace — clone once, reuse for both projects:
```bash
git clone --depth 1 https://github.com/google/watchface.git /tmp/wff-validator-src
cd /tmp/wff-validator-src/third_party/wff/specification/validator
mkdir out
javac -cp "$(find libs -name '*.jar' | tr '\n' ':')" -d out $(find src/main -name '*.java')
(cd ../documents && zip -qr ../validator/out/docs.zip .)
java -cp "$(find libs -name '*.jar' | tr '\n' ':')out" \
  com.samsung.watchface.DWFValidationApplication 4 \
  /data/BUSINESS/Burnilab/QuinaryWatchFace/app/src/main/res/raw/watchface.xml
```
This is ephemeral (`/tmp` — gone between sessions), re-clone as needed.

## Quinary-specific WFF notes

Everything BinaryWatchFace's `SETUP.md` documents (the required
`watch_face_info.xml` for gallery listing, `alpha` can't take a conditional
expression, `displayName` uses bare string-resource names, `ComplicationSlot`
must be a direct child of `<Scene>`) applies here unchanged — this project
never needed to relearn any of it. Two things that *were* new ground here:

- **`GREATER_THAN` as a `Compare` operator** — BinaryWatchFace only ever used
  `EQUALS` (via `% 2`/`% 10` bit/digit flags). Quinary's "count of lit
  sub-cells encodes the digit" design needs `digit > k` per sub-cell (k =
  0..3) — confirmed valid against the offline XSD validator and working
  on-device.
- **`<Scene>` paints children in document order** — a full-canvas theme
  background declared *after* the `ComplicationSlot` elements silently
  painted over them every frame (data was always computed correctly; only
  the paint was buried). Fixed by moving the complication declarations after
  the theme block. See `../<memory>/project_quinarywatchface.md` for the
  full root-cause writeup if this project's memory is available, or the
  `History` page on this project's Product page in the `bws` graph.
