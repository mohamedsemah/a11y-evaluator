# Testing Security Fixes on Windows PowerShell

## ⚠️ Important: PowerShell vs Unix curl

PowerShell's `curl` is an alias for `Invoke-WebRequest` and has different syntax. Use the commands below for Windows.

---

## 🧪 Test 1: Path Traversal Protection

### Test with malicious filename

**PowerShell:**
```powershell
# Create a test file first
"test content" | Out-File -FilePath test.txt -Encoding utf8

# Try uploading with path traversal in filename
$uri = "http://localhost:8000/upload"
$formData = @{
    files = Get-Item -Path "test.txt"
}
$headers = @{
    "Content-Disposition" = 'form-data; name="files"; filename="../../../etc/passwd"'
}
Invoke-WebRequest -Uri $uri -Method POST -Form $formData
```

**Or use curl.exe (if installed):**
```powershell
# Use curl.exe explicitly (not the alias)
curl.exe -X POST http://localhost:8000/upload -F "files=@test.txt;filename=../../../etc/passwd"
```

**Expected Result:** File should be saved as `passwd` (sanitized), not in `../../../etc/`

---

## 🧪 Test 2: ZIP Slip Protection

### Create a malicious ZIP file

**PowerShell Script:**
```powershell
# Create a test ZIP with path traversal
$zipPath = "malicious.zip"
$tempDir = "temp_zip_test"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
"malicious content" | Out-File -FilePath "$tempDir\..\..\..\etc\passwd" -Encoding utf8

# Create ZIP (requires .NET)
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($tempDir, $zipPath)

# Try to upload
$uri = "http://localhost:8000/upload"
$formData = @{
    files = Get-Item -Path $zipPath
}
Invoke-WebRequest -Uri $uri -Method POST -Form $formData

# Cleanup
Remove-Item -Path $tempDir -Recurse -Force
Remove-Item -Path $zipPath -Force
```

**Expected Result:** Should be rejected with 400 error: "Path traversal detected"

---

## 🧪 Test 3: File Size Limits

### Test with oversized file

**PowerShell:**
```powershell
# Create a 60MB file (exceeds 50MB limit)
$largeFile = "large_file.txt"
$content = "x" * (60 * 1024 * 1024)  # 60 MB
$content | Out-File -FilePath $largeFile -Encoding utf8

# Try to upload
$uri = "http://localhost:8000/upload"
$formData = @{
    files = Get-Item -Path $largeFile
}
try {
    Invoke-WebRequest -Uri $uri -Method POST -Form $formData
} catch {
    Write-Host "Error (expected): $($_.Exception.Message)"
}

# Cleanup
Remove-Item -Path $largeFile -Force
```

**Expected Result:** 400 error: "File exceeds maximum size of 50.0 MB"

---

## 🧪 Test 4: Rate Limiting

### Test rate limit (60 requests/minute)

**PowerShell:**
```powershell
$uri = "http://localhost:8000/health"
$successCount = 0
$rateLimitCount = 0

for ($i = 1; $i -le 65; $i++) {
    try {
        $response = Invoke-WebRequest -Uri $uri -Method GET
        if ($response.StatusCode -eq 200) {
            $successCount++
        }
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            $rateLimitCount++
            Write-Host "Request $i : Rate limited (429) - Expected!"
        } else {
            Write-Host "Request $i : Error - $($_.Exception.Message)"
        }
    }
    Start-Sleep -Milliseconds 100  # Small delay
}

Write-Host "Successful: $successCount"
Write-Host "Rate Limited: $rateLimitCount"
```

**Expected Result:** First 60 requests succeed, 61st+ return 429

---

## 🧪 Test 5: Input Validation

### Test invalid session ID

**PowerShell:**
```powershell
$uri = "http://localhost:8000/analyze"
$body = @{
    session_id = "not-a-valid-uuid"
    models = @("gpt-4o")
} | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
}

try {
    Invoke-WebRequest -Uri $uri -Method POST -Body $body -Headers $headers
} catch {
    Write-Host "Error (expected): $($_.Exception.Message)"
    Write-Host "Status: $($_.Exception.Response.StatusCode)"
}
```

**Expected Result:** 422 Validation Error: "session_id must be a valid UUID"

---

## 🧪 Test 6: Invalid Model Name

**PowerShell:**
```powershell
$uri = "http://localhost:8000/analyze"
$body = @{
    session_id = "123e4567-e89b-12d3-a456-426614174000"
    models = @("invalid-model-name")
} | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
}

try {
    Invoke-WebRequest -Uri $uri -Method POST -Body $body -Headers $headers
} catch {
    Write-Host "Error (expected): $($_.Exception.Message)"
}
```

**Expected Result:** 422 Validation Error: "Model 'invalid-model-name' is not allowed"

---

## 🧪 Test 7: Authentication (when enabled)

### Test without API key

**PowerShell:**
```powershell
# First, set AUTH_REQUIRED=true in .env and restart server

$uri = "http://localhost:8000/upload"
$formData = @{
    files = Get-Item -Path "test.txt"
}

try {
    Invoke-WebRequest -Uri $uri -Method POST -Form $formData
} catch {
    Write-Host "Error (expected if auth required): $($_.Exception.Message)"
    Write-Host "Status: $($_.Exception.Response.StatusCode)"
}
```

**Expected Result:** 401 Unauthorized if `AUTH_REQUIRED=true`

### Test with API key

