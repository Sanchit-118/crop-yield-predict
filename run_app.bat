@echo off
cd /d "%~dp0"
python generate_dataset.py
python app.py
