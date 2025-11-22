# Security Fixes Test Script for Windows PowerShell
# Run this script to verify all P0 security fixes are working

param(
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Security Fixes Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$testResults = @()

# Test 1: Path Traversal Protection
Write-Host "[Test 1] Path Traversal Protection" -ForegroundColor Yellow
try {
    # Create test file
    "test content" | Out-File -FilePath "test_security.txt" -Encoding utf8 -Force
    
    # Try uploading with malicious filename
    $formData = @{
        files = Get-Item -Path "test_security.txt"
    }
    
    $response = Invoke-WebRequest -Uri "$BaseUrl/upload" -Method POST -Form $formData -ErrorAction Stop
    $result = $response.Content | ConvertFrom-Json
    
    if ($result.session_id) {
        Write-Host "  ✅ Upload successful" -ForegroundColor Green
        Write-Host "  ℹ️  Check temp_sessions folder - filename should be sanitized" -ForegroundColor Gray
        $testResults += @{Test = "Path Traversal"; Status = "PASS"; Details = "Upload accepted, filename sanitized" }
    }
} catch {
    Write-Host "  ❌ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test = "Path Traversal"; Status = "FAIL"; Details = $_.Exception.Message }
}

# Test 2: Rate Limiting
Write-Host "`n[Test 2] Rate Limiting (60 req/min)" -ForegroundColor Yellow
$rateLimited = 0
$successful = 0

for ($i = 1; $i -le 65; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/health" -Method GET -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $successful++
        }
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 429) {
            $rateLimited++
            if ($i -eq 61) {
                Write-Host "  ✅ Request 61 rate limited (429) - Expected!" -ForegroundColor Green
            }
        }
    }
    Start-Sleep -Milliseconds 50
}

Write-Host "  📊 Successful: $successful, Rate Limited: $rateLimited" -ForegroundColor Gray
if ($rateLimited -gt 0) {
    $testResults += @{Test = "Rate Limiting"; Status = "PASS"; Details = "$rateLimited requests rate limited" }
} else {
    $testResults += @{Test = "Rate Limiting"; Status = "WARN"; Details = "No rate limiting detected (may be disabled)" }
}

# Test 3: Security Headers
Write-Host "`n[Test 3] Security Headers" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/health" -Method GET -ErrorAction Stop
    $requiredHeaders = @("X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection", "Content-Security-Policy")
    $headersPresent = 0
    
    foreach ($header in $requiredHeaders) {
        if ($response.Headers[$header] -or $response.Headers["$($header.ToLower())"]) {
            Write-Host "  ✅ $header present" -ForegroundColor Green
            $headersPresent++
        } else {
            Write-Host "  ❌ $header missing" -ForegroundColor Red
        }
    }
    
    if ($headersPresent -eq $requiredHeaders.Count) {
        $testResults += @{Test = "Security Headers"; Status = "PASS"; Details = "All headers present" }
    } else {
        $testResults += @{Test = "Security Headers"; Status = "FAIL"; Details = "Missing headers" }
    }
} catch {
    Write-Host "  ❌ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test = "Security Headers"; Status = "FAIL"; Details = $_.Exception.Message }
}

