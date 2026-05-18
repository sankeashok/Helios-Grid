# 🚀 Helios-Grid Cloud Deployment Setup

## 🎯 Overview
Deploy your MLOps pipeline to **Azure** (backend) and **Vercel** (frontend) for public access.

---

## 🔧 Azure Backend Deployment

### **Step 1: Install Azure CLI**
```bash
# Windows
winget install Microsoft.AzureCLI

# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### **Step 2: Login to Azure**
```bash
az login
```

### **Step 3: Create Service Principal (for CI/CD)**
```bash
# Create service principal
az ad sp create-for-rbac --name "helios-grid-sp" --role contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID --sdk-auth

# Copy the JSON output - you'll need it for GitHub secrets
```

### **Step 4: Add GitHub Secrets**
Go to: `https://github.com/sankeashok/Helios-Grid/settings/secrets/actions`

Add these secrets:
- **AZURE_CREDENTIALS**: Paste the JSON from Step 3
- **DOCKER_HUB_USERNAME**: Your Docker Hub username
- **DOCKER_HUB_TOKEN**: Your Docker Hub access token

### **Step 5: Deploy Manually (Optional)**
```bash
# Deploy directly from local machine
python deploy_azure_production.py
```

---

## 🌐 Vercel Frontend Deployment

### **Step 1: Install Vercel CLI**
```bash
npm install -g vercel
```

### **Step 2: Login to Vercel**
```bash
vercel login
```

### **Step 3: Deploy Frontend**
```bash
# From project root
cd react-frontend
vercel --prod
```

### **Step 4: Configure Environment Variables**
In Vercel dashboard, add:
- **REACT_APP_API_URL**: Your Azure API URL
- **REACT_APP_ENVIRONMENT**: production

---

## 🔄 Automated Deployment

Once secrets are configured, every push to feature branch will:

1. **Feature Branch** → Staging tests
2. **Auto-merge** → Main branch  
3. **Production Pipeline** → **Real Azure deployment**
4. **Frontend** → **Real Vercel deployment**

---

## 🌍 Public URLs

After deployment, your app will be live at:

- **🔗 Backend API**: `https://helios-grid-energy-api.eastus.azurecontainer.io:8000`
- **📊 API Documentation**: `https://helios-grid-energy-api.eastus.azurecontainer.io:8000/docs`
- **🌐 Frontend Dashboard**: `https://helios-grid-dashboard.vercel.app`

---

## 💰 Cost Estimation

### **Azure Container Instances**
- **CPU**: 2 vCPUs
- **Memory**: 4 GB
- **Estimated Cost**: ~$50-80/month

### **Vercel**
- **Hobby Plan**: Free (with limits)
- **Pro Plan**: $20/month (recommended)

---

## 🛡️ Security Considerations

- **API Keys**: Store in Azure Key Vault
- **HTTPS**: Enabled by default
- **CORS**: Configure for your domain
- **Rate Limiting**: Implement in FastAPI

---

## 📊 Monitoring

- **Azure Monitor**: Container health and metrics
- **Vercel Analytics**: Frontend performance
- **Custom Logging**: Application-level monitoring

---

## 🚀 Next Steps

1. **Configure secrets** in GitHub
2. **Push to feature branch** to trigger deployment
3. **Monitor deployment** in GitHub Actions
4. **Access your live app** at public URLs
5. **Share with the world!** 🌍

Your enterprise MLOps pipeline will be **live and accessible globally**! 🎉