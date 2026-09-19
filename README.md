# Quinary Watch Face

A Pixel Watch (Wear OS) watch face that shows the time in base 5 ("quinary"),
sibling to [BinaryWatchFace](https://github.com/pburney/BinaryWatchFace) —
same generator-driven toolchain, different number base and a fully custom
visual encoding.

## How it reads

Three rows — **H**our, **M**inute, **S**econd — each split into 2 or 3
"digit groups" (H needs 2 to cover 0-23, M/S need 3 each to cover 0-59), for
**8 digit groups / 32 sub-cells** total. Each digit group is 4 fixed-color
sub-cells; the **count of lit sub-cells encodes the digit's value 0-4**, in a
fixed lighting order (top-right → top-left → bottom-left → bottom-right) —
so 1 lit sub-cell is always the same top-right color, 2 lit is that plus
top-left, and so on. The color of a given position never changes; only
whether it's lit does, the same way a clock face's numeral positions never
move.

The three rows are also each a different **shape**, so the eye can tell them
apart at a glance even before reading the digits:

| row | shape | why |
|---|---|---|
| **H** | wide rectangles, barely rounded | sharpest corners |
| **M** | rounded rectangles | halfway between H and S |
| **S** | four-part circle (pie wedges) | fully round |

A fully-lit digit group fuses into one seamless shape (rectangle, rounded
rectangle, or circle) rather than four separate cells with visible seams.

**Cheat mode**: toggle the "Row labels" watch face setting to also show the
raw two-digit decimal H/M/S value to the right of each row, for sanity-
checking the base-5 reading against the actual time — genuinely useful, and
apparently intuitive to anyone used to counting money in 5s and 25s.

## How it works

Everything is generated from one spec in **`tools/gen_watchface.py`** — the
same "one Python file emits both the real WFF app and a browser preview"
architecture as BinaryWatchFace:

```
digit(value, place) = round( floor(value / 5^place) % 5 )
```

| output | purpose |
|---|---|
| `app/src/main/res/raw/watchface.xml` | the actual Wear OS watch face (WFF v2) |
| `preview.html` | a live browser preview — **no build required** |

```
python3 tools/gen_watchface.py
xdg-open preview.html          # see it now
```

## Building and installing

Same toolchain and steps as BinaryWatchFace — see `SETUP.md` in this repo
for the full build/install walkthrough (Android Studio SDK, Gradle wrapper,
wireless `adb` pairing to the watch, and how to validate `watchface.xml`
offline against Google's WFF schema before a device round-trip).

```bash
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Long-press the current face → **+ Add** → pick **Quinary**. Tap the gear to
toggle theme (light/dark) and row labels/cheat mode.

## Publishing

Same distribution path as BinaryWatchFace — Google Play (Watch face
category, Play Console account + signed release build + store listing +
privacy policy) and, optionally, F-Droid/IzzyOnDroid (this is a pure WFF
app: no code, no dependencies, no network, no trackers — about as close to
an ideal F-Droid candidate as an app gets).

**License:** Apache-2.0 (see `LICENSE`).

## Layout

```
QuinaryWatchFace/
├── tools/gen_watchface.py      the spec + generator (edit this)
├── preview.html                generated — open in a browser
├── app/
│   ├── build.gradle.kts
│   └── src/main/
│       ├── AndroidManifest.xml
│       └── res/
│           ├── raw/watchface.xml    generated
│           ├── xml/watch_face_info.xml
│           └── values/strings.xml
├── settings.gradle.kts
├── build.gradle.kts
└── gradle.properties
```
