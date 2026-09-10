import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.juancarlosburgos.cloudpulse"
    compileSdk = 36
    buildToolsVersion = "36.0.0"

    defaultConfig {
        applicationId = "com.juancarlosburgos.cloudpulse"
        minSdk = 26
        targetSdk = 36
        versionCode = 2
        versionName = "1.0.0"
        // URL configurable en build: ./gradlew assembleRelease -PapiUrl=https://...
        val api = (project.findProperty("apiUrl") as String?) ?: "https://api.juancarlosburgosautor.com"
        buildConfigField("String", "API_BASE_URL", "\"$api\"")
    }

    signingConfigs {
        val ksProps = rootProject.file("../play-package/keys/keystore.properties")
        if (ksProps.exists()) {
            create("release") {
                val p = Properties().apply {
                    ksProps.inputStream().use { load(it) }
                }
                storeFile = rootProject.file("../play-package/keys/" + p.getProperty("storeFile"))
                storePassword = p.getProperty("storePassword")
                keyAlias = p.getProperty("keyAlias")
                keyPassword = p.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("release")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { buildConfig = true }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
