#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# Aurexis Core — M9 WSL Bootstrap Script
# Run once inside WSL (Ubuntu) to set up the Android build
# environment. Usage:
#   bash setup_wsl.sh
#
# This installs: Python 3, pip, Buildozer, JDK 17, Cython,
# and all system-level build dependencies.
# Android SDK/NDK are downloaded automatically by Buildozer
# on the first build.
#
# (c) 2026 Vincent Anderson — Aurexis Core
# ──────────────────────────────────────────────────────────

set -e

echo "============================================="
echo "  Aurexis Core — M9 WSL Build Setup"
echo "============================================="
echo ""

# ── 1. System packages ────────────────────────────────────
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    zip \
    unzip \
    openjdk-17-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5 \
    cmake \
    libffi-dev \
    libssl-dev \
    automake \
    lld \
    2>/dev/null

echo "  Done."

# ── 2. Set JAVA_HOME ──────────────────────────────────────
echo "[2/5] Configuring Java..."
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
if ! grep -q "JAVA_HOME" ~/.bashrc 2>/dev/null; then
    echo "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64" >> ~/.bashrc
    echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
fi
echo "  JAVA_HOME=$JAVA_HOME"

# ── 3. Python packages ────────────────────────────────────
echo "[3/5] Installing Python packages..."
pip3 install --upgrade pip setuptools wheel 2>/dev/null || \
    pip3 install --upgrade pip setuptools wheel --break-system-packages
pip3 install buildozer cython==0.29.36 2>/dev/null || \
    pip3 install buildozer cython==0.29.36 --break-system-packages
echo "  Done."

# ── 4. Verify installations ───────────────────────────────
echo "[4/5] Verifying..."
echo "  Python:    $(python3 --version)"
echo "  pip:       $(pip3 --version | cut -d' ' -f1-2)"
echo "  Buildozer: $(buildozer version 2>/dev/null || echo 'installed')"
echo "  Java:      $(java -version 2>&1 | head -1)"
echo "  Cython:    $(python3 -c 'import Cython; print(Cython.__version__)' 2>/dev/null || echo 'installed')"

# ── 5. Done ────────────────────────────────────────────────
echo ""
echo "[5/5] Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. cd into mobile_app/"
echo "  2. Run: buildozer -v android debug"
echo "  3. First build takes 20-30 min (downloads SDK/NDK)"
echo "  4. APK lands in mobile_app/bin/"
echo ""
echo "============================================="
echo "  Ready to build Aurexis Core for Android"
echo "============================================="
