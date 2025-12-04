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

# ============================================================================
# CORS — Fixed + Development Safe
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",            # Allow all origins in development
        "null",         # Required when frontend loads via file://
        "file://",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# APP STATE
# ============================================================================

SESSIONS: Dict[str, SessionState] = {}

lti_config = LTIConfig()
lti_validator = LTIValidator(lti_config)
lti_grade_submitter = LTIGradeSubmitter(lti_config)

used_nonces = set()  # Prevent OIDC replay

# ============================================================================
# MODELS
# ============================================================================

class AnswerRequest(BaseModel):
    student_answer: str = Field(..., min_length=1, max_length=5000)
    explanation: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., description="Session ID returned by /start")


# ============================================================================
# LTI ENDPOINTS
# ============================================================================

@app.get("/lti/config.json")
async def lti_config_json():
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
                    "placements": [
                        {
                            "placement": "assignment_selection",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": f"{lti_config.tool_url}/lti/launch",
                            "text": "Adaptive Python Assessment",
                            "enabled": True,
                        },
                        {
                            "placement": "link_selection",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": f"{lti_config.tool_url}/lti/launch",
                            "text": "Adaptive Python Assessment",
                            "enabled": True,
                        },
                    ]
                },
                "privacy_level": "public",
            }
        ],
        "public_jwk_url": f"{lti_config.tool_url}/lti/jwks",
        "custom_fields": {},
    }


@app.get("/lti/jwks")
async def lti_jwks():
    return lti_config.get_public_jwks()


@app.get("/lti/login")
@app.post("/lti/login")
async def lti_login(request: Request):
    params = dict(request.query_params)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    used_nonces.add(nonce)

    from urllib.parse import urlencode

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
        "lti_message_hint": params.get("lti_message_hint", ""),
    }

    auth_url = f"{lti_config.auth_login_url}?{urlencode(auth_params)}"
    return RedirectResponse(url=auth_url)


@app.post("/lti/launch")
async def lti_launch(request: Request, id_token: str = Form(...), state: str = Form(...)):
    try:
        claims = lti_validator.validate_launch(id_token)
        if not claims:
            raise HTTPException(401, "Invalid LTI launch token")

        nonce = claims.get("nonce")
        if nonce not in used_nonces:
            raise HTTPException(401, "Invalid or reused nonce")
        used_nonces.discard(nonce)

        user_name = claims.get("name", "Student")
        user_id = claims.get("sub")

        is_gradable = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint" in claims

        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = SessionState()

        if is_gradable:
            store_lti_session(session_id, claims)

        question = next_question(SESSIONS[session_id])
        if not question:
            raise HTTPException(500, "Failed to load initial question")

        return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Adaptive Python Assessment</title>
    <style>{get_embedded_styles()}</style>
</head>
<body>
    <div class="lti-container">
        <div class="header">
            <h1>🐍 Adaptive Python Assessment</h1>
            <p class="user-info">Welcome, {user_name}!</p>
            {"<p class='gradable-notice'>✓ This assessment will be graded</p>" if is_gradable else ""}
        </div>
        <div id="app">
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading...</p>
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

    except Exception as e:
        print("Error in LTI launch:", e)
        raise HTTPException(500, f"Launch error: {e}")


# ============================================================================
# NON-LTI ASSESSMENT ENDPOINTS
# ============================================================================

@app.get("/start")
def start():
    try:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = SessionState()

        question = next_question(SESSIONS[session_id])
        if not question:
            raise HTTPException(500, "Failed to load question")

        return {"session_id": session_id, "question": question}

    except Exception as e:
        raise HTTPException(500, f"Error starting assessment: {e}")


