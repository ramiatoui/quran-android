plugins {
    id("com.android.application")
}

android {
    namespace = "app.mushaf.arabi"
    compileSdk = 34
    defaultConfig {
        applicationId = "app.mushaf.arabi"
        minSdk = 21            // Android 5.0+
        targetSdk = 34
        versionCode = 6
        versionName = "1.6"
    }
    // no Google-signed dependency metadata blob in the APK (F-Droid / reproducible builds)
    dependenciesInfo {
        includeInApk = false
        includeInBundle = false
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
}
// no dependencies on purpose: no Kotlin, no AppCompat -> nothing to conflict at dexing
