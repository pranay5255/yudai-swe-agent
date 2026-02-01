#!/bin/bash

# Script to launch the exploit results EDA notebook

echo "🚀 Launching Exploit Results EDA Notebook..."
echo ""
echo "The notebook will open in your browser at http://localhost:8888"
echo "Press Ctrl+C to stop the Jupyter server when done."
echo ""

cd "$(dirname "$0")"
uv run jupyter notebook exploit_results_eda.ipynb
