from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import zipfile
import tempfile
import shutil
import json
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from datetime import datetime
import mimetypes
from pydantic import BaseModel
import logging
import traceback
import sys

from llm_clients import LLMClient
from wcag_analyzer import WCAGAnalyzer
from code_processor import CodeProcessor
from report_generator import ReportGenerator
from enhanced_remediation import EnhancedRemediationService

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix Unicode encoding issues on Windows
if sys.platform.startswith('win'):
    # Set environment variable to force UTF-8 encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    # Reconfigure stdout and stderr to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')


# Configure detailed logging with UTF-8 encoding
class UTF8FileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        super().__init__(filename, mode, encoding, delay)


class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)

    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Replace problematic Unicode characters with safe alternatives
            msg = self.format(record)
            safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
            # Replace the Unicode checkmark with a simple [OK]
            safe_msg = safe_msg.replace('�', '[OK]')
            print(safe_msg)


# Setup logging with UTF-8 support
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# File handler with UTF-8 encoding
file_handler = UTF8FileHandler('accessibility_analyzer.log')
file_handler.setFormatter(log_formatter)

# Console handler with Unicode fallback
console_handler = UTF8StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger(__name__)


# Safe logging functions that replace Unicode with ASCII alternatives
def log_success(message):
    """Log success message with safe Unicode handling"""
    safe_message = message.replace('✅', '[SUCCESS]')
    logger.info(safe_message)


def log_error(message):
    """Log error message with safe Unicode handling"""
    safe_message = message.replace('❌', '[ERROR]')
    logger.error(safe_message)


def log_warning(message):
    """Log warning message with safe Unicode handling"""
    safe_message = message.replace('⚠️', '[WARNING]')
    logger.warning(safe_message)


