[app]

# ──────────────────────────────────────────────────────────
# Aurexis Core — M9 Mobile App Buildozer Configuration
# (c) 2026 Vincent Anderson
# ──────────────────────────────────────────────────────────

# App metadata
title = Aurexis Core
package.name = aurexiscore
package.domain = com.aurexis
version = 0.9.0

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,md

# Include the aurexis_lang source package
source.include_patterns = aurexis_lang/src/aurexis_lang/*.py

# ── Python / Kivy ──────────────────────────────────────────

# Requirements — order matters for recipe resolution
# opencv uses the python-for-android opencv recipe (includes numpy)
# PHASE 2: Testing all deps — diagnostic screen shows which work
requirements = python3,kivy,pillow,numpy,opencv

# Python version
osx.python_version = 3
android.python_version = 3

# ── Android build settings ─────────────────────────────────

# Target Samsung Galaxy S23 Ultra (arm64-v8a, Android 13+)
android.archs = arm64-v8a

# API levels
android.api = 33
android.minapi = 26
android.ndk_api = 26

# NDK version (r25b is stable with python-for-android)
android.ndk = 25b

# Permissions
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Allow backup
android.allow_backup = True

# Orientation — portrait locked
orientation = portrait

# Fullscreen
fullscreen = 0

# ── Appearance ─────────────────────────────────────────────

# App icon (will use Kivy default if not present)
# icon.filename = %(source.dir)s/data/icon.png

# Presplash
# presplash.filename = %(source.dir)s/data/presplash.png

# ── Build options ──────────────────────────────────────────

# Use copy rather than symlinking to work around WSL issues
# android.copy_libs = 1

# Gradle dependencies (none needed beyond defaults)
# android.gradle_dependencies =

# Accept SDK licenses automatically
android.accept_sdk_license = True

# Skip stripping to avoid issues with opencv native libs
android.no_byte_compile_python = False

# Log level for build debugging
log_level = 2

# ── Buildozer ──────────────────────────────────────────────

# Build directory (inside WSL)
# build_dir = ./.buildozer

# Warn on root
warn_on_root = 1

# ── iOS (not targeted for M9, placeholder) ─────────────────
# ios.kivy_ios_url = https://github.com/kivy/kivy-ios
# ios.kivy_ios_branch = master
