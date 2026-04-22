#!/bin/bash
source .venv/bin/activate

# Check integrity silently (result only)
python3 scripts/check_data_integrity.py

export FLASK_APP=src/web/app.py
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src/web"

# Professional output
echo ""
echo "🚀 Dashboard listo en: http://localhost:8501"
echo "--------------------------------------------"

# Run Flask with reduced noise but keep it in foreground
# We remove 2>/dev/null so the process doesn't terminate immediately and we see errors
flask run --host 127.0.0.1 --port 8501
