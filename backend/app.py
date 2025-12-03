from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from engine.adaptive_engine import next_question, score_response
from models.session import SessionState
from lti_integration import (
    LTIConfig, 
    LTIValidator, 
    LTIGradeSubmitter,
    store_lti_session,
    get_lti_session
)
from typing import Dict, Optional
import uuid
import secrets

app = FastAPI(title="Adaptive Python Assessment API with LTI")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourusername.github.io",
        "http://localhost:8080",
        "https://*.instructure.com",  # Canvas domains
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session storage
SESSIONS: Dict[str, SessionState] = {}

# LTI Configuration
lti_config = LTIConfig()
lti_validator = LTIValidator(lti_config)
lti_grade_submitter = LTIGradeSubmitter(lti_config)

# Store nonces to prevent replay attacks
used_nonces = set()


class AnswerRequest(BaseModel):
    """Request model for answer submission."""
    student_answer: str = Field(..., min_length=1, max_length=5000)
    explanation: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., description="Session ID from /start endpoint")


# ============================================================================
# LTI ENDPOINTS
# ============================================================================

@app.get("/lti/config.json")
async def lti_config_json():
    """
    LTI 1.3 Configuration JSON for Canvas
    Canvas Admin → Developer Keys → + Developer Key → + LTI Key
    """
    return {
        "title": "Adaptive Python Assessment",
        "description": "AI-powered adaptive assessment for Python programming",
        "oidc_initiation_url": f"{lti_config.tool_url}/lti/login",
        "target_link_uri": f"{lti_config.tool_url}/lti/launch",
        "scopes": [
            "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
            "https://purl.imsglobal.org/spec/lti-ags/scope/score",
            "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly",
        ],
        "extensions": [
            {
                "platform": "canvas.instructure.com",
                "settings": {
                    "platform": "canvas.instructure.com",
                    "placements": [
                        {
                            "placement": "assignment_selection",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": f"{lti_config.tool_url}/lti/launch",
                            "text": "Adaptive Python Assessment",
                            "enabled": True
                        },
                        {
                            "placement": "link_selection",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": f"{lti_config.tool_url}/lti/launch",
                            "text": "Adaptive Python Assessment",
                            "enabled": True
                        }
                    ]
                },
                "privacy_level": "public"
            }
        ],
        "public_jwk_url": f"{lti_config.tool_url}/lti/jwks",
        "custom_fields": {}
    }


@app.get("/lti/jwks")
async def lti_jwks():
    """
    JSON Web Key Set endpoint
    Canvas uses this to verify our signatures
    """
    return lti_config.get_public_jwks()


@app.get("/lti/login")
@app.post("/lti/login")
async def lti_login(request: Request):
    """
    OIDC Login Initiation
    First step of LTI 1.3 launch flow
    """
    params = dict(request.query_params)
    
    # Generate state and nonce for security
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    
    # Store nonce to validate later
    used_nonces.add(nonce)
    
    # Build authorization redirect URL
    auth_params = {
        "response_type": "id_token",
        "response_mode": "form_post",
        "client_id": lti_config.client_id,
        "redirect_uri": lti_config.launch_url,
        "scope": "openid",
        "state": state,
        "nonce": nonce,
        "prompt": "none",
        "login_hint": params.get("login_hint", ""),
        "lti_message_hint": params.get("lti_message_hint", "")
    }
    
    # Construct redirect URL
    from urllib.parse import urlencode
    auth_url = f"{lti_config.auth_login_url}?{urlencode(auth_params)}"
    
    return RedirectResponse(url=auth_url)


@app.post("/lti/launch")
async def lti_launch(request: Request, id_token: str = Form(...), state: str = Form(...)):
    """
    LTI Launch endpoint
    Canvas sends the student here with an id_token after login
    """
    try:
        # Validate the LTI launch token
        claims = lti_validator.validate_launch(id_token)
        
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid LTI launch token")
        
        # Verify nonce hasn't been used before
        nonce = claims.get("nonce")
        if nonce not in used_nonces:
            raise HTTPException(status_code=401, detail="Invalid or reused nonce")
        
        # Remove nonce so it can't be reused
        used_nonces.discard(nonce)
        
        # Extract user information
        user_id = claims.get("sub")
        user_name = claims.get("name", "Student")
        user_email = claims.get("email", "")
        
        # Check if this is a gradable launch
        is_gradable = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint" in claims
        
        # Create new assessment session
        session_id = str(uuid.uuid4())
        session = SessionState()
        SESSIONS[session_id] = session
        
        # Store LTI claims for grade passback later
        if is_gradable:
            store_lti_session(session_id, claims)
        
        # Get first question
        question = next_question(session)
        
        if question is None:
            raise HTTPException(status_code=500, detail="Failed to load initial question")
        
        # Return HTML page with embedded assessment
        return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adaptive Python Assessment</title>
    <style>
        {get_embedded_styles()}
    </style>
