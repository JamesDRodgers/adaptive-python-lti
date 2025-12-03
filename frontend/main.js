const API = "https://adaptive-python-lti.onrender.com";
let sessionId = null;

// Start assessment on page load
async function start() {
    try {
        showLoading("Starting assessment...");
        const response = await fetch(`${API}/start`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;
        showQuestion(data.question);
    } catch (error) {
        showError("Failed to start assessment. Please refresh the page.", error);
    }
}

// Submit answer
async function submitAnswer() {
    const answerInput = document.getElementById("answer");
    const explanationInput = document.getElementById("explanation");

    const answer = answerInput.value.trim();
    const explanation = explanationInput.value.trim();

    // Validate inputs
    if (!answer) {
        alert("Please provide an answer");
        answerInput.focus();
        return;
    }

    if (!explanation) {
        alert("Please provide an explanation");
        explanationInput.focus();
        return;
    }

    try {
        showLoading("Evaluating your response...");

        const response = await fetch(`${API}/answer`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                student_answer: answer,
                explanation: explanation,
                session_id: sessionId
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Show evaluation feedback
        showFeedback(data.evaluation);

        // Wait a moment for user to read feedback
        await new Promise(resolve => setTimeout(resolve, 2000));

        if (data.finished) {
            showSummary(data.summary);
        } else {
            showQuestion(data.next_question);
        }

    } catch (error) {
        showError("Failed to submit answer. Please try again.", error);
    }
}

// Display question
function showQuestion(question) {
    if (!question) {
        showError("No question available");
        return;
    }

    const app = document.getElementById("app");
    app.innerHTML = `
        <div class="question-container">
            <div class="question-header">
                <span class="difficulty">Difficulty: ${question.difficulty || 'N/A'}</span>
                <span class="bloom">Bloom Level: ${question.bloom || 'N/A'}</span>
            </div>
            <h2 class="question">${escapeHtml(question.question)}</h2>
            
            <div class="form-group">
                <label for="answer">Your Answer:</label>
                <textarea 
                    id="answer" 
                    placeholder="Enter your answer here..." 
                    rows="4"
                ></textarea>
            </div>
            
            <div class="form-group">
                <label for="explanation">Explain Your Reasoning:</label>
                <textarea 
                    id="explanation" 
                    placeholder="Explain why you believe this is the correct answer..." 
                    rows="4"
                ></textarea>
            </div>
            
            <button onclick="submitAnswer()" class="submit-btn">Submit Answer</button>
        </div>
    `;

    // Focus on first input
    document.getElementById("answer").focus();
}

// Show evaluation feedback
function showFeedback(evaluation) {
    const app = document.getElementById("app");

    const scoreClass = evaluation.final_score >= 0.7 ? 'good' :
        evaluation.final_score >= 0.5 ? 'okay' : 'poor';

    let misconceptionsHtml = '';
    if (evaluation.misconceptions && evaluation.misconceptions.length > 0) {
        misconceptionsHtml = `
            <div class="misconceptions">
                <h3>Areas to Review:</h3>
                <ul>
                    ${evaluation.misconceptions.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    app.innerHTML = `
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
            ${misconceptionsHtml}
            <p class="next-question-message">Loading next question...</p>
        </div>
    `;
}

// Show final summary
function showSummary(summary) {
    const app = document.getElementById("app");

    const finalScorePercent = (summary.final_score * 100).toFixed(1);
    const scoreClass = summary.final_score >= 0.7 ? 'good' :
        summary.final_score >= 0.5 ? 'okay' : 'poor';

    app.innerHTML = `
        <div class="summary-container">
            <h2>Assessment Complete!</h2>
            
            <div class="final-score ${scoreClass}">
                <div class="score-label">Final Score</div>
                <div class="score-value">${finalScorePercent}%</div>
            </div>
            
            <div class="summary-stats">
                <div class="stat">
                    <span class="stat-label">Average Accuracy:</span>
                    <span class="stat-value">${(summary.average_accuracy * 100).toFixed(1)}%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Average Explanation:</span>
                    <span class="stat-value">${(summary.average_explanation * 100).toFixed(1)}%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Questions Answered:</span>
                    <span class="stat-value">${summary.responses.length}</span>
                </div>
            </div>
            
            <button onclick="location.reload()" class="restart-btn">Start New Assessment</button>
        </div>
    `;
}

// Show loading state
function showLoading(message) {
    const app = document.getElementById("app");
    app.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

// Show error message
function showError(message, error = null) {
    const app = document.getElementById("app");

    if (error) {
        console.error("Error:", error);
    }

    app.innerHTML = `
        <div class="error">
            <h2>Error</h2>
            <p>${escapeHtml(message)}</p>
            <button onclick="location.reload()" class="restart-btn">Reload Page</button>
        </div>
    `;
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Start the assessment when page loads
start();
