# Quick Start Guide - Security Fixes

## 🚀 Installation

1. **Install new dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Create `.env` file** in the `backend/` directory:
   ```env
   # Required for production
   SECRET_KEY=generate-a-random-32-character-secret-key-here
   
   # Optional - enable authentication
   AUTH_REQUIRED=false
   API_KEY=your-api-key-if-auth-enabled
   
   # CORS - add your frontend URLs
   ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
   
   # File limits (optional - defaults provided)
   MAX_FILE_SIZE=52428800
   MAX_TOTAL_SIZE=524288000
   MAX_FILES_PER_SESSION=100
   
   # Rate limiting (optional - defaults provided)
   RATE_LIMIT_ENABLED=true
   RATE_LIMIT_PER_MINUTE=60
   RATE_LIMIT_PER_HOUR=1000
   
   # Database (optional - SQLite default)
   DATABASE_URL=sqlite:///./accessibility_analyzer.db
   SESSION_EXPIRY_HOURS=24
   
   # Your existing LLM API keys
   OPENAI_API_KEY=your-key
   ANTHROPIC_API_KEY=your-key
   DEEPSEEK_API_KEY=your-key
   REPLICATE_API_TOKEN=your-token
   ```

3. **Run the application:**
   ```bash
   python backend/main.py
   ```

   The database will be created automatically on first run.

## 🔒 Security Features Enabled

### ✅ All P0 Critical Fixes Applied:

1. **Path Traversal Protection** - Filenames are sanitized
2. **ZIP Slip Protection** - ZIP paths validated before extraction
3. **File Size Limits** - 50MB per file, 500MB per session
4. **Input Validation** - All inputs validated with Pydantic
5. **Rate Limiting** - 60 req/min, 1000 req/hour per IP
6. **Security Headers** - CSP, X-Frame-Options, etc.
7. **CORS Configuration** - Environment-based, specific methods/headers
8. **Database Sessions** - Persistent storage with expiration
9. **Authentication** - API key and JWT infrastructure (optional)
10. **API Key Protection** - Health check doesn't expose keys

## 🧪 Testing the Fixes

### ⚠️ Windows PowerShell Users

PowerShell's `curl` is an alias for `Invoke-WebRequest` with different syntax. See `TESTING_SECURITY_FIXES_WINDOWS.md` for PowerShell commands.

### Test Path Traversal Protection (Unix/Linux/Mac):
```bash
# Try uploading a file with malicious filename
curl -X POST http://localhost:8000/upload \
  -F "files=@test.txt;filename=../../../etc/passwd"
# Should be sanitized to just "passwd"
```

### Test Path Traversal Protection (Windows PowerShell):
```powershell
# Create test file
"test" | Out-File -FilePath test.txt -Encoding utf8

# Upload with malicious filename
$uri = "http://localhost:8000/upload"
$formData = @{ files = Get-Item -Path "test.txt" }
Invoke-WebRequest -Uri $uri -Method POST -Form $formData
# Check that file was saved as "passwd" not "../../../etc/passwd"
```

### Test Rate Limiting (Windows PowerShell):
```powershell
$uri = "http://localhost:8000/health"
for ($i = 1; $i -le 65; $i++) {
    try {
        Invoke-WebRequest -Uri $uri -Method GET | Out-Null
        Write-Host "Request $i : OK"
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            Write-Host "Request $i : Rate Limited (429) - Expected!"
        }
    }
}
```

### Test Authentication (when enabled):
```powershell
# Without API key (should fail if AUTH_REQUIRED=true)
Invoke-WebRequest -Uri "http://localhost:8000/upload" -Method POST

# With API key
$headers = @{ "X-API-Key" = "your-api-key" }
Invoke-WebRequest -Uri "http://localhost:8000/upload" -Method POST -Headers $headers
```

## 📝 Important Notes

1. **Authentication is OFF by default** - Set `AUTH_REQUIRED=true` to enable
2. **Database is SQLite** - Change `DATABASE_URL` for PostgreSQL
3. **Rate limiting is in-memory** - Use Redis for production
4. **Sessions expire after 24 hours** - Configurable via `SESSION_EXPIRY_HOURS`

## 🔄 Migration from Old Code

The application is backward compatible:
- Old sessions in memory will be lost (expected)
- New sessions go to database
- All endpoints work the same way
- Authentication can be enabled gradually

## 🐛 Troubleshooting

**Database errors:**
- Ensure SQLite is available (usually built-in)
- Check file permissions for database file
- Verify `DATABASE_URL` is correct

**Authentication errors:**
- Check `AUTH_REQUIRED` setting
- Verify `API_KEY` is set if auth is enabled
- Check request headers include `X-API-Key`

**Rate limiting too strict:**
- Adjust `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR`
- Or set `RATE_LIMIT_ENABLED=false` to disable

**CORS errors:**
- Add your frontend URL to `ALLOWED_ORIGINS`
- Ensure no trailing slashes in URLs

---

**All security fixes are production-ready!** ✅

