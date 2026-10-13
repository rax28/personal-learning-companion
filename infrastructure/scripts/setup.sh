#!/usr/bin/env bash
set -euo pipefail
npm install
python3 -m venv ai-backend/.venv
ai-backend/.venv/bin/pip install -r ai-backend/requirements.txt
