# Infotainment Accessibility Analyzer

A local, open-source web tool that detects and fixes WCAG 2.2-based accessibility issues in infotainment system UI code using multiple LLMs for performance comparison.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- API keys for the LLMs you want to use

### Backend Setup (FastAPI)

1. **Install Python dependencies:**
```bash
pip install fastapi uvicorn python-multipart
pip install openai anthropic httpx
pip install reportlab
pip install python-dotenv
```

2. **Create environment file:**
```bash
# Create .env file in backend directory
touch .env
```

Add your API keys to `.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
LLAMA_API_KEY=your_llama_api_key_here
```

3. **Create the backend structure:**
```bash
mkdir infotainment-accessibility-analyzer
cd infotainment-accessibility-analyzer
mkdir backend
mkdir temp_projects
```

4. **Save the backend code as `backend/main.py`**

5. **Run the FastAPI server:**
```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup (React)

1. **Create React app:**
```bash
# In the main project directory
npx create-react-app frontend
cd frontend
```

2. **Install additional dependencies:**
```bash
npm install lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

3. **Configure Tailwind CSS:**

Update `tailwind.config.js`:
```javascript
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

4. **Add Tailwind to CSS:**

Replace `src/index.css` content:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

5. **Replace `src/App.js` with the provided React component**

6. **Start the React development server:**
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## 🛠️ Usage Instructions

### 1. Upload Infotainment Code
- Navigate to the Upload tab
- Select multiple files (HTML, JSX, XML, CSS, C++, Java, etc.)
- Click "Upload Project"

### 2. Analyze for Issues
- Go to Analysis tab
- Choose an LLM model for detection (GPT-4o, Claude Opus 4, DeepSeek V3, or LLaMA Maverick)
- Click "Start Analysis"

### 3. Fix Issues
- Review detected issues in the Results tab
- For each issue, select a model for remediation
- Click the dropdown to choose fixing model
- View diff comparisons of original vs fixed code

### 4. Compare Performance
- Visit the Comparison tab to see model performance metrics
- Rate fixes using the expert rating system (1-5 stars)
- Download fixes as ZIP or generate PDF reports

### 5. Export Results
- **Download Fixes**: ZIP file containing all fixed code files
- **Download Report**: PDF report with analysis summary and metrics

## 🔧 API Endpoints

### Core Endpoints
- `POST /upload-project` - Upload multiple code files
- `POST /analyze/{project_id}` - Analyze project with specified LLM
- `POST /fix-issue/{project_id}/{issue_id}` - Fix specific issue with chosen LLM
- `GET /project/{project_id}` - Get project details and results
- `GET /download-fixes/{project_id}` - Download ZIP of fixed files
- `GET /download-report/{project_id}` - Download PDF report
- `GET /health` - Health check endpoint

## 📊 WCAG 2.2 Coverage

The tool focuses on all POUR principles:

### Perceivable
- Color contrast ratios
- Text alternatives for images
- Captions and transcripts
- Sensory characteristics

### Operable
- Keyboard navigation
- Focus management
- Touch target sizes
- Motion and animation controls

### Understandable
- Clear labeling
- Consistent navigation
- Error identification and suggestions
- Language specification

### Robust
- Valid markup
- Assistive technology compatibility
- Future-proofing considerations

## 🎯 Model Comparison Features

### Detection Metrics
- **Coverage**: Number of real WCAG issues found
- **Precision**: Accuracy of detections
- **Confidence**: Model's confidence in each detection
- **Response Time**: Time taken for analysis

### Remediation Metrics
- **Fix Quality**: Expert rating system (1-5 stars)
- **Fix Time**: Time taken to generate fixes
- **Code Changes**: Diff visualization with `// PATCHED` annotations
- **Explanation Quality**: Clarity of fix explanations

### Evaluation Tools
- **Split-view Diff**: Side-by-side code comparison
- **Syntax Highlighting**: Easy-to-read code differences
- **Expert Rating Interface**: Human evaluation of fix quality
- **Performance Dashboard**: Comparative metrics across models

## 🔄 Real-time Features

- **Live Analysis**: Real-time LLM integration with authentic results
- **Progress Tracking**: Live status updates during analysis and fixing
- **Interactive Fixes**: Choose different models for each individual fix
- **Instant Diff View**: Immediate code comparison after fixes
- **Performance Monitoring**: Real-time metrics collection

## 📁 Project Structure

```
infotainment-accessibility-analyzer/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── .env                    # API keys (create this)
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js             # React application
│   │   └── index.css          # Tailwind CSS
│   ├── package.json
│   └── tailwind.config.js
├── temp_projects/             # Uploaded project storage
└── README.md                  # This file
```

## 🚨 Important Notes

- **No Mock Data**: All results are generated by real LLM APIs
- **Local Storage**: Projects stored locally, no cloud dependencies
- **API Keys Required**: Must provide valid API keys for LLMs to function
- **File Preservation**: Maintains file relationships and import structures
- **Expert Validation**: Includes human rating system for fix quality assessment

## 🔐 Security Considerations

- All processing happens locally
- API keys stored in environment variables
- No data sent to external services except LLM APIs
- Temporary file cleanup after processing
- No authentication required for local use

## 🐛 Troubleshooting

### Common Issues
1. **API Key Errors**: Ensure all API keys are correctly set in `.env`
2. **CORS Issues**: Backend runs on 8000, frontend on 3000
3. **Upload Failures**: Check file permissions and disk space
4. **LLM Timeouts**: Some models may take longer to respond

### Performance Tips
- Start with smaller projects for initial testing
- Use different models for detection vs remediation
- Rate limit calls if using free API tiers
- Monitor token usage for cost management

## 📈 Future Enhancements

Potential improvements for production use:
- Database integration for persistent storage
- User authentication and project management
- Docker containerization
- CI/CD pipeline integration
- Advanced reporting and analytics
- Batch processing capabilities
- Custom WCAG rule configurations