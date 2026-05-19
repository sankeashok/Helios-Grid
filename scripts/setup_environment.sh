#!/bin/bash

# Helios-Grid Environment Setup Script
# This script activates the virtual environment and installs dependencies

echo "☀️ Helios-Grid Environment Setup"
echo "================================"

# Check if virtual environment exists
if [ ! -f "helios-grid-env/bin/activate" ]; then
    echo "🔧 Creating virtual environment..."
    python -m venv helios-grid-env
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    echo "✅ Virtual environment created successfully"
else
    echo "📁 Virtual environment already exists"
fi

# Activate virtual environment
echo "🚀 Activating Helios-Grid environment..."
source helios-grid-env/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install core dependencies
echo "🔧 Installing core dependencies..."
pip install wheel setuptools

# Install project dependencies
echo "📋 Installing Helios-Grid dependencies..."
pip install -r requirements.txt

# Install additional ML and development tools
echo "🤖 Installing additional ML tools..."
pip install kagglehub
pip install jupyter
pip install notebook
pip install ipywidgets

# Install development and testing tools
echo "🧪 Installing development tools..."
pip install pytest-cov
pip install black
pip install flake8
pip install mypy
pip install pre-commit

# Install monitoring and visualization tools
echo "📊 Installing monitoring tools..."
pip install streamlit
pip install plotly
pip install seaborn

echo ""
echo "✅ Helios-Grid environment setup completed!"
echo ""
echo "🎯 Environment Details:"
python --version
echo "📍 Virtual Environment: $(pwd)/helios-grid-env"
echo ""
echo "🚀 To activate this environment in the future, run:"
echo "   source helios-grid-env/bin/activate"
echo ""
echo "💡 Quick Start Commands:"
echo "   python run_energy_pipeline.py          # Run complete pipeline"
echo "   python src/api/enhanced_main.py        # Start API server"
echo "   jupyter notebook                       # Launch Jupyter"
echo ""
echo "☀️ Helios-Grid is ready for energy analytics!"