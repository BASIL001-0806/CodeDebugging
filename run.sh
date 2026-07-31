#!/bin/bash
cd "$(dirname "$0")"
echo "Installing dependencies..."
pip install -r requirements.txt -q
echo "Seeding database..."
python seed_data.py
echo "Starting Flask server..."
python app.py
