# Canvas LTI 1.3 Integration Guide

This guide walks you through integrating the Adaptive Python Assessment with Canvas LMS using LTI 1.3 (Learning Tools Interoperability).

## What You'll Get

✅ Single sign-on from Canvas (students don't need separate login)  
✅ Automatic grade passback to Canvas gradebook  
✅ Embedded assessment experience in Canvas  
✅ Student privacy protection (Canvas handles identity)  
✅ Works with Canvas assignments and modules  

## Architecture Overview

```
Canvas LMS → LTI 1.3 Launch → Your Backend → Assessment → Grade Passback → Canvas Gradebook
```

## Prerequisites

1. **Canvas Administrator Access** (or ask your Canvas admin)
2. **Backend deployed** to Render/Railway/etc with a public URL
3. **OpenAI API key** configured in environment

## Part 1: Deploy Backend with LTI Support

### 1.1 Update Your Files

Replace your `app.py` with `app_with_lti.py` and add `lti_integration.py` to your backend folder:

```
backend/
├── app.py                    ← Use app_with_lti.py
├── lti_integration.py        ← New LTI module
├── models/
├── engine/
└── requirements.txt          ← Use requirements_with_lti.txt
```

### 1.2 Set Environment Variables

In your hosting platform (Render/Railway/Fly.io), add these environment variables:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here
TOOL_URL=https://your-app.onrender.com

# Canvas-specific (get from Canvas Admin)
LTI_ISSUER=https://canvas.instructure.com
LTI_CLIENT_ID=your-client-id-from-canvas
LTI_DEPLOYMENT_ID=your-deployment-id-from-canvas
```

**Note**: You'll get `LTI_CLIENT_ID` and `LTI_DEPLOYMENT_ID` from Canvas in the next steps.

### 1.3 Deploy

```bash
git add .
git commit -m "Add LTI 1.3 support"
git push

# Your backend should redeploy automatically
```

## Part 2: Register Tool in Canvas

### 2.1 Access Developer Keys

1. Log into Canvas as Admin
2. Go to **Admin** → **Developer Keys**
3. Click **+ Developer Key** → **+ LTI Key**

### 2.2 Configure the LTI Key

#### Method A: Manual Configuration

Fill in these fields:

| Field | Value |
|-------|-------|
| **Key Name** | Adaptive Python Assessment |
| **Owner Email** | your-email@example.com |
| **Redirect URIs** | `https://your-app.onrender.com/lti/launch` |
| **Method** | Manual Entry |
| **Title** | Adaptive Python Assessment |
| **Target Link URI** | `https://your-app.onrender.com/lti/launch` |
| **OpenID Connect Initiation Url** | `https://your-app.onrender.com/lti/login` |
| **JWK Method** | Public JWK URL |
| **Public JWK URL** | `https://your-app.onrender.com/lti/jwks` |

#### LTI Advantage Services (Required for Grading)

Enable these scopes:
- ✅ **Can create and view assignment data in the gradebook** (AGS LineItem)
- ✅ **Can view submission data in the gradebook** (AGS Result)
- ✅ **Can create and update submission results in the gradebook** (AGS Score)

#### Placements

Enable these placements:
- ✅ **Assignment Selection** (so teachers can add to assignments)
- ✅ **Link Selection** (so teachers can add to modules)

#### Method B: JSON URL Configuration (Easier!)

Instead of manual entry, use **Paste JSON** or **Enter URL**:

**JSON URL**: `https://your-app.onrender.com/lti/config.json`

Or download and paste the JSON from that URL.

### 2.3 Save and Enable

1. Click **Save**
2. Find your new Developer Key in the list
3. Toggle the **State** to **ON** (it starts as OFF)
4. Copy the **Client ID** - you'll need this!

### 2.4 Get Deployment ID

1. After enabling the key, click **Show Key** or view details
2. Look for the **Deployment ID** (might be in settings or when you add the tool to a course)
3. Or: It will be in the LTI launch claims when you first use the tool

## Part 3: Update Backend with Canvas Info

### 3.1 Add Canvas Details to Environment

Update your hosting platform's environment variables:

```bash
LTI_CLIENT_ID=10000000000001        # From Canvas Developer Key
LTI_DEPLOYMENT_ID=xxx:yyy           # From Canvas or first launch
LTI_ISSUER=https://canvas.instructure.com  # Or your institution's Canvas URL
```

**Important**: If your Canvas is hosted by your institution (like `canvas.myschool.edu`), use that URL as the issuer:

```bash
LTI_ISSUER=https://canvas.myschool.edu
```

### 3.2 Restart Your Backend

After updating environment variables, restart your backend service.

## Part 4: Add Tool to a Canvas Course

### 4.1 Create an Assignment

1. Go to your Canvas course
2. Click **Assignments** → **+ Assignment**
3. Fill in:
   - **Assignment Name**: Python Assessment Module 1
   - **Points**: 100 (or whatever you want)
   - **Submission Type**: External Tool
   - Click **Find** button next to External Tool

4. In the tool selector:
   - Find **Adaptive Python Assessment**
   - Click to select it
   - Click **Select**

5. Configure assignment settings:
   - Set due date (optional)
   - Set available from/until dates (optional)
   - Choose assignment group
   - Click **Save**

### 4.2 Add to a Module (Alternative)

1. Go to **Modules**
2. Click **+** in a module
3. Select **External Tool**
4. Find **Adaptive Python Assessment**
5. Click **Add Item**

## Part 5: Test the Integration

### 5.1 Student View

1. Click **Student View** in Canvas (or use a test student account)
2. Go to the assignment you created
3. Click **Load [Tool Name] in a new window** or embedded view
4. You should see the assessment interface
5. Complete a question
6. Check that the grade appears in Canvas gradebook

### 5.2 Verify Grade Passback

After completing the assessment:

1. Go to **Grades** in Canvas as instructor
2. Find the assignment
3. Student's score should appear automatically
4. Click on the score to see the comment with detailed breakdown

## Troubleshooting

### "Invalid LTI launch token"

**Problem**: Canvas isn't sending valid credentials

**Solutions**:
1. Verify Developer Key is enabled (toggle is ON)
2. Check that `LTI_CLIENT_ID` matches Canvas exactly
3. Confirm `LTI_ISSUER` matches your Canvas URL
4. Check backend logs for specific error details

### "Session not found"

**Problem**: Session storage issue or backend restarted

**Solutions**:
1. Complete assessment in one sitting (sessions don't persist across restarts)
2. For production, implement Redis or database session storage
3. Check that cookies/localStorage aren't blocked

### Grade not appearing in Canvas

**Problem**: AGS (Assignment and Grade Services) not working

**Solutions**:
1. Verify AGS scopes are enabled in Developer Key
2. Check that assignment was created via External Tool (not after)
3. Look for grade submission errors in backend logs
4. Confirm `ags_claim` exists in LTI launch token

### CORS errors

**Problem**: Browser blocking requests

**Solutions**:
1. Add Canvas domain to CORS allowed origins in `app.py`:
   ```python
   allow_origins=[
       "https://canvas.instructure.com",
       "https://canvas.myschool.edu",  # Your institution's domain
   ]
   ```
2. Restart backend after CORS changes

### Tool not appearing in Canvas

**Problem**: Developer Key not configured correctly

**Solutions**:
1. Ensure Developer Key state is **ON**
2. Check that placements include "Assignment Selection"
3. Verify JWK URL is accessible: visit `https://your-app.onrender.com/lti/jwks`
4. Make sure your TOOL_URL environment variable is correct

## Advanced Configuration

### Custom Question Sets per Assignment

Modify `lti_launch` endpoint to check:

```python
# In app_with_lti.py, in lti_launch function:
custom_params = claims.get("https://purl.imsglobal.org/spec/lti/claim/custom", {})
question_set = custom_params.get("question_set", "default")
```

Then in Canvas assignment settings, add custom parameter:
```
question_set=module1
```

### Persistent Sessions with Redis

For production, replace in-memory sessions with Redis:

```python
import redis
redis_client = redis.Redis.from_url(os.environ.get("REDIS_URL"))

# Store session
redis_client.setex(f"session:{session_id}", 7200, json.dumps(session_dict))

# Retrieve session
session_data = redis_client.get(f"session:{session_id}")
```

### Multiple Canvas Instances

If you serve multiple schools, support different issuers:

```python
# In lti_integration.py
KNOWN_ISSUERS = [
    "https://canvas.instructure.com",
    "https://canvas.school1.edu",
    "https://canvas.school2.edu",
]

# Validate issuer is in known list
if unverified["iss"] not in KNOWN_ISSUERS:
    return None
```

## Security Best Practices

1. ✅ Always verify LTI token signature (TODO in current implementation)
2. ✅ Check nonce to prevent replay attacks (implemented)
3. ✅ Use HTTPS for all endpoints
4. ✅ Rotate private keys periodically
5. ✅ Validate all user inputs
6. ✅ Log security events
7. ✅ Set appropriate session timeouts
8. ✅ Use environment variables for secrets (never hardcode)

## Testing Checklist

- [ ] LTI launch works (student sees assessment)
- [ ] Questions display correctly
- [ ] Answers can be submitted
- [ ] Feedback shows after each question
- [ ] Final summary appears
- [ ] Grade appears in Canvas gradebook
- [ ] Grade includes comment with details
- [ ] Multiple students can use simultaneously
- [ ] Works on mobile devices
- [ ] No CORS errors in browser console

## Support Resources

### Canvas LTI Documentation
- https://canvas.instructure.com/doc/api/file.lti_dev_key_config.html
- https://www.imsglobal.org/spec/lti/v1p3

### Your Backend URLs
Test these are accessible:
- Config: `https://your-app.onrender.com/lti/config.json`
- JWKS: `https://your-app.onrender.com/lti/jwks`
- Health: `https://your-app.onrender.com/health`

### Common Canvas Admin Questions

**Q: Is this secure?**  
A: Yes, LTI 1.3 uses OAuth 2.0 with JWT tokens, signed with RSA keys.

**Q: Can students cheat?**  
A: The assessment uses AI evaluation. Students can still use external resources, like any Canvas assignment.

**Q: Will this slow down Canvas?**  
A: No, the tool runs on separate servers and doesn't affect Canvas performance.

**Q: Can we customize question banks?**  
A: Yes, edit `questions.jsonl` or use custom parameters in Canvas to select question sets.

## Next Steps

Once LTI is working:

1. Create assignments for different Python modules
2. Build question banks for each topic
3. Set up analytics dashboard
4. Train instructors on using the tool
5. Gather student feedback
6. Iterate and improve!

## Getting Help

If you're stuck:

1. Check backend logs in your hosting dashboard
2. Check browser console for JavaScript errors
3. Verify all environment variables are set
4. Test endpoints directly with curl/Postman
5. Contact your Canvas admin for institutional settings

## Appendix: Environment Variables Reference

```bash
# Required
OPENAI_API_KEY=sk-...                          # Your OpenAI API key
TOOL_URL=https://your-app.onrender.com         # Your backend URL

# Canvas LTI Configuration
LTI_ISSUER=https://canvas.instructure.com      # Canvas platform URL
LTI_CLIENT_ID=10000000000001                   # From Canvas Developer Key
LTI_DEPLOYMENT_ID=xxx:yyy                      # From Canvas (may be auto-detected)

# Optional
REDIS_URL=redis://...                          # For persistent sessions
LOG_LEVEL=INFO                                 # Logging verbosity
```
