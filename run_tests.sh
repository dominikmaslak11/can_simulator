#!/bin/bash
source venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=html
echo "Raport pokrycia: htmlcov/index.html"
