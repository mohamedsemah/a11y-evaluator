# ***LLM Accessibility based Tool for Infotainment Systems***

A production-ready tool for analyzing accessibility issues in infotainment system code using multiple Large Language Models (GPT-4o, Claude Opus 4, and Llama).

## Features

- Multi-file code upload support (including ZIP files)
- Parallel analysis using multiple LLMs
- A/B testing capabilities for model comparison
- Interactive code editor with diff view
- One-click fix application
- Batch fixing of multiple issues
- User rating system for LLM suggestions
- PDF report generation
- Complete research metrics tracking

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Docker & Docker Compose (optional)

## Quick Start with Docker

1. Clone the repository and navigate to the project directory

2. Copy the environment template and add your API keys:
```bash
cp .env.template .env
# Edit .env with your API keys
```

3. Start the application:
```bash
docker-compose up -d
```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
   - PgAdmin: http://localhost:5050 (admin@example.com / admin)

## Manual Setup

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database:
```bash
# Create database
createdb llm_analyzer

# Run schema
psql -d llm_analyzer -f database.sql
```

3. Configure environment variables:
```bash
cp .env.template .env
# Edit .env with your configurations
```

4. Start the backend server:
```bash
python backend.py
```

### Frontend Setup

1. Install Node dependencies:
```bash
npm install
```

2. Start the frontend:
```bash
npm run dev
```

## API Keys Configuration

Edit your `.env` file with your actual API keys:

- **OpenAI**: Get your API key from https://platform.openai.com/api-keys
- **Anthropic**: Get your API key from https://console.anthropic.com/
- **Llama**: Depending on your provider (Replicate, Hugging Face, etc.)

## Usage

1. **Register/Login**: Create an account or login to the system
2. **Upload Files**: Upload your code files (max 10MB each) or ZIP archives
3. **Select Models**: Choose which LLMs to use for analysis
4. **Start Analysis**: Click "Start Analysis" to begin
5. **Review Results**: 
   - View detected issues with severity levels
   - Compare results across different models
   - Rate the quality of suggestions (1-5 stars)
6. **Apply Fixes**:
   - Select issues to fix
   - View diff of changes
   - Apply fixes individually or in batch
7. **Generate Report**: Download a PDF report of findings

## File Structure

```
llm-accessibility-analyzer/
│
├── backend.py                 # FastAPI server with all endpoints
├── models.py                  # SQLAlchemy database models
├── llm_analyzer.py            # LLM integration and analysis logic
├── database.sql               # PostgreSQL schema and setup
├── requirements.txt           # Python dependencies
├── .env.template              # Environment variables template
├── package.json               # Node.js dependencies
├── docker-compose.yml         # Docker orchestration
├── README.md                  # Setup and usage instructions
│
├── src/                       # Frontend source directory
│   ├── App.jsx                # React application 
│   └── main.jsx               # React entry point 
│
├── index.html                 # HTML entry point
├── vite.config.js             # Vite configuration 
│
├── Dockerfile.backend         # Backend Docker image (optional)
├── Dockerfile.frontend        # Frontend Docker image (optional)
│
└── .gitignore                 # Git ignore file 
```


## Supported File Types

- Web: HTML, CSS, JavaScript, TypeScript, JSX, TSX
- Native: Swift, Kotlin, Java
- Embedded: C, C++, Header files
- Config: XML
- Archives: ZIP

## Research Metrics Collected

- Analysis timestamps and duration
- Token usage per model
- API response times
- Issue detection counts by category/severity
- User ratings for each suggestion
- Fix acceptance rates
- Cross-model agreement statistics

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- Verify user permissions

### LLM API Errors
- Verify API keys are correct
- Check API rate limits
- Ensure sufficient credits/quota

### File Upload Issues
- Check file size (max 10MB)
- Verify file encoding (UTF-8)
- Ensure proper file permissions

## Security Notes

- Change JWT_SECRET_KEY in production
- Use HTTPS in production
- Implement rate limiting for API endpoints
- Regular security audits recommended

## Development

To modify the code:

1. Backend changes: Edit `backend.py`, `models.py`, or `llm_analyzer.py`
2. Frontend changes: Edit `frontend.jsx` (src/App.jsx)
3. Database changes: Update `database.sql` and run migrations

## Production Deployment

1. Use a production-grade web server (e.g., Gunicorn)
2. Set up reverse proxy (e.g., Nginx)
3. Enable HTTPS with SSL certificates
4. Configure firewall rules
5. Set up monitoring and logging
6. Regular database backups

## Support

For issues related to:
- API keys: Check provider documentation
- Database: PostgreSQL documentation
- Frontend: React/Chakra UI documentation
- Backend: FastAPI documentation

## License

This tool is for research purposes. Ensure compliance with API providers' terms of service.
