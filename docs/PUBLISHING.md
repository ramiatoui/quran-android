# Publishing

This guide covers three channels:

1. **GitHub Releases**: automatic, built by CI.
2. **F-Droid**: F-Droid builds the app from source and signs it.
3. **Aurora Store**: there is no upload. Aurora Store is an anonymous client for Google Play, so the app shows up in Aurora once it is on Google Play.

---

## 0. Before any release

1. Bump `versionCode` (+1) and `versionName` in `app/build.gradle.kts`.
2. Add a changelog file `fastlane/metadata/android/en-US/changelogs/<versionCode>.txt` (and `ar/changelogs/<versionCode>.txt`), max 500 characters.
3. Commit, then tag and push:
   ```sh
   git tag v1.6
   git push origin v1.6
   ```
   The `Build APK` workflow builds the APKs and attaches them to a GitHub Release for that tag.

### Release signing (GitHub Releases / Google Play)

Without signing secrets, CI uploads a debug APK and an **unsigned** release APK. To get a signed release APK:

```sh
keytool -genkeypair -v -keystore release.jks -alias mushaf \
  -keyalg RSA -keysize 4096 -validity 10000
base64 -w0 release.jks > release.jks.b64
```

Under **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `KEYSTORE_BASE64` | contents of `release.jks.b64` |
| `KEYSTORE_PASSWORD` | keystore password |
| `KEY_ALIAS` | `mushaf` |
| `KEY_PASSWORD` | key password |

Back up `release.jks` somewhere safe and never commit it. If you lose it, you can't ship updates under the same signature.

---

## 1. F-Droid

F-Droid builds from your source code and signs with its own key, so it doesn't use your keystore or the CI APKs.

### 1.1 Licensing check (blocker)

F-Droid only accepts apps whose code is free software, and it checks the assets too:

- **Code**: GPL-3.0-or-later ✅
- **Scheherazade New** (OFL) ✅, **quran-meta** (MIT) ✅, **Tanzil Hafs text** (CC BY 3.0) ✅
- **King Fahd Complex fonts** `uthmanic-*.ttf`: all rights reserved ⚠️
  The app can still be listed, but with the `NonFreeAssets` anti-feature (already in the template). For a clean listing, remove these fonts from the F-Droid build or replace them with freely licensed fonts.
- **Quranpedia texts** (Qalun, Warsh, Duri, Susi, Shu'bah): confirm the license and write it in `NOTICE.md`. Reviewers will ask about it.

### 1.2 Repository requirements

- [x] No proprietary dependencies (the project has no dependencies)
- [x] No network permission, no trackers
- [x] Fastlane metadata in `fastlane/metadata/android/{en-US,ar}/`
- [ ] Icon: `fastlane/metadata/android/en-US/images/icon.png` (512×512)
- [ ] Screenshots: `fastlane/metadata/android/en-US/images/phoneScreenshots/1.png`, `2.png`, …
- [ ] Changelog: `fastlane/metadata/android/en-US/changelogs/6.txt`
- [ ] A git tag `v<versionName>` for every release (F-Droid watches tags)
- [ ] Build files: F-Droid's `gradle` uses `distributionUrl` from `gradle/wrapper/gradle-wrapper.properties` (Gradle 8.7), which is already set

Optional but recommended: make the build reproducible so F-Droid can ship **your** signed APK (see https://f-droid.org/docs/Reproducible_Builds/).

### 1.3 Submit

1. Create an account on https://gitlab.com and fork https://gitlab.com/fdroid/fdroiddata.
2. Copy `docs/fdroid/app.mushaf.arabi.yml` from this repo to `metadata/app.mushaf.arabi.yml` in your fork.
3. Test locally (optional, needs the Android SDK):
   ```sh
   pip install fdroidserver
   cd fdroiddata
   fdroid readmeta
   fdroid lint app.mushaf.arabi
   fdroid build -v -l app.mushaf.arabi
   ```
4. Commit on a new branch (for example `app.mushaf.arabi`), push it, and open a Merge Request against `fdroid/fdroiddata`. Use the "App inclusion" MR template and fill in the checklist.
5. Answer reviewer comments. Once merged, the app usually appears in F-Droid within a few days.

After inclusion, new versions are picked up automatically: `UpdateCheckMode: Tags` + `AutoUpdateMode: Version` make F-Droid build every new `v*` tag. Just bump the version and push the tag.

Alternative before full inclusion: you can also host your own F-Droid repo, or list the GitHub releases in **IzzyOnDroid** (https://apt.izzysoft.de/fdroid/). It uses your signed APKs from GitHub Releases and is usually faster to get accepted.

---

## 2. Aurora Store (via Google Play)

Aurora Store has no developer console. It mirrors Google Play, so:

1. Create a Google Play Console developer account (one-time USD 25 fee): https://play.google.com/console
2. Create the app with package name `app.mushaf.arabi`.
3. Google Play requires an **AAB** (not an APK). Build it with:
   ```sh
   gradle bundleRelease
   ```
   and sign it with your upload key (the same keystore as above works). Enroll in **Play App Signing**.
4. `targetSdk` must meet Google's current minimum. Google raises it every year (35 or higher for new apps as of 2025-2026), so bump `targetSdk`/`compileSdk` from 34 before uploading.
5. Fill in the store listing (reuse the `fastlane/metadata` texts), content rating, the **Data safety** form (the app collects no data and has no internet permission), and a privacy policy URL (required even for apps with no data collection; a simple page in this repo is enough).
6. Personal developer accounts created after November 2023 must run a **closed test with at least 12 testers for 14 days** before production access.
7. Roll out to production. Within a day or so of going live, the app is searchable and installable in Aurora Store.

Note on fonts: the copyright of the King Fahd Complex fonts also applies on Google Play. Get permission or use free fonts before publishing.
