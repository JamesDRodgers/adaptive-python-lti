# Deployment Guide: GitHub Pages + Backend Hosting

## Architecture Overview

```
Frontend (GitHub Pages)          Backend (Render/Railway/etc)
├── index.html                   ├── app.py
├── main.js              →→→     ├── models/
└── [static only]                ├── engine/
                                 └── questions.jsonl
```

## Step 1: Deploy Backend to Render (Free)

### 1.1 Prepare Backend for Deployment

Create a `render.yaml` in your backend folder:

```yaml
services:
  - type: web
    name: adaptive-python-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
```

### 1.2 Deploy to Render

1. Go to https://render.com and sign up
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variable:
   - **Key**: `OPENAI_API_KEY`
   - **Value**: Your OpenAI API key
6. Click "Create Web Service"
7. Wait for deployment (you'll get a URL like `https://your-app.onrender.com`)

## Step 2: Update Frontend for Production

### 2.1 Update main.js with your backend URL

```javascript
// Replace this line in main.js:
const API = "http://localhost:8000";

// With your Render backend URL:
const API = "https://your-app.onrender.com";
```

### 2.2 Update CORS in app.py

```python
# Update this in app.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourusername.github.io",  # Your GitHub Pages URL
        "http://localhost:8080"  # Keep for local testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Step 3: Deploy Frontend to GitHub Pages

### 3.1 Create a GitHub repository

```bash
# In your project root
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/adaptive-python-assessment.git
git push -u origin main
```

### 3.2 Enable GitHub Pages

1. Go to your repository on GitHub
2. Click "Settings" → "Pages"
3. Under "Source", select "main" branch
4. Select folder: `/frontend` (if you organized it this way)
   - OR put index.html and main.js at root level
5. Click "Save"
6. Your site will be at: `https://yourusername.github.io/adaptive-python-assessment/`

### 3.3 Recommended: Put frontend files at root

For easier GitHub Pages setup, reorganize like this:

```
adaptive-python-assessment/
├── index.html           ← Move to root
├── main.js              ← Move to root
├── backend/             ← Keep backend separate
│   ├── app.py
│   ├── requirements.txt
│   └── ...
└── README.md
```

Then GitHub Pages can serve from root.

## Alternative Backend Hosting Options

### Railway (Easy, Free Trial)
1. Go to https://railway.app
2. "New Project" → "Deploy from GitHub"
3. Select your repo
4. Add `OPENAI_API_KEY` in Variables
5. Railway auto-detects Python and deploys

### Fly.io (Free Tier)
1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. From backend folder: `fly launch`
4. Set secret: `fly secrets set OPENAI_API_KEY=sk-...`
5. Deploy: `fly deploy`

### PythonAnywhere (Free Tier)
1. Sign up at https://www.pythonanywhere.com
2. Upload files via Files tab
3. Set up Web app with Flask/FastAPI
4. Configure environment variables in Web tab
5. Reload web app

## Testing Your Deployment

1. **Test backend directly**:
   ```bash
   curl https://your-backend-url.onrender.com/health
   ```

2. **Test CORS**:
   Open browser console on your GitHub Pages site and check for CORS errors

3. **Test full flow**:
   - Visit your GitHub Pages URL
   - Start an assessment
   - Submit an answer
   - Check browser Network tab for API calls

## Troubleshooting

### CORS Errors
- Make sure your GitHub Pages URL is in `allow_origins` in app.py
- Redeploy backend after changing CORS settings

### "Session not found" errors
- Render free tier sleeps after inactivity (takes ~30s to wake)
- Consider upgrading or using persistent storage

### API Key Issues
- Verify environment variable is set correctly in hosting dashboard
- Check backend logs for authentication errors

### Frontend not updating
- GitHub Pages can cache aggressively
- Try hard refresh (Ctrl+Shift+R)
- Clear browser cache
- Check if you pushed latest changes

## Cost Breakdown

**Free Tier Options:**
- GitHub Pages: Free forever
- Render: Free tier available (sleeps after 15 min inactivity)
- Railway: $5 free credit monthly
- Fly.io: Free tier with 3 VMs
- PythonAnywhere: Free tier with limitations

**OpenAI Costs:**
- GPT-4o-mini: ~$0.15 per 1M input tokens
- Very cheap for this use case (pennies per assessment)

## Production Checklist

- [ ] Backend deployed and accessible
- [ ] OPENAI_API_KEY environment variable set
- [ ] CORS configured for your domain
- [ ] Frontend updated with backend URL
- [ ] GitHub Pages enabled and working
- [ ] Test complete user flow
- [ ] Check browser console for errors
- [ ] Test on mobile devices
- [ ] Set up error monitoring (optional)
- [ ] Add analytics (optional)

## File Structure for Deployment

```
your-repo/
├── index.html              ← GitHub Pages serves this
├── main.js                 ← Update API URL here
├── backend/                ← Deploy this to Render
│   ├── app.py
│   ├── requirements.txt
│   ├── models/
│   └── engine/
└── README.md
```

## Next Steps

1. Deploy backend first (get URL)
2. Update main.js with backend URL
3. Update app.py CORS settings
4. Push to GitHub
5. Enable GitHub Pages
6. Test everything!

Need help? Check the logs in your hosting dashboard for error messages.
