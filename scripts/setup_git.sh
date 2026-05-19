#!/bin/bash

# Helios-Grid Git Setup and Push Script
# This script initializes the git repository and pushes to GitHub

echo "🌟 Setting up Helios-Grid Git Repository"
echo "========================================"

# Navigate to project directory
cd "C:\Users\sanke\Documents\MLops\Azure-MLOps-Pipeline"

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
else
    echo "📁 Git repository already initialized"
fi

# Configure git user (update with your details)
echo "👤 Configuring Git user..."
git config user.name "Ashok Sanke"
git config user.email "sankeashok@gmail.com"

# Add remote origin
echo "🔗 Adding remote origin..."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/sankeashok/Helios-Grid.git

# Create main branch if needed
echo "🌿 Setting up main branch..."
git branch -M main

# Add all files
echo "📦 Adding files to staging..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "🚀 Initial commit: Helios-Grid Enterprise Energy MLOps Pipeline

✨ Features:
- Complete MLOps pipeline for energy consumption prediction
- Azure-native architecture with enterprise security
- Premium glassmorphism UI with WCAG accessibility
- Comprehensive CI/CD with blue-green deployments
- Real-time monitoring and drift detection
- Chaos engineering and edge case handling
- Staff-level engineering implementation

🔧 Tech Stack:
- Azure ML, Blob Storage, Key Vault, DevOps
- FastAPI, MLflow, XGBoost, LightGBM
- Prometheus, Grafana, Docker
- pytest, SAST/DAST security scanning

🎯 Ready for enterprise production deployment!"

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Helios-Grid successfully pushed to GitHub!"
echo "🌐 Repository: https://github.com/sankeashok/Helios-Grid"
echo ""
echo "🎉 Next steps:"
echo "   1. Visit the repository on GitHub"
echo "   2. Set up branch protection rules"
echo "   3. Configure GitHub Actions (optional)"
echo "   4. Add collaborators if needed"
echo ""
echo "☀️ Helios-Grid is ready to power the future of energy analytics!"