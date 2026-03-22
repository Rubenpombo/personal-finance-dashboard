#!/bin/bash
source .venv/bin/activate

# Integrity Check
echo "Ejecutando verificaciones de robustez..."
python scripts/check_data_integrity.py
echo "---------------------------"

export FLASK_APP=src/web/app.py
export FLASK_ENV=development
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src/web"

# Seguridad: Escuchar solo en localhost (127.0.0.1)
echo "Lanzando dashboard en http://localhost:8501..."
flask run --host 127.0.0.1 --port 8501