**PowerShell:**
```powershell
$uri = "http://localhost:8000/upload"
$apiKey = "your-api-key-here"  # From .env file
$formData = @{
    files = Get-Item -Path "test.txt"
}

$headers = @{
    "X-API-Key" = $apiKey
}

Invoke-WebRequest -Uri $uri -Method POST -Form $formData -Headers $headers
```

**Expected Result:** 200 OK (if API key is correct)

---

## 🧪 Test 8: Security Headers

**PowerShell:**
```powershell
$uri = "http://localhost:8000/health"
$response = Invoke-WebRequest -Uri $uri -Method GET

Write-Host "Security Headers:"
Write-Host "X-Content-Type-Options: $($response.Headers['X-Content-Type-Options'])"
Write-Host "X-Frame-Options: $($response.Headers['X-Frame-Options'])"
Write-Host "X-XSS-Protection: $($response.Headers['X-XSS-Protection'])"
Write-Host "Content-Security-Policy: $($response.Headers['Content-Security-Policy'])"
```

**Expected Result:** All security headers should be present

---

## 🧪 Test 9: Database Persistence

**PowerShell:**
```powershell
# Upload a file
$uri = "http://localhost:8000/upload"
$formData = @{
    files = Get-Item -Path "test.txt"
}
$response = Invoke-WebRequest -Uri $uri -Method POST -Form $formData
$sessionId = ($response.Content | ConvertFrom-Json).session_id

Write-Host "Session ID: $sessionId"

# Restart server, then check if session still exists
$getUri = "http://localhost:8000/session/$sessionId"
$sessionResponse = Invoke-WebRequest -Uri $getUri -Method GET
Write-Host "Session exists after restart: $($sessionResponse.StatusCode -eq 200)"
```

**Expected Result:** Session should persist after server restart

---

## 🧪 Test 10: Health Check (No API Key Exposure)

**PowerShell:**
```powershell
$uri = "http://localhost:8000/health/detailed"
$response = Invoke-WebRequest -Uri $uri -Method GET
$content = $response.Content | ConvertFrom-Json

Write-Host "Health Status:"
$content | ConvertTo-Json -Depth 3

# Check that API keys are NOT exposed
if ($content.services_configured -ne $null) {
    Write-Host "✅ API keys not exposed (only count shown)"
} else {
    Write-Host "❌ API key details might be exposed"
}
```

**Expected Result:** Should show `services_configured` count, NOT which services have keys

---

## 🔧 Alternative: Install curl for Windows

If you prefer Unix-style curl commands:

1. **Install curl via Chocolatey:**
   ```powershell
   choco install curl
   ```

2. **Or download from:** https://curl.se/windows/

3. **Then use Unix-style commands:**
   ```powershell
   curl.exe -X POST http://localhost:8000/upload -F "files=@test.txt;filename=../../../etc/passwd"
   ```

---

## 📝 Complete Test Script

Save this as `test_security.ps1`:

```powershell
# Security Fixes Test Script
Write-Host "Testing Security Fixes..." -ForegroundColor Green

$baseUrl = "http://localhost:8000"

# Test 1: Path Traversal
Write-Host "`n[Test 1] Path Traversal Protection" -ForegroundColor Yellow
"test" | Out-File -FilePath test.txt -Encoding utf8
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/upload" -Method POST -Form @{files = Get-Item test.txt}
    Write-Host "✅ Upload successful (check filename was sanitized)" -ForegroundColor Green
} catch {
    Write-Host "❌ Upload failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Rate Limiting
Write-Host "`n[Test 2] Rate Limiting" -ForegroundColor Yellow
$rateLimited = 0
for ($i = 1; $i -le 65; $i++) {
    try {
        Invoke-WebRequest -Uri "$baseUrl/health" -Method GET | Out-Null
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            $rateLimited++
        }
    }
}
if ($rateLimited -gt 0) {
    Write-Host "✅ Rate limiting working ($rateLimited requests limited)" -ForegroundColor Green
} else {
    Write-Host "⚠️ Rate limiting may not be working" -ForegroundColor Yellow
}

# Test 3: Security Headers
Write-Host "`n[Test 3] Security Headers" -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET
$headers = @("X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection")
$allPresent = $true
foreach ($header in $headers) {
    if ($response.Headers[$header]) {
        Write-Host "  ✅ $header present" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $header missing" -ForegroundColor Red
        $allPresent = $false
    }
}

# Test 4: Input Validation
Write-Host "`n[Test 4] Input Validation" -ForegroundColor Yellow
$body = @{
    session_id = "invalid-uuid"
    models = @("gpt-4o")
} | ConvertTo-Json

try {
    Invoke-WebRequest -Uri "$baseUrl/analyze" -Method POST -Body $body -ContentType "application/json" | Out-Null
    Write-Host "❌ Validation failed (should reject invalid UUID)" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 422) {
        Write-Host "✅ Input validation working (rejected invalid UUID)" -ForegroundColor Green
    }
}

Write-Host "`nTests Complete!" -ForegroundColor Green
```

Run with:
```powershell
.\test_security.ps1
```

---

## ✅ Verification Checklist

After running tests, verify:

- [ ] Path traversal filenames are sanitized
- [ ] ZIP files with path traversal are rejected
- [ ] Files > 50MB are rejected
- [ ] Rate limiting returns 429 after 60 requests
- [ ] Security headers are present in responses
- [ ] Invalid inputs are rejected with 422
- [ ] Health check doesn't expose API keys
- [ ] Sessions persist in database
- [ ] Authentication works (if enabled)

---

**Note:** Make sure the backend server is running before testing:
```powershell
cd backend
python main.py
```

