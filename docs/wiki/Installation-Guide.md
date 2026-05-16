# 🚀 Installation Guide

## 📋 **Prerequisites**

### **System Requirements**
- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: 3.9 or higher (3.10 recommended)
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 10GB free space
- **Network**: Internet connection for downloading datasets and dependencies

### **Required Accounts**
- **Azure Account**: [Create free account](https://azure.microsoft.com/free/)
- **Kaggle Account**: [Sign up at Kaggle](https://www.kaggle.com/account/login?phase=startRegisterTab)
- **GitHub Account**: [Create account](https://github.com/join) (for contributing)

---

## 🔧 **Step 1: Environment Setup**

### **1.1 Clone Repository**
```bash
# Clone the Helios-Grid repository
git clone https://github.com/sankeashok/Helios-Grid.git
cd Helios-Grid

# Verify repository structure
ls -la
```

### **1.2 Create Virtual Environment**
```bash
# Create isolated Python environment
python -m venv helios-grid-env

# Activate virtual environment
# Windows:
helios-grid-env\Scripts\activate.bat

# macOS/Linux:
source helios-grid-env/bin/activate

# Verify activation (should show helios-grid-env)
which python
```

### **1.3 Install Dependencies**
```bash
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install core dependencies
pip install -r requirements.txt

# Install Kaggle API for dataset access
pip install kagglehub

# Verify installation
pip list | grep -E "(pandas|scikit-learn|fastapi|kagglehub)"
```

---

## 🔑 **Step 2: Kaggle API Setup**

### **2.1 Get Kaggle API Credentials**

1. **Login to Kaggle**: Visit [kaggle.com](https://www.kaggle.com) and sign in
2. **Go to Account Settings**: Click your profile → Account
3. **Create API Token**: 
   - Scroll to "API" section
   - Click "Create New API Token"
   - Download `kaggle.json` file

### **2.2 Configure Kaggle Credentials**

#### **Option A: Environment Variables (Recommended)**
```bash
# Windows (Command Prompt)
set KAGGLE_USERNAME=your-kaggle-username
set KAGGLE_KEY=your-kaggle-key

# Windows (PowerShell)
$env:KAGGLE_USERNAME="your-kaggle-username"
$env:KAGGLE_KEY="your-kaggle-key"

# macOS/Linux
export KAGGLE_USERNAME="your-kaggle-username"
export KAGGLE_KEY="your-kaggle-key"
```

#### **Option B: Kaggle Config File**
```bash
# Create Kaggle directory
# Windows:
mkdir %USERPROFILE%\.kaggle
copy kaggle.json %USERPROFILE%\.kaggle\

# macOS/Linux:
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

### **2.3 Test Kaggle Access**
```bash
# Test dataset access
python -c "import kagglehub; print('Kaggle API working!')"

# Test specific dataset download (small test)
python -c "
import kagglehub
path = kagglehub.dataset_download('robikscube/hourly-energy-consumption')
print(f'Dataset downloaded to: {path}')
"
```

---

## ☁️ **Step 3: Azure Setup**

### **3.1 Install Azure CLI**

#### **Windows**
```bash
# Download and install Azure CLI
# Visit: https://aka.ms/installazurecliwindows
# Or use winget:
winget install -e --id Microsoft.AzureCLI
```

#### **macOS**
```bash
# Install using Homebrew
brew update && brew install azure-cli
```

#### **Linux (Ubuntu/Debian)**
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### **3.2 Azure Authentication**
```bash
# Login to Azure
az login

# Verify login and list subscriptions
az account list --output table

# Set default subscription (optional)
az account set --subscription "your-subscription-id"
```

### **3.3 Create Azure Resources**
```bash
# Run Azure setup script
python scripts/setup_azure_resources.py \
    --subscription-id "your-subscription-id" \
    --resource-group "helios-grid-rg" \
    --location "eastus" \
    --kaggle-username "$KAGGLE_USERNAME" \
    --kaggle-key "$KAGGLE_KEY"
```

---

## 🐳 **Step 4: Docker Setup (Optional)**

### **4.1 Install Docker**

#### **Windows**
- Download [Docker Desktop for Windows](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe)
- Run installer and follow setup wizard
- Restart computer if required

#### **macOS**
- Download [Docker Desktop for Mac](https://desktop.docker.com/mac/main/amd64/Docker.dmg)
- Drag Docker to Applications folder
- Launch Docker from Applications

#### **Linux (Ubuntu)**
```bash
# Install Docker
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

### **4.2 Verify Docker Installation**
```bash
# Check Docker version
docker --version
docker-compose --version

# Test Docker with hello-world
docker run hello-world
```

---

## 🧪 **Step 5: Verification & Testing**

### **5.1 Environment Verification**
```bash
# Run environment verification script
python scripts/verify_environment.py

# Expected output:
# ✅ Python 3.9+ detected
# ✅ All required packages installed
# ✅ Kaggle API configured
# ✅ Azure CLI authenticated
# ✅ Environment ready for Helios-Grid
```

### **5.2 Quick Pipeline Test**
```bash
# Run a quick test of the data pipeline
python run_energy_pipeline.py --step data --test-mode

# Expected output:
# 📥 Downloading Kaggle dataset...
# 🔄 Processing energy consumption data...
# ✅ Data pipeline test successful!
```

### **5.3 API Test**
```bash
# Start the API server
python src/api/enhanced_main.py &

# Test API health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0-local"}
```

---

## 🎯 **Step 6: First Run**

### **6.1 Complete Pipeline Execution**
```bash
# Run the complete MLOps pipeline
python run_energy_pipeline.py

# This will:
# 1. Download Kaggle dataset (~15MB)
# 2. Process and engineer features
# 3. Train multiple ML models
# 4. Evaluate model performance
# 5. Generate predictions and reports
```

### **6.2 Launch Dashboard**
```bash
# Start the web dashboard
python src/api/enhanced_main.py

# Access dashboard at:
# http://localhost:8000
```

### **6.3 Alternative UI Options**
```bash
# Option 1: Streamlit app
streamlit run src/ui/streamlit_app.py

# Option 2: React frontend (if Node.js installed)
cd react-frontend
npm install
npm start
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Kaggle API Issues**
```bash
# Error: "403 Forbidden"
# Solution: Verify Kaggle credentials
echo $KAGGLE_USERNAME
echo $KAGGLE_KEY

# Error: "Dataset not found"
# Solution: Check dataset URL and permissions
kaggle datasets list -s "hourly-energy-consumption"
```

#### **Azure Authentication Issues**
```bash
# Error: "Please run 'az login'"
# Solution: Re-authenticate
az logout
az login --use-device-code

# Error: "Subscription not found"
# Solution: List and set correct subscription
az account list
az account set --subscription "correct-subscription-id"
```

#### **Python Package Issues**
```bash
# Error: "ModuleNotFoundError"
# Solution: Reinstall in virtual environment
pip install --force-reinstall -r requirements.txt

# Error: "Permission denied"
# Solution: Use virtual environment
deactivate
helios-grid-env\Scripts\activate  # Windows
source helios-grid-env/bin/activate  # macOS/Linux
```

#### **Memory Issues**
```bash
# Error: "MemoryError during model training"
# Solution: Reduce dataset size for testing
python run_energy_pipeline.py --sample-size 10000
```

### **Getting Help**

- **Documentation**: Check [Wiki](https://github.com/sankeashok/Helios-Grid/wiki)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/sankeashok/Helios-Grid/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/sankeashok/Helios-Grid/discussions)

---

## ✅ **Installation Checklist**

- [ ] Python 3.9+ installed and verified
- [ ] Virtual environment created and activated
- [ ] All dependencies installed successfully
- [ ] Kaggle API credentials configured
- [ ] Azure CLI installed and authenticated
- [ ] Docker installed (optional)
- [ ] Environment verification passed
- [ ] Quick pipeline test successful
- [ ] API health check passed
- [ ] Dashboard accessible at localhost:8000

---

**🎉 Congratulations! Helios-Grid is now installed and ready for energy consumption prediction!**

**Next Steps**: 
- Explore the [Dataset Documentation](Dataset-Documentation)
- Learn about [Feature Engineering](Feature-Engineering)
- Try the [Web Dashboard](Web-Dashboard)

---

**Last Updated**: January 2025  
**Installation Guide Version**: 1.0.0