@app.post("/answer")
def answer(request: AnswerRequest):
    try:
        session = SESSIONS.get(request.session_id)
        if not session:
            raise HTTPException(404, "Session not found")

        # Score the current response
        evaluation = score_response(session, {
            "student_answer": request.student_answer,
            "explanation": request.explanation,
        })

        # CHECK IF FINISHED AFTER SCORING (question_number is now incremented)
        if session.question_number > session.max_questions:
            session.finished = True
            summary = session.summary()

            # Submit grade if LTI session
            lti_claims = get_lti_session(request.session_id)
            if lti_claims:
                summary["grade_submitted"] = lti_grade_submitter.submit_grade(
                    id_token_claims=lti_claims,
                    score=summary["final_score"],
                    max_score=1.0,
                    comment=f"Accuracy: {summary['average_accuracy']:.1%}, Explanation: {summary['average_explanation']:.1%}"
                )

            # Clean up session
            del SESSIONS[request.session_id]

            return {
                "evaluation": evaluation,
                "finished": True,
                "summary": summary,
            }

        # Not finished - get next question
        next_q = next_question(session)
        
        return {
            "evaluation": evaluation,
            "finished": False,
            "next_question": next_q,
        }

    except Exception as e:
        print(f"Error processing answer: {e}")
        raise HTTPException(500, f"Error processing answer: {e}")


@app.get("/session/{session_id}")
def get_session_status(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    return {
        "question_number": session.question_number,
        "max_questions": session.max_questions,
        "bloom_level": session.bloom_level,
        "difficulty": session.difficulty,
        "finished": session.finished,
        "is_lti_session": get_lti_session(session_id) is not None,
    }


@app.delete("/session/{session_id}")
def end_session(session_id: str):
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return {"message": "Session ended"}

    raise HTTPException(404, "Session not found")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "active_sessions": len(SESSIONS),
        "lti_configured": bool(lti_config.client_id),
    }


# ============================================================================
# EMBEDDED UI RESOURCES
# ============================================================================

def get_embedded_styles():
    return """
        * { box-sizing: border-box; }
        body { font-family: sans-serif; background: #f5f5f5; padding: 20px; }
        .lti-container { max-width: 900px; margin: auto; }
        .header {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white; padding: 30px; border-radius: 12px 12px 0 0;
            text-align: center;
        }
        #app { background: white; padding: 40px; min-height: 300px;
               border-radius: 0 0 12px 12px; }
        .spinner {
            border: 4px solid #ddd;
            border-top: 4px solid #667eea;
            width: 40px; height: 40px;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: auto;
        }
        @keyframes spin { 
            0% { transform: rotate(0deg); } 
            100% { transform: rotate(360deg); } 
        }
    """


def get_embedded_javascript():
    return """
        let currentSessionId = SESSION_ID;

        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }

        function showQuestion(question) {
            const app = document.getElementById("app");
            app.innerHTML = `
                <div>
                    <h2>${escapeHtml(question.question)}</h2>
                    <textarea id="answer" rows="4" placeholder="Your answer..."></textarea>
                    <br><br>
                    <textarea id="explanation" rows="4" placeholder="Explain your reasoning..."></textarea>
                    <br><br>
                    <button onclick="submitAnswer()">Submit</button>
                </div>
            `;
        }

        async function submitAnswer() {
            const answer = document.getElementById("answer").value.trim();
            const explanation = document.getElementById("explanation").value.trim();

            if (!answer || !explanation) {
                alert("Both fields are required");
                return;
            }

            const payload = {
                student_answer: answer,
                explanation: explanation,
                session_id: currentSessionId,
            };

            document.getElementById("app").innerHTML =
                '<div class="loading"><div class="spinner"></div><p>Evaluating...</p></div>';

            const res = await fetch(API + "/answer", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });

            const data = await res.json();

            if (data.finished) {
                showSummary(data.summary);
            } else {
                showQuestion(data.next_question);
            }
        }

        function showSummary(summary) {
            document.getElementById("app").innerHTML = `
                <h2>Assessment Complete!</h2>
                <p>Final Score: ${(summary.final_score * 100).toFixed(1)}%</p>
                <p>Accuracy: ${(summary.average_accuracy * 100).toFixed(1)}%</p>
                <p>Explanation: ${(summary.average_explanation * 100).toFixed(1)}%</p>
                <p>Questions Answered: ${summary.responses.length}</p>
            `;
        }
    """