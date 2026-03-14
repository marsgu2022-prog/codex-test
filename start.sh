#!/usr/bin/env bash

set -euo pipefail

python3 -m pip install -r requirements.txt
python3 -m uvicorn api:app --app-dir bazichart-engine --host 0.0.0.0 --port 8000
