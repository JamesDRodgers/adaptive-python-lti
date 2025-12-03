# 🚀 Push to GitHub Instructions

Your repository is ready! Here's how to push it to GitHub.

## Step 1: Create Repository on GitHub

1. Go to https://github.com
2. Click the **"+"** icon (top right) → **"New repository"**
3. Fill in:
   - **Repository name**: `adaptive-python-lti`
   - **Description**: `AI-powered adaptive Python assessment with Canvas LTI 1.3 integration`
   - **Public** or **Private** (your choice)
   - ⚠️ **DO NOT** initialize with README (we already have one)
   - ⚠️ **DO NOT** add .gitignore or license (we have these)
4. Click **"Create repository"**

## Step 2: Connect Local Repo to GitHub

After creating the repo, GitHub will show you commands. Use these:

```bash
# Add the remote
git remote add origin https://github.com/JamesDRodgers/adaptive-python-lti.git

# Verify remote was added
git remote -v

# Push to GitHub
git push -u origin main
```

### If you get authentication errors:

**Option A: Use Personal Access Token**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Use token as password when prompted

**Option B: Use SSH**
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copy public key and add to GitHub
cat ~/.ssh/id_ed25519.pub
# Go to GitHub → Settings → SSH and GPG keys → New SSH key

# Change remote to SSH
git remote set-url origin git@github.com:JamesDRodgers/adaptive-python-lti.git

# Push
git push -u origin main
```

## Step 3: Verify on GitHub

After pushing:
1. Refresh your GitHub repository page
2. You should see all files
3. README.md will display on the main page
4. Check that .env is NOT there (it's in .gitignore)

## Step 4: Deploy to Render

Now that it's on GitHub:

1. Go to https://render.com
2. Sign in with GitHub
3. Click **"New +"** → **"Web Service"**
4. Select your `adaptive-python-lti` repository
5. Configure:
   - **Name**: `adaptive-python-lti`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`

6. Add Environment Variables:
   ```
   OPENAI_API_KEY=sk-your-key-here
   TOOL_URL=https://adaptive-python-lti.onrender.com
   LTI_ISSUER=https://canvas.instructure.com
   ```

7. Click **"Create Web Service"**

8. Wait for deployment (5-10 minutes first time)

9. Your backend will be at: `https://adaptive-python-lti.onrender.com`

## Step 5: Test Your Deployment

```bash
# Test health endpoint
curl https://adaptive-python-lti.onrender.com/health

# Test LTI config
curl https://adaptive-python-lti.onrender.com/lti/config.json

# Should return JSON responses
```

## Step 6: Canvas Integration

Now follow the **CANVAS_LTI_SETUP.md** guide:

1. Go to Canvas → Admin → Developer Keys
2. Create new LTI Key
3. Use your Render URL for all endpoints
4. Copy Client ID and add to Render environment variables
5. Create assignment in Canvas

## Next Steps

### Future Updates

When you make changes:

```bash
# Make your changes to files
# Then commit and push:

git add .
git commit -m "Description of your changes"
git push origin main

# Render will automatically redeploy
```

### Add Collaborators

On GitHub:
1. Go to repository → Settings → Collaborators
2. Add team members

### Enable Issues

1. Repository → Settings → Features
2. Check "Issues"
3. Students/instructors can report bugs

### Set Up Continuous Integration (Optional)

Add GitHub Actions for automated testing:
1. Create `.github/workflows/test.yml`
2. Add pytest for backend tests
3. Auto-test on every push

## Troubleshooting

### "Permission denied (publickey)"
- Use personal access token instead of SSH
- Or follow SSH key setup instructions above

### "Repository not found"
- Check repository name matches exactly
- Verify you have push access

### Render deployment fails
- Check build logs in Render dashboard
- Verify requirements.txt is valid
- Ensure all imports are correct

### LTI not working
- Check environment variables in Render
- Verify TOOL_URL matches your Render URL
- Follow CANVAS_LTI_SETUP.md carefully

## Success Checklist

- [ ] Repository created on GitHub
- [ ] Local repo connected to GitHub
- [ ] Pushed successfully (all files visible on GitHub)
- [ ] Deployed to Render
- [ ] Health endpoint returns 200 OK
- [ ] Environment variables set in Render
- [ ] Canvas LTI key configured
- [ ] Test assignment created in Canvas
- [ ] Student can launch and complete assessment
- [ ] Grade appears in Canvas gradebook

## 🎉 You're Done!

Your adaptive Python assessment is now:
- ✅ Version controlled on GitHub
- ✅ Deployed and accessible
- ✅ Ready for Canvas integration
- ✅ Set up for easy updates

Congratulations! 🎊
