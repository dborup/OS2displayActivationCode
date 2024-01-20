#!/usr/bin/env bash

# Enable "exit on error" mode - script will exit if any command fails
set -e

# Install tesseract-ocr package using apt-get package manager
apt-get update
apt-get install tesseract-ocr -y

# Install the Pillow Python package using pip3
pip3 install Pillow

# Install the opencv-python Python package using pip3
pip3 install opencv-python

# Install the pytesseract Python package using pip (assumes the default Python interpreter)
pip install pytesseract




