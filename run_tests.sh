#!/bin/bash
# Uruchamia wszystkie testy jednostkowe

cd "$(dirname "$0")"
python -m pytest tests/ -v
