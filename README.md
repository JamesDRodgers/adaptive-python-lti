# Adaptive Python Assessment with Canvas LTI 1.3

AI-powered adaptive assessment system for first-year Python programming courses with seamless Canvas LMS integration.

## 🌟 Features

- **Adaptive Learning**: Automatically adjusts difficulty and Bloom's taxonomy levels based on student performance
- **AI Evaluation**: Uses GPT-4o-mini to evaluate answers and explanations
- **Canvas Integration**: Full LTI 1.3 support with automatic grade passback
- **Misconception Tracking**: Identifies learning gaps and generates targeted follow-up questions
- **Real-time Feedback**: Immediate scoring and explanations after each question
- **Modern UI**: Clean, responsive interface that works in Canvas or standalone

## 🏗️ Architecture

```
Canvas LMS → LTI 1.3 Launch → FastAPI Backend → OpenAI API → Grade Passback → Canvas Gradebook
```

### Technology Stack

- **Backend**: FastAPI (Python 3.8+)
- **AI**: OpenAI GPT-4o-mini
- **Authentication**: LTI 1.3 / OAuth 2.0 / JWT
- **Frontend**: Vanilla JavaScript (no framework dependencies)
- **Deployment**: Render / Railway / Fly.io

## 📁 Project Structure

```
adaptive-python-lti/
├── backend/
│   ├── app.py                    # Main FastAPI application with LTI endpoints
│   ├── lti_integration.py        # LTI 1.3 authentication & grade passback
│   ├── requirements.txt          # Python dependencies
│   ├── models/
│   │   └── session.py            # Session state management
│   └── engine/
│       ├── adaptive_engine.py    # Adaptive question selection logic
│       ├── scoring.py            # OpenAI evaluation integration
│       └── questions.jsonl       # Question bank (Bloom levels 1-5)
├── frontend/                     # Optional standalone interface
│   ├── index.html
│   └── main.js
├── CANVAS_LTI_SETUP.md          # Complete Canvas integration guide
├── DEPLOYMENT.md                 # Deployment instructions
└── README.md                     # This file
```

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/JamesDRodgers/adaptive-python-lti.git
cd adaptive-python-lti
```

2. **Set up environment**
```bash
cd backend
cp ../.env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the server**
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

5. **Test it**
- API: http://localhost:8000/health
- Frontend: Open `frontend/index.html` in browser

### Canvas LTI Integration

See **[CANVAS_LTI_SETUP.md](CANVAS_LTI_SETUP.md)** for complete step-by-step instructions.

**Quick overview:**
1. Deploy backend to Render/Railway
2. Configure LTI Developer Key in Canvas
3. Add environment variables (CLIENT_ID, DEPLOYMENT_ID)
4. Create assignment using External Tool
5. Students launch from Canvas and grades sync automatically

## 🎓 How It Works

### Adaptive Logic

The system adjusts difficulty based on performance:

- **Score ≥ 85%**: Increase difficulty + Bloom level
- **Score < 50%**: Decrease difficulty
- **Score < 30%**: Decrease both difficulty and Bloom level

### Bloom's Taxonomy Levels

1. **Remember**: Recall facts (e.g., "What is a variable?")
2. **Understand**: Explain concepts (e.g., "Why does input() return a string?")
3. **Apply**: Use knowledge (e.g., "Write code to swap two variables")
4. **Analyze**: Break down problems (e.g., "What's wrong with this code?")
5. **Evaluate**: Justify decisions (e.g., "When should you use recursion?")

### Misconception Tracking

When the AI detects a misconception, it:
1. Records the specific learning gap
2. Generates a targeted follow-up question
3. Provides immediate corrective feedback

## 🔧 Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-key-here
TOOL_URL=https://your-app.onrender.com

# Canvas LTI (get from Canvas Admin)
LTI_ISSUER=https://canvas.instructure.com
LTI_CLIENT_ID=10000000000001
LTI_DEPLOYMENT_ID=xxx:yyy
```

### Question Bank

Add questions to `backend/engine/questions.jsonl`:

```json
{
  "id": 16,
  "bloom": 3,
  "difficulty": 2,
  "question": "Write a function that returns the sum of even numbers in a list",
  "answer": "def sum_evens(lst): return sum(x for x in lst if x % 2 == 0)",
  "misconceptions": []
}
```

## 📊 API Endpoints

### LTI Endpoints
- `GET /lti/config.json` - Auto-configuration for Canvas
- `GET /lti/jwks` - Public key endpoint
- `GET/POST /lti/login` - OIDC login initiation
- `POST /lti/launch` - LTI launch handler

### Assessment Endpoints
- `GET /start` - Start new assessment session
- `POST /answer` - Submit answer and get evaluation
- `GET /session/{id}` - Get session status
- `DELETE /session/{id}` - End session
- `GET /health` - Health check

## 🎨 Customization

### Custom Question Sets

Create different question banks for different modules:

```python
# In Canvas assignment settings, add custom parameter:
question_set=module2

# Then in app.py, load different questions based on parameter
```

### Grading Weights

Modify in `backend/engine/scoring.py`:

```python
# Adjust how accuracy and explanation are weighted
final_score = (accuracy * 0.7) + (explanation_score * 0.3)
```

### Session Length

Change in `backend/models/session.py`:

```python
self.max_questions = 15  # Adjust number of questions
```

## 🧪 Testing

```bash
# Test local backend
curl http://localhost:8000/health

# Test LTI config
curl http://localhost:8000/lti/config.json

# Test question loading
curl http://localhost:8000/start
```

## 🚢 Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for detailed instructions.

**Recommended hosting:**
- **Backend**: Render (free tier), Railway, or Fly.io
- **Frontend**: GitHub Pages (for standalone use)

## 🔒 Security

- ✅ LTI 1.3 with OAuth 2.0 authentication
- ✅ JWT token validation
- ✅ Nonce verification (prevents replay attacks)
- ✅ RSA key signing
- ✅ CORS protection
- ✅ Input validation with Pydantic
- ✅ Environment-based configuration

**Never commit:**
- `.env` files
- `lti_private_key.pem`
- API keys

## 📈 Future Enhancements

- [ ] Persistent session storage (Redis)
- [ ] Analytics dashboard
- [ ] Multiple language support
- [ ] Code execution environment
- [ ] Peer comparison metrics
- [ ] Instructor feedback interface
- [ ] Export assessment data
- [ ] Integration with other LMS platforms

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

MIT License - feel free to use and modify for your educational needs.

## 💡 Use Cases

- **First-year Python courses**: Adaptive assessment for intro programming
- **Placement testing**: Determine student skill levels
- **Practice exercises**: Formative assessment with immediate feedback
- **Homework assignments**: Graded assignments that adapt to learners
- **Self-paced learning**: Students work through at their own pace

## 📞 Support

- **Canvas Setup Issues**: See [CANVAS_LTI_SETUP.md](CANVAS_LTI_SETUP.md)
- **Deployment Problems**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Questions**: Open an issue on GitHub
- **Security Concerns**: Please report privately

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenAI API](https://openai.com/)
- [LTI 1.3 Standard](https://www.imsglobal.org/spec/lti/v1p3/)

## 📚 Documentation

- [Canvas LTI Setup Guide](CANVAS_LTI_SETUP.md)
- [Deployment Guide](DEPLOYMENT.md)
- [API Documentation](http://your-app.onrender.com/docs) (when deployed)

---

**Built for educators, by educators** 🎓

Make Python learning adaptive and intelligent with AI-powered assessments.
