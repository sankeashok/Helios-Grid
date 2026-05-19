# 🚀 Vercel Deployment Guide - Helios-Grid React Frontend

## 🎯 Quick Setup

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Deploy from React Frontend Directory
```bash
cd react-frontend
vercel --prod
```

## 🔧 GitHub Actions Setup (Automatic Deployment)

### Required Secrets in GitHub Repository Settings:

1. **VERCEL_TOKEN**
   - Go to https://vercel.com/account/tokens
   - Create new token
   - Add to GitHub Secrets

2. **VERCEL_ORG_ID** 
   - Run `vercel` in project directory
   - Copy Organization ID from `.vercel/project.json`

3. **VERCEL_PROJECT_ID**
   - Run `vercel` in project directory  
   - Copy Project ID from `.vercel/project.json`

## 🌐 Live URLs

- **Frontend**: https://helios-grid-react.vercel.app (will be your actual domain)
- **API Backend**: https://sankeashook-helios-gridenergy-prediction.hf.space
- **Full Platform**: Complete MLOps pipeline with React UI + FastAPI backend

## ✅ Features Deployed

- 🎨 Premium React UI with Tailwind CSS
- 📊 Interactive energy prediction dashboard
- 📈 Real-time charts and visualizations  
- 🔮 ML model predictions via Hugging Face API
- 📱 Responsive mobile-first design
- ⚡ Fast Vercel CDN delivery

## 🔄 Automatic Deployment

The GitHub Actions workflow will automatically deploy to Vercel when:
- Changes are pushed to `main` branch
- Files in `react-frontend/` directory are modified
- Manual workflow dispatch is triggered

## 🎉 Result

Complete full-stack MLOps platform:
- **Frontend**: React app on Vercel
- **Backend**: FastAPI on Hugging Face Spaces  
- **CI/CD**: Automated deployment pipeline
- **Monitoring**: Production-ready with health checks