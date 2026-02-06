#!/bin/bash
source .venv/bin/activate

# Integrity Check
echo "Ejecutando verificaciones..."
python scripts/check_data_integrity.py
echo "---------------------------"

export FLASK_APP=src/web/app.py
export FLASK_ENV=development
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src/web"
flask run --host 0.0.0.0 --port 8501