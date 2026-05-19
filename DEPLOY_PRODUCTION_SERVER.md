# 🚀 Deploy Production Server (localhost:3002) to Cloud

## 🎯 Goal: Make `http://localhost:3002/` Live on Internet

Your production server with ML model needs to be deployed to a public URL.

## ✅ Option 1: Railway (Recommended - Free Tier)

### 1. **Sign up for Railway**
   - Go to: https://railway.app
   - Sign up with GitHub account

### 2. **Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `sankeashok/Helios-Grid`
   - Railway will auto-detect Python and deploy

### 3. **Configuration**
   - Railway will use `railway.toml` and `Procfile` automatically
   - Uses `cloud_production_server.py` (optimized for cloud)
   - Installs from `requirements-production.txt`

### 4. **Get Your Live URL**
   - Railway provides: `https://your-app-name.railway.app`
   - Your production server will be live at this URL

## ✅ Option 2: Render (Alternative - Free Tier)

### 1. **Sign up for Render**
   - Go to: https://render.com
   - Sign up with GitHub

### 2. **Create Web Service**
   - New → Web Service
   - Connect GitHub repo: `sankeashok/Helios-Grid`
   - Settings:
     - **Build Command**: `pip install -r requirements-production.txt`
     - **Start Command**: `python cloud_production_server.py`
     - **Environment**: Python 3

### 3. **Get Live URL**
   - Render provides: `https://your-app-name.onrender.com`

## ✅ Option 3: Heroku (Classic Option)

### 1. **Install Heroku CLI**
   ```bash
   # Download from: https://devcenter.heroku.com/articles/heroku-cli
   ```

### 2. **Deploy Commands**
   ```bash
   cd "C:\Users\sanke\Documents\MLops\Azure-MLOps-Pipeline"
   heroku login
   heroku create helios-grid-production
   git push heroku main
   ```

## 🎯 Expected Result

Once deployed, you'll have:

- **Live Production API**: `https://your-app.railway.app` (or similar)
- **Same functionality as localhost:3002**:
  - ✅ `/` - Beautiful dashboard
  - ✅ `/health` - Health check
  - ✅ `/predict` - Energy predictions
  - ✅ `/docs` - API documentation
  - ✅ `/model/info` - Model details

## 🔄 Update Frontend

After deployment, update your frontend to use the live URL:

1. **Update GitHub Pages** (`docs/index.html`):
   ```javascript
   // Change this line:
   const response = await axios.post('https://sankeashook-helios-gridenergy-prediction.hf.space/predict', {
   
   // To your new Railway URL:
   const response = await axios.post('https://your-app.railway.app/predict', {
   ```

2. **Commit and push** to update GitHub Pages

## 🎉 Final Result

- **Frontend**: https://sankeashok.github.io/Helios-Grid/ ✅
- **Backend**: https://your-app.railway.app ✅
- **Full Stack**: Complete MLOps platform live!

## 🚀 Recommended: Railway Deployment

Railway is the easiest and most reliable for FastAPI apps. Just connect your GitHub repo and it deploys automatically!

**Go to https://railway.app and deploy now!** 🚀