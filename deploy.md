# Flight Tracker Deployment Guide

## Option 1: Deploy to Render (Recommended)

### Backend Deployment on Render

1. **Create a Render account** at [render.com](https://render.com)

2. **Connect your GitHub repository**:
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your flight-tracker repository

3. **Configure the service**:
   - Name: `flight-tracker-backend`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd backend && python app.py`
   - Plan: Free

4. **Set environment variables**:
   - `FLASK_ENV` = `production`
   - `PORT` = `8080`

5. **Deploy**: Click "Create Web Service"

Your backend will be available at: `https://flight-tracker-backend-xxxxx.onrender.com`

### Frontend Deployment on Netlify/GitHub Pages

#### Option A: Netlify (Recommended)

1. **Create a Netlify account** at [netlify.com](https://netlify.com)

2. **Deploy from GitHub**:
   - Click "New site from Git"
   - Connect GitHub and select your repository
   - Build settings:
     - Publish directory: `frontend`
     - No build command needed

3. **Update API URL**:
   - Edit `frontend/script.js`
   - Change `apiBaseUrl` to your Render backend URL
   
#### Option B: GitHub Pages

1. **Enable GitHub Pages**:
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: main / (root)

2. **Update API URL**:
   - Edit `frontend/script.js`
   - Change `apiBaseUrl` to your backend URL

## Option 2: Deploy to Railway

1. **Create a Railway account** at [railway.app](https://railway.app)

2. **Deploy from GitHub**:
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect it's a Python app

3. **Configure**:
   - Root directory: `/`
   - Start command: `cd backend && python app.py`

## Option 3: Deploy to Heroku

1. **Create a Heroku account** at [heroku.com](https://heroku.com)

2. **Install Heroku CLI** and login:
   ```bash
   heroku login
   ```

3. **Create and deploy**:
   ```bash
   heroku create your-flight-tracker
   git push heroku main
   ```

## Configuration Updates for Production

### Update CORS Settings
In `backend/app.py`, update CORS for production:

```python
CORS(app, origins=["https://your-frontend-domain.com"])
```

### Update Frontend API URL
In `frontend/script.js`, update:

```javascript
this.apiBaseUrl = 'https://your-backend-domain.com/api';
```

### Environment Variables
Set these environment variables in your hosting service:

- `FLASK_ENV=production`
- `PORT=8080` (or as required by hosting service)
- `DATABASE_PATH=data/flights.db`

## GitHub Repository Setup

1. **Initialize git** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Create GitHub repository**:
   - Go to github.com → New repository
   - Name: `flight-tracker`
   - Make it public
   - Don't initialize with README (you already have files)

3. **Push to GitHub**:
   ```bash
   git remote add origin https://github.com/yourusername/flight-tracker.git
   git branch -M main
   git push -u origin main
   ```

## Final Steps

1. Deploy backend to Render/Railway/Heroku
2. Update frontend API URL to point to deployed backend
3. Deploy frontend to Netlify/GitHub Pages
4. Test the live application
5. Share your public URL!

## Estimated Costs

- **Free Option**: Render (backend) + Netlify (frontend) = $0/month
- **Paid Option**: Railway ($5/month) or Heroku ($7/month)

All free tiers have limitations but are perfect for a personal project like this. 