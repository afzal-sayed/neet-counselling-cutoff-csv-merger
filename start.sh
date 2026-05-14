#!/usr/bin/env bash
set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

echo "Starting NEET PG Merger at http://127.0.0.1:5000"
python app.py
