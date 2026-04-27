#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Chrome for Selenium/undetected-chromedriver
# We use the official Google Chrome binary for Linux
if [[ ! -d $STORAGE_DIR/chrome ]]; then
    echo "... Installing Chrome ..."
    mkdir -p $STORAGE_DIR/chrome
    cd $STORAGE_DIR/chrome
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    dpkg -x google-chrome-stable_current_amd64.deb .
    cd $HOME/project/src # Back to project root
fi

# Set Environment Variables for Chrome
export PATH=$PATH:$STORAGE_DIR/chrome/opt/google/chrome
