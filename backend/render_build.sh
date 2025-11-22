#!/usr/bin/env bash
# Install system dependencies
apt-get update
apt-get install -y ffmpeg

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p ../storage/uploads
mkdir -p ../storage/processed
mkdir -p ../storage/temp
mkdir -p ../storage/thumbnails