</head>
<body>
    <div class="lti-container">
        <div class="header">
            <h1>🐍 Adaptive Python Assessment</h1>
            <p class="user-info">Welcome, {user_name}!</p>
            {f'<p class="gradable-notice">✓ This assessment will be graded</p>' if is_gradable else ''}
        </div>
        <div id="app">
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading assessment...</p>
            </div>
        </div>
    </div>
    <script>
        const SESSION_ID = "{session_id}";
        const IS_GRADABLE = {str(is_gradable).lower()};
        const API = "{lti_config.tool_url}";
        {get_embedded_javascript()}
    </script>
</body>
</html>
        """)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in LTI launch: {e}")
        raise HTTPException(status_code=500, detail=f"Launch error: {str(e)}")


# ============================================================================
# ASSESSMENT ENDPOINTS (Modified for LTI)
# ============================================================================

@app.get("/start")
def start():
    """Start a new assessment session (non-LTI)"""
    try:
        session_id = str(uuid.uuid4())
        session = SessionState()
        SESSIONS[session_id] = session
        
        question = next_question(session)
        
        if question is None:
            raise HTTPException(status_code=500, detail="Failed to load initial question")
        
        return {
            "session_id": session_id,
            "question": question
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting assessment: {str(e)}")


@app.post("/answer")
async def answer(request: AnswerRequest):
    """Submit an answer and get evaluation with next question"""
    try:
        # Retrieve session
        session = SESSIONS.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found. Please start a new assessment.")
        
        if session.finished:
            raise HTTPException(status_code=400, detail="Assessment already completed")
        
        if not session.current_question:
            raise HTTPException(status_code=400, detail="No active question")
        
        # Score the response
        response_data = {
            "student_answer": request.student_answer,
            "explanation": request.explanation
        }
        evaluation = score_response(session, response_data)
        
        # Check if assessment is finished
        if session.finished:
            summary = session.summary()
            
            # Submit grade to Canvas if this is an LTI launch
            lti_claims = get_lti_session(request.session_id)
            if lti_claims:
                grade_submitted = lti_grade_submitter.submit_grade(
                    id_token_claims=lti_claims,
                    score=summary["final_score"],
                    max_score=1.0,
                    comment=f"Assessment completed. Accuracy: {summary['average_accuracy']:.1%}, Explanation: {summary['average_explanation']:.1%}"
                )
                summary["grade_submitted"] = grade_submitted
            
            # Clean up session
            del SESSIONS[request.session_id]
            
            return {
                "evaluation": evaluation,
                "finished": True,
                "summary": summary
            }
        
        # Get next question
        next_q = next_question(session)
        return {
            "evaluation": evaluation,
            "finished": False,
            "next_question": next_q
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")


@app.get("/session/{session_id}")
def get_session_status(session_id: str):
    """Get current session status"""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if this is an LTI session
    is_lti = get_lti_session(session_id) is not None
    
    return {
        "question_number": session.question_number,
        "max_questions": session.max_questions,
        "bloom_level": session.bloom_level,
        "difficulty": session.difficulty,
        "finished": session.finished,
        "is_lti_session": is_lti
    }


@app.delete("/session/{session_id}")
def end_session(session_id: str):
    """End a session early"""
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return {"message": "Session ended"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(SESSIONS),
        "lti_configured": bool(lti_config.client_id)
    }


# ============================================================================
# EMBEDDED STYLES AND JAVASCRIPT
# ============================================================================

def get_embedded_styles():
    """CSS styles for embedded LTI view"""
    return """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .lti-container { max-width: 900px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px 12px 0 0;
            text-align: center;
        }
        .header h1 { margin-bottom: 10px; }
        .user-info { font-size: 1.1em; opacity: 0.9; }
        .gradable-notice {
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
            font-size: 0.9em;
        }
        #app {
            background: white;
            padding: 40px;
            border-radius: 0 0 12px 12px;
            min-height: 400px;
        }
        .question-container h2 { color: #333; margin-bottom: 30px; font-size: 1.5em; }
        .form-group { margin-bottom: 25px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: 600; }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: inherit;
            font-size: 1em;
            resize: vertical;
        }
        textarea:focus { outline: none; border-color: #667eea; }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            font-size: 1.1em;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
        }
        button:hover { opacity: 0.9; }
        .loading { text-align: center; padding: 60px 20px; }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .score-display {
            display: flex;
            justify-content: space-around;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 25px 0;
        }
        .score-item { display: flex; flex-direction: column; gap: 8px; text-align: center; }
        .score-label { color: #666; font-size: 0.9em; }
        .score-value { font-size: 1.8em; font-weight: bold; }
        .score-display.good .score-value { color: #10b981; }
        .score-display.okay .score-value { color: #f59e0b; }
        .score-display.poor .score-value { color: #ef4444; }
    """


def get_embedded_javascript():
    """JavaScript for embedded LTI view"""
    return """
        let currentSessionId = SESSION_ID;
        
        async function showQuestion(question) {
            const app = document.getElementById('app');
            app.innerHTML = `
                <div class="question-container">
                    <h2>${escapeHtml(question.question)}</h2>
                    <div class="form-group">
                        <label for="answer">Your Answer:</label>
                        <textarea id="answer" placeholder="Enter your answer..." rows="4"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="explanation">Explain Your Reasoning:</label>
                        <textarea id="explanation" placeholder="Explain why..." rows="4"></textarea>
                    </div>
                    <button onclick="submitAnswer()">Submit Answer</button>
                </div>
            `;
            document.getElementById('answer').focus();
        }
        
        async function submitAnswer() {
            const answer = document.getElementById('answer').value.trim();
            const explanation = document.getElementById('explanation').value.trim();
            
            if (!answer || !explanation) {
                alert('Please provide both an answer and explanation');
                return;
            }
            
            try {
                document.getElementById('app').innerHTML = '<div class="loading"><div class="spinner"></div><p>Evaluating...</p></div>';
                
                const response = await fetch(API + '/answer', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        student_answer: answer,
                        explanation: explanation,
                        session_id: currentSessionId
                    })
                });
                
                const data = await response.json();
                
                showFeedback(data.evaluation);
                
                setTimeout(() => {
                    if (data.finished) {
                        showSummary(data.summary);
                    } else {
                        showQuestion(data.next_question);
                    }
                }, 2000);
                
            } catch (error) {
                document.getElementById('app').innerHTML = `<div class="error"><p>Error: ${error.message}</p></div>`;
            }
        }
        
        function showFeedback(evaluation) {
            const scoreClass = evaluation.final_score >= 0.7 ? 'good' : evaluation.final_score >= 0.5 ? 'okay' : 'poor';
            document.getElementById('app').innerHTML = `
                <div class="feedback-container">
                    <h2>Response Evaluated</h2>
                    <div class="score-display ${scoreClass}">
                        <div class="score-item">
                            <span class="score-label">Accuracy:</span>
                            <span class="score-value">${(evaluation.accuracy * 100).toFixed(0)}%</span>
                        </div>
                        <div class="score-item">
                            <span class="score-label">Explanation:</span>
                            <span class="score-value">${(evaluation.explanation_score * 100).toFixed(0)}%</span>
                        </div>
                        <div class="score-item">
                            <span class="score-label">Overall:</span>
                            <span class="score-value">${(evaluation.final_score * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                    <p style="text-align:center;color:#666;">Loading next question...</p>
                </div>
            `;
        }
        
        function showSummary(summary) {
            const finalScorePercent = (summary.final_score * 100).toFixed(1);
            const scoreClass = summary.final_score >= 0.7 ? 'good' : summary.final_score >= 0.5 ? 'okay' : 'poor';
            const gradeMsg = IS_GRADABLE && summary.grade_submitted ? 
                '<p style="color:#10b981;margin-top:20px;">✓ Grade submitted to Canvas</p>' : '';
            
            document.getElementById('app').innerHTML = `
                <div style="text-align:center;">
                    <h2>Assessment Complete!</h2>
                    <div class="score-display ${scoreClass}" style="flex-direction:column;padding:40px;">
                        <div class="score-label" style="font-size:1.2em;">Final Score</div>
                        <div class="score-value" style="font-size:3em;">${finalScorePercent}%</div>
                    </div>
                    <p>Accuracy: ${(summary.average_accuracy * 100).toFixed(1)}%</p>
                    <p>Explanation: ${(summary.average_explanation * 100).toFixed(1)}%</p>
                    <p>Questions: ${summary.responses.length}</p>
                    ${gradeMsg}
                </div>
            `;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Auto-start on load
        if (window.location.search.includes('question=')) {
            const urlParams = new URLSearchParams(window.location.search);
            const questionData = JSON.parse(decodeURIComponent(urlParams.get('question')));
            showQuestion(questionData);
        }
    """