app = FastAPI(title="Infotainment Accessibility Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for analysis sessions
analysis_sessions = {}

# Initialize enhanced remediation service
enhanced_remediation = EnhancedRemediationService()


class AnalysisRequest(BaseModel):
    session_id: str
    models: List[str]


class RemediationRequest(BaseModel):
    session_id: str
    issue_id: str
    model: str
    file_path: str


class PreviewRemediationRequest(BaseModel):
    session_id: str
    issue_id: str
    model: str


class ApplyRemediationRequest(BaseModel):
    session_id: str
    issue_id: str
    model: str
    force_apply: bool = False


class RollbackRequest(BaseModel):
    session_id: str
    issue_id: str


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Handle file uploads - supports individual files or ZIP archives"""
    session_id = str(uuid.uuid4())
    session_dir = Path(f"temp_sessions/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = []
    logger.info(f"Starting file upload for session: {session_id}")

    try:
        for file in files:
            logger.info(f"Processing uploaded file: {file.filename}")
            file_path = session_dir / file.filename

            # Save uploaded file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            logger.info(f"Saved file: {file_path} ({len(content)} bytes)")

            # If it's a ZIP file, extract it
            if file.filename.endswith('.zip'):
                logger.info(f"Extracting ZIP file: {file.filename}")
                extract_dir = session_dir / "extracted"
                extract_dir.mkdir(exist_ok=True)

                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)

                    # Collect all extracted files
                    for root, dirs, files in os.walk(extract_dir):
                        for f in files:
                            full_path = Path(root) / f
                            relative_path = full_path.relative_to(extract_dir)

                            if CodeProcessor.is_supported_file(full_path):
                                uploaded_files.append({
                                    "name": str(relative_path),
                                    "path": str(full_path),
                                    "size": full_path.stat().st_size,
                                    "type": mimetypes.guess_type(str(full_path))[0] or "text/plain"
                                })
                                logger.info(f"Added extracted file: {relative_path}")

                    # Remove the original ZIP file
                    os.remove(file_path)
                    logger.info(f"ZIP extraction completed, found {len(uploaded_files)} supported files")

                except zipfile.BadZipFile as e:
                    logger.error(f"Bad ZIP file: {e}")
                    raise HTTPException(status_code=400, detail=f"Invalid ZIP file: {str(e)}")

            else:
                if CodeProcessor.is_supported_file(file_path):
                    uploaded_files.append({
                        "name": file.filename,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "type": file.content_type or "text/plain"
                    })
                    logger.info(f"Added supported file: {file.filename}")
                else:
                    logger.warning(f"Unsupported file type: {file.filename}")

        # Store session data
        analysis_sessions[session_id] = {
            "id": session_id,
            "files": uploaded_files,
            "created_at": datetime.now().isoformat(),
            "analysis_results": {},
            "remediation_results": {}
        }

        logger.info(f"Upload completed for session {session_id}: {len(uploaded_files)} files")

        return {
            "session_id": session_id,
            "files": uploaded_files,
            "total_files": len(uploaded_files)
        }

    except Exception as e:
        logger.error(f"Upload failed for session {session_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Cleanup on error
        if session_dir.exists():
            shutil.rmtree(session_dir)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/analyze")
async def analyze_accessibility(request: AnalysisRequest):
    """Perform accessibility analysis using specified LLM models - Detection Only"""
    logger.info(f"=== STARTING DETECTION ANALYSIS ===")
    logger.info(f"Session ID: {request.session_id}")
    logger.info(f"Models: {request.models}")

    if request.session_id not in analysis_sessions:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    session = analysis_sessions[request.session_id]
    logger.info(f"Session found with {len(session.get('files', []))} files")

    try:
        # Check if any files to analyze
        if not session.get("files"):
            logger.error("No files found in session")
            raise HTTPException(status_code=400, detail="No files found in session")

        # Initialize clients with detailed error checking
        logger.info("Initializing LLM client...")
        try:
            llm_client = LLMClient()
            log_success("LLM client initialized successfully")
        except Exception as e:
            log_error(f"LLM client initialization failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"LLM client initialization failed: {str(e)}")

        logger.info("Initializing WCAG analyzer...")
        try:
            wcag_analyzer = WCAGAnalyzer()
            log_success("WCAG analyzer initialized successfully")
        except Exception as e:
            log_error(f"WCAG analyzer initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"WCAG analyzer initialization failed: {str(e)}")

        results = {}

        for model_idx, model in enumerate(request.models):
            logger.info(f"=== PROCESSING MODEL {model_idx + 1}/{len(request.models)}: {model} ===")
            model_results = []

            for file_idx, file_info in enumerate(session["files"]):
                logger.info(f"--- Processing file {file_idx + 1}/{len(session['files'])}: {file_info['name']} ---")
                file_path = Path(file_info["path"])

                if not file_path.exists():
                    logger.error(f"File not found: {file_path}")
                    model_results.append({
                        "file_info": file_info,
                        "error": f"File not found: {file_path}",
                        "total_issues": 0,
                        "issues": []
                    })
                    continue

                try:
                    # Read file content
                    logger.info(f"Reading file: {file_path}")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        log_success(f"File read successfully: {len(content)} characters, {len(content.split())} lines")
                    except Exception as e:
                        log_error(f"Failed to read file {file_path}: {str(e)}")
                        model_results.append({
                            "file_info": file_info,
                            "error": f"Failed to read file: {str(e)}",
                            "total_issues": 0,
                            "issues": []
                        })
                        continue

                    # Analyze with LLM for detection only
                    logger.info(f"Starting LLM detection analysis with {model}...")
                    try:
                        logger.info(f"Calling detect_accessibility_issues...")
                        analysis_result = await llm_client.detect_accessibility_issues(
                            content, file_info["name"], model
                        )

                        log_success("LLM detection analysis completed")
                        logger.info(f"Result keys: {list(analysis_result.keys())}")

                        # Log the result structure for debugging
                        if analysis_result.get("error"):
                            log_error(f"LLM returned error: {analysis_result['error']}")
                        else:
                            issues_count = len(analysis_result.get("issues", []))
                            logger.info(f"Found {issues_count} accessibility issues")

                    except Exception as e:
                        log_error(f"LLM analysis failed: {str(e)}")
                        logger.error(f"Exception type: {type(e).__name__}")
                        logger.error(f"Traceback: {traceback.format_exc()}")

                        analysis_result = {
                            "error": f"LLM analysis failed: {str(e)}",
                            "total_issues": 0,
                            "issues": [],
                            "file_info": {"filename": file_info["name"], "total_lines": len(content.split('\n')),
                                          "file_type": "unknown"}
                        }

                    # Process and enhance results
                    logger.info("Processing results with WCAG analyzer...")
                    try:
                        processed_result = wcag_analyzer.process_llm_result(
                            analysis_result, file_info, content
                        )
                        log_success("WCAG processing completed")
                    except Exception as e:
                        log_error(f"WCAG processing failed: {str(e)}")
                        logger.error(f"Traceback: {traceback.format_exc()}")

                        # Fallback to basic result structure
                        processed_result = {
                            "file_info": file_info,
                            "total_issues": len(analysis_result.get("issues", [])),
                            "issues": analysis_result.get("issues", []),
                            "error": f"WCAG processing failed: {str(e)}",
                            "llm_result": analysis_result
                        }

                    model_results.append(processed_result)
                    log_success(f"File processing completed for {file_info['name']}")

                except Exception as e:
                    log_error(f"Unexpected error processing file {file_info['name']}: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    model_results.append({
                        "file_info": file_info,
                        "error": f"Unexpected error: {str(e)}",
                        "total_issues": 0,
                        "issues": []
                    })

            results[model] = model_results
            log_success(f"Model {model} processing completed: {len(model_results)} files processed")

        # Store results in analysis_results (detection only)
        session["analysis_results"] = results

        logger.info(f"=== DETECTION ANALYSIS COMPLETED SUCCESSFULLY ===")
        logger.info(f"Session: {request.session_id}")
        logger.info(f"Models processed: {len(results)}")

        return {
            "session_id": request.session_id,
            "results": results,
            "analysis_type": "detection"
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        log_error(f"ANALYSIS FAILED: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/debug/session/{session_id}")
async def debug_session_structure(session_id: str):
    """Debug endpoint to inspect session structure"""
    if session_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = analysis_sessions[session_id]

    debug_info = {
        "session_keys": list(session.keys()),
        "analysis_results_structure": {},
        "issue_ids": [],
        "files": []
    }

    # Analyze analysis_results structure
    analysis_results = session.get('analysis_results', {})
    for model, model_results in analysis_results.items():
        debug_info["analysis_results_structure"][model] = {
            "type": str(type(model_results)),
            "length": len(model_results) if isinstance(model_results, list) else "N/A",
            "sample_keys": []
        }

        if isinstance(model_results, list) and model_results:
            first_result = model_results[0]
            debug_info["analysis_results_structure"][model]["sample_keys"] = list(first_result.keys()) if isinstance(
                first_result, dict) else []

            # Extract issue IDs
            for file_result in model_results:
                if isinstance(file_result, dict):
                    issues = file_result.get('issues', [])
                    for issue in issues:
                        if isinstance(issue, dict):
                            issue_id = issue.get('issue_id', 'NO_ID')
                            debug_info["issue_ids"].append({
                                "model": model,
                                "file": file_result.get('file_info', {}).get('name', 'Unknown'),
                                "issue_id": issue_id,
                                "wcag_guideline": issue.get('wcag_guideline', 'No guideline')
                            })

    # Analyze files structure
    files = session.get('files', [])
    for file_info in files:
        debug_info["files"].append({
            "name": file_info.get('name', 'Unknown'),
            "path": file_info.get('path', 'No path'),
            "size": file_info.get('size', 0)
        })

    return debug_info


@app.post("/remediate/preview")
async def preview_remediation(request: PreviewRemediationRequest):
    """Preview the proposed remediation without applying it"""
    logger.info(f"Generating remediation preview for issue {request.issue_id} with model {request.model}")

    if request.session_id not in analysis_sessions:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        preview_result = await enhanced_remediation.preview_remediation(
            request.session_id, request.issue_id, request.model, analysis_sessions
        )

        if preview_result.get("success"):
            log_success("Remediation preview generated successfully")
            return {
                "success": True,
                "preview": True,
                "issue_id": request.issue_id,
                "model": request.model,
                **preview_result
            }
        else:
            log_error(f"Preview generation failed: {preview_result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Preview generation failed: {preview_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        log_error(f"Preview generation failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@app.post("/remediate/apply")
async def apply_remediation(request: ApplyRemediationRequest):
    """Apply the remediation after validation"""
    logger.info(f"Applying remediation for issue {request.issue_id} with model {request.model}")

    if request.session_id not in analysis_sessions:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        apply_result = await enhanced_remediation.apply_remediation(
            request.session_id, request.issue_id, request.model,
            analysis_sessions, request.force_apply
        )

        if apply_result.get("success"):
            log_success("Remediation applied successfully")
            return apply_result
        else:
            log_error(f"Remediation application failed: {apply_result.get('error', 'Unknown error')}")

            # If it's a quality score issue, return a different status code
            if "quality score" in apply_result.get("error", "").lower():
                return JSONResponse(
                    status_code=422,  # Unprocessable Entity
                    content=apply_result
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Remediation application failed: {apply_result.get('error', 'Unknown error')}"
                )

    except Exception as e:
        log_error(f"Remediation application failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Remediation application failed: {str(e)}")


@app.post("/remediate/rollback")
async def rollback_remediation(request: RollbackRequest):
    """Rollback a previously applied remediation"""
    logger.info(f"Rolling back remediation for issue {request.issue_id}")

    if request.session_id not in analysis_sessions:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        rollback_result = await enhanced_remediation.rollback_remediation(
            request.session_id, request.issue_id, analysis_sessions
        )

        if rollback_result.get("success"):
            log_success("Remediation rolled back successfully")
            return rollback_result
        else:
            log_error(f"Rollback failed: {rollback_result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=400,
                detail=f"Rollback failed: {rollback_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        log_error(f"Rollback failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


@app.post("/remediate")
async def remediate_issue(request: RemediationRequest):
    """Legacy remediation endpoint - now uses enhanced remediation"""
    logger.info(f"Legacy remediation request for issue {request.issue_id} with model {request.model}")

    if request.session_id not in analysis_sessions:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Use enhanced remediation but apply directly (for backward compatibility)
        apply_result = await enhanced_remediation.apply_remediation(
            request.session_id, request.issue_id, request.model,
            analysis_sessions, force_apply=True  # Force apply for legacy endpoint
        )

        if apply_result.get("success"):
            log_success("Legacy remediation completed")
            return {
                "issue_id": request.issue_id,
                "model": request.model,
                "fixed_code": apply_result.get("validation", {}).get("fixed_code", ""),
                "changes": apply_result.get("changes_applied", [])
            }
        else:
            log_error(f"Legacy remediation failed: {apply_result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Remediation failed: {apply_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        log_error(f"Legacy remediation failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Remediation failed: {str(e)}")


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session details and analysis results"""
    if session_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return analysis_sessions[session_id]


@app.get("/file/{session_id}/{file_path:path}")
async def get_file_content(session_id: str, file_path: str):
    """Get content of a specific file"""
    if session_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = analysis_sessions[session_id]

    # Find file by path
    target_file = None
    for file_info in session["files"]:
        if file_info["name"] == file_path:
            target_file = file_info
            break

    if not target_file:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(target_file["path"], 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        return {
            "file_path": file_path,
            "content": content,
            "size": target_file["size"],
            "type": target_file["type"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@app.get("/download/{session_id}/fixed-code")
async def download_fixed_code(session_id: str):
    """Download ZIP file with all fixed code"""
    if session_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = analysis_sessions[session_id]

    # Create ZIP with fixed code
    zip_path = Path(f"temp_sessions/{session_id}_fixed.zip")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_info in session["files"]:
            original_path = Path(file_info["path"])

            # Check if file has been fixed
            if "remediations" in session:
                # Use fixed version if available
                with open(original_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Apply all fixes for this file
                for issue_id, remediation in session["remediations"].items():
                    if remediation.get("applied") and file_info["name"] in remediation["result"].get("file_path", ""):
                        content = remediation["result"]["fixed_code"]

                zipf.writestr(f"fixed/{file_info['name']}", content)
            else:
                # Include original file
                zipf.write(original_path, file_info["name"])

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"fixed_code_{session_id}.zip"
    )


@app.get("/download/{session_id}/report")
async def download_report(session_id: str):
    """Download PDF report of analysis and fixes"""
    if session_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = analysis_sessions[session_id]
    report_generator = ReportGenerator()

    try:
        pdf_path = await report_generator.generate_pdf_report(session)

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"accessibility_report_{session_id}.pdf"
        )
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including API key validation"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    try:
        # Check API keys
        services = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY"),
            "replicate": os.getenv("REPLICATE_API_TOKEN")
        }

        for service, api_key in services.items():
            if api_key:
                health_status["services"][service] = "configured"
            else:
                health_status["services"][service] = "missing_api_key"

        # Check if at least one service is available
        if not any(key for key in services.values() if key):
            health_status["status"] = "degraded"
            health_status["message"] = "No API keys configured"

    except Exception as e:
        health_status["status"] = "error"
        health_status["error"] = str(e)

    return health_status


if __name__ == "__main__":
    import uvicorn

    # Create temp directories
    Path("temp_sessions").mkdir(exist_ok=True)

    logger.info("Starting Infotainment Accessibility Analyzer")
    api_key_count = len([k for k in
                         [os.getenv('OPENAI_API_KEY'), os.getenv('ANTHROPIC_API_KEY'), os.getenv('DEEPSEEK_API_KEY'),
                          os.getenv('REPLICATE_API_TOKEN')] if k])
    logger.info(f"API Keys configured: {api_key_count}/4")

    uvicorn.run(app, host="0.0.0.0", port=8000)