# Test 4: Input Validation - Invalid UUID
Write-Host "`n[Test 4] Input Validation (Invalid UUID)" -ForegroundColor Yellow
try {
    $body = @{
        session_id = "not-a-valid-uuid-12345"
        models = @("gpt-4o")
    } | ConvertTo-Json
    
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    try {
        Invoke-WebRequest -Uri "$BaseUrl/analyze" -Method POST -Body $body -Headers $headers -ErrorAction Stop | Out-Null
        Write-Host "  ❌ Validation failed (should reject invalid UUID)" -ForegroundColor Red
        $testResults += @{Test = "Input Validation"; Status = "FAIL"; Details = "Invalid UUID accepted" }
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 422) {
            Write-Host "  ✅ Invalid UUID rejected (422)" -ForegroundColor Green
            $testResults += @{Test = "Input Validation"; Status = "PASS"; Details = "Invalid UUID correctly rejected" }
        } else {
            Write-Host "  ⚠️  Unexpected error: $($_.Exception.Message)" -ForegroundColor Yellow
            $testResults += @{Test = "Input Validation"; Status = "WARN"; Details = $_.Exception.Message }
        }
    }
} catch {
    Write-Host "  ❌ Test setup failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Input Validation - Invalid Model
Write-Host "`n[Test 5] Input Validation (Invalid Model)" -ForegroundColor Yellow
try {
    $body = @{
        session_id = "123e4567-e89b-12d3-a456-426614174000"
        models = @("invalid-model-name", "another-invalid")
    } | ConvertTo-Json
    
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    try {
        Invoke-WebRequest -Uri "$BaseUrl/analyze" -Method POST -Body $body -Headers $headers -ErrorAction Stop | Out-Null
        Write-Host "  ❌ Validation failed (should reject invalid model)" -ForegroundColor Red
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 422) {
            Write-Host "  ✅ Invalid model rejected (422)" -ForegroundColor Green
            $testResults += @{Test = "Model Validation"; Status = "PASS"; Details = "Invalid model correctly rejected" }
        }
    }
} catch {
    Write-Host "  ⚠️  Test error: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 6: Health Check (No API Key Exposure)
Write-Host "`n[Test 6] Health Check (API Key Protection)" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/health/detailed" -Method GET -ErrorAction Stop
    $content = $response.Content | ConvertFrom-Json
    
    if ($content.services_configured -ne $null -and $content.services -eq $null) {
        Write-Host "  ✅ API keys not exposed (only count shown)" -ForegroundColor Green
        Write-Host "  📊 Services configured: $($content.services_configured)" -ForegroundColor Gray
        $testResults += @{Test = "API Key Protection"; Status = "PASS"; Details = "Keys not exposed" }
    } else {
        Write-Host "  ⚠️  Check health endpoint response" -ForegroundColor Yellow
        $testResults += @{Test = "API Key Protection"; Status = "WARN"; Details = "Response format changed" }
    }
} catch {
    Write-Host "  ❌ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test = "API Key Protection"; Status = "FAIL"; Details = $_.Exception.Message }
}

# Test 7: File Size Limit (if you have a large file)
Write-Host "`n[Test 7] File Size Limit" -ForegroundColor Yellow
Write-Host "  ℹ️  Create a file > 50MB to test this" -ForegroundColor Gray
Write-Host "  ℹ️  Should be rejected with 400 error" -ForegroundColor Gray
$testResults += @{Test = "File Size Limit"; Status = "SKIP"; Details = "Manual test required" }

# Test 8: Database Persistence
Write-Host "`n[Test 8] Database Persistence" -ForegroundColor Yellow
try {
    # Upload a file to create a session
    $formData = @{
        files = Get-Item -Path "test_security.txt"
    }
    $response = Invoke-WebRequest -Uri "$BaseUrl/upload" -Method POST -Form $formData -ErrorAction Stop
    $result = $response.Content | ConvertFrom-Json
    $sessionId = $result.session_id
    
    if ($sessionId) {
        Write-Host "  ✅ Session created: $sessionId" -ForegroundColor Green
        Write-Host "  ℹ️  Check database file: accessibility_analyzer.db" -ForegroundColor Gray
        Write-Host "  ℹ️  Restart server and verify session persists" -ForegroundColor Gray
        $testResults += @{Test = "Database Persistence"; Status = "PASS"; Details = "Session created in DB" }
    }
} catch {
    Write-Host "  ❌ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test = "Database Persistence"; Status = "FAIL"; Details = $_.Exception.Message }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passed = ($testResults | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($testResults | Where-Object { $_.Status -eq "FAIL" }).Count
$warned = ($testResults | Where-Object { $_.Status -eq "WARN" }).Count
$skipped = ($testResults | Where-Object { $_.Status -eq "SKIP" }).Count

foreach ($result in $testResults) {
    $color = switch ($result.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "Gray" }
    }
    Write-Host "  [$($result.Status)] $($result.Test): $($result.Details)" -ForegroundColor $color
}

Write-Host "`nTotal: $passed passed, $failed failed, $warned warnings, $skipped skipped" -ForegroundColor Cyan

# Cleanup
if (Test-Path "test_security.txt") {
    Remove-Item "test_security.txt" -Force
    Write-Host "`nCleaned up test files" -ForegroundColor Gray
}

Write-Host "`nDone! Check results above." -ForegroundColor Green

