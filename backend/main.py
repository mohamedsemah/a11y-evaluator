from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Request
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

# Security and configuration imports
from config import get_settings
from security import sanitize_filename, validate_zip_path
from middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from database import (
    init_db, get_db, create_session, get_session, 
    update_session, delete_expired_sessions, session_to_dict
)
from validators import (
    AnalysisRequest, PreviewRemediationRequest, 
    ApplyRemediationRequest, RollbackRequest
)
from auth import get_current_user

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get settings
settings = get_settings()

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


app = FastAPI(
    title="Infotainment Accessibility Analyzer", 
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add security headers middleware (first, so it applies to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# CORS configuration with environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Specific methods only
    allow_headers=["Content-Type", "Authorization"],  # Specific headers only
)

# Initialize database
init_db()

# Initialize enhanced remediation service
enhanced_remediation = EnhancedRemediationService()


def sync_session_to_db(session_id: str, session_dict: Dict[str, Any]) -> bool:
    """
    Helper function to sync session dictionary changes back to database
    """
    try:
        updates = {
            "analysis_results": session_dict.get("analysis_results", {}),
            "remediation_results": session_dict.get("remediation_results", {}),
            "remediations": session_dict.get("remediations", {})
        }
        return update_session(session_id, updates)
    except Exception as e:
        logger.error(f"Failed to sync session to database: {str(e)}")
        return False

# Legacy RemediationRequest for backward compatibility
class RemediationRequest(BaseModel):
    session_id: str
    issue_id: str
    model: str
    file_path: str


@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = Depends(get_current_user)
):
    """
    Handle file uploads - supports individual files or ZIP archives
    SECURITY: Includes path traversal protection, file size limits, and ZIP slip protection
    """
    # Validate number of files
    if len(files) > settings.MAX_FILES_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {settings.MAX_FILES_PER_SESSION} files per session allowed."
        )
    
    session_id = str(uuid.uuid4())
    session_dir = Path(settings.TEMP_SESSIONS_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = []
    total_size = 0
    logger.info(f"Starting file upload for session: {session_id}")

    try:
        for file in files:
            # Validate filename and sanitize to prevent path traversal
            if not file.filename:
                logger.warning("Skipping file with no filename")
                continue
            
            try:
                safe_filename = sanitize_filename(file.filename)
            except ValueError as e:
                logger.error(f"Invalid filename: {file.filename} - {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid filename: {str(e)}")
            
            logger.info(f"Processing uploaded file: {safe_filename} (original: {file.filename})")
            file_path = session_dir / safe_filename

            # Read file content with size validation
            content = await file.read()
            file_size = len(content)
            
            # Validate individual file size
            if file_size > settings.max_file_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{safe_filename}' exceeds maximum size of {settings.MAX_FILE_SIZE / (1024*1024):.1f} MB"
                )
            
            # Check total size limit
            total_size += file_size
            if total_size > settings.max_total_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Total upload size exceeds maximum of {settings.MAX_TOTAL_SIZE / (1024*1024):.1f} MB"
                )

            # Save uploaded file
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            logger.info(f"Saved file: {file_path} ({file_size} bytes)")

            # If it's a ZIP file, extract it with ZIP slip protection
            if safe_filename.lower().endswith('.zip'):
                logger.info(f"Extracting ZIP file: {safe_filename}")
                extract_dir = session_dir / "extracted"
                extract_dir.mkdir(exist_ok=True)

                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        # SECURITY: Validate all paths before extraction to prevent ZipSlip
                        for member in zip_ref.namelist():
                            if not validate_zip_path(member, extract_dir):
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Invalid path in ZIP file: {member}. Path traversal detected."
                                )
                        
                        # Safe extraction after validation
                        zip_ref.extractall(extract_dir)

                    # Collect all extracted files
                    for root, dirs, files_in_dir in os.walk(extract_dir):
                        for f in files_in_dir:
                            full_path = Path(root) / f
                            
                            # Ensure path is still within extract_dir (double-check)
                            try:
                                relative_path = full_path.relative_to(extract_dir)
                            except ValueError:
                                logger.warning(f"Skipping file outside extract directory: {full_path}")
                                continue

                            if CodeProcessor.is_supported_file(full_path):
                                file_stat = full_path.stat()
                                uploaded_files.append({
                                    "name": str(relative_path),
                                    "path": str(full_path),
                                    "size": file_stat.st_size,
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
                        "name": safe_filename,
                        "path": str(file_path),
                        "size": file_size,
                        "type": file.content_type or "text/plain"
                    })
                    logger.info(f"Added supported file: {safe_filename}")
                else:
                    logger.warning(f"Unsupported file type: {safe_filename}")
                    # Remove unsupported file
                    if file_path.exists():
                        os.remove(file_path)

        # Validate we have at least one file
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="No valid files uploaded")

        # Store session data in database instead of memory
        try:
            db_session = create_session(session_id, uploaded_files, user_id=user_id)
            logger.info(f"Upload completed for session {session_id}: {len(uploaded_files)} files, {total_size} bytes")
        except Exception as e:
            logger.error(f"Failed to create database session: {str(e)}")
            # Cleanup on error
            if session_dir.exists():
                shutil.rmtree(session_dir)
            raise HTTPException(status_code=500, detail="Failed to create session")

        return {
            "session_id": session_id,
            "files": uploaded_files,
            "total_files": len(uploaded_files),
            "total_size": total_size
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Upload failed for session {session_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Cleanup on error
        if session_dir.exists():
            shutil.rmtree(session_dir)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/analyze")
async def analyze_accessibility(
    request: AnalysisRequest,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Perform accessibility analysis using specified LLM models - Detection Only"""
    logger.info(f"=== STARTING DETECTION ANALYSIS ===")
    logger.info(f"Session ID: {request.session_id}")
    logger.info(f"Models: {request.models}")

    # Get session from database
    db_session = get_session(request.session_id)
    if not db_session:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict for compatibility
    session = session_to_dict(db_session)
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

        # Store results in database
        update_session(request.session_id, {"analysis_results": results})

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
    db_session = get_session(session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_to_dict(db_session)

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
async def preview_remediation(
    request: PreviewRemediationRequest,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Preview the proposed remediation without applying it"""
    logger.info(f"Generating remediation preview for issue {request.issue_id} with model {request.model}")

    # Get session from database
    db_session = get_session(request.session_id)
    if not db_session:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict and create temporary sessions dict for compatibility
    session_dict = session_to_dict(db_session)
    analysis_sessions_temp = {request.session_id: session_dict}

    try:
        preview_result = await enhanced_remediation.preview_remediation(
            request.session_id, request.issue_id, request.model, analysis_sessions_temp
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
async def apply_remediation(
    request: ApplyRemediationRequest,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Apply the remediation after validation"""
    logger.info(f"Applying remediation for issue {request.issue_id} with model {request.model}")

    # Get session from database
    db_session = get_session(request.session_id)
    if not db_session:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict and create temporary sessions dict for compatibility
    session_dict = session_to_dict(db_session)
    analysis_sessions_temp = {request.session_id: session_dict}

    try:
        apply_result = await enhanced_remediation.apply_remediation(
            request.session_id, request.issue_id, request.model,
            analysis_sessions_temp, request.force_apply
        )
        
        # Update session in database if remediation was applied
        if apply_result.get("success"):
            # Sync session changes back to database
            sync_session_to_db(request.session_id, analysis_sessions_temp.get(request.session_id, {}))

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
async def rollback_remediation(
    request: RollbackRequest,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Rollback a previously applied remediation"""
    logger.info(f"Rolling back remediation for issue {request.issue_id}")

    # Get session from database
    db_session = get_session(request.session_id)
    if not db_session:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict and create temporary sessions dict for compatibility
    session_dict = session_to_dict(db_session)
    analysis_sessions_temp = {request.session_id: session_dict}

    try:
        rollback_result = await enhanced_remediation.rollback_remediation(
            request.session_id, request.issue_id, analysis_sessions_temp
        )
        
        # Update session in database after rollback
        if rollback_result.get("success"):
            # Sync session changes back to database
            sync_session_to_db(request.session_id, analysis_sessions_temp.get(request.session_id, {}))

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

    # Get session from database
    db_session = get_session(request.session_id)
    if not db_session:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict and create temporary sessions dict for compatibility
    session_dict = session_to_dict(db_session)
    analysis_sessions_temp = {request.session_id: session_dict}

    try:
        # Use enhanced remediation but apply directly (for backward compatibility)
        apply_result = await enhanced_remediation.apply_remediation(
            request.session_id, request.issue_id, request.model,
            analysis_sessions_temp, force_apply=True  # Force apply for legacy endpoint
        )
        
        # Update session in database
        if apply_result.get("success"):
            # Sync session changes back to database
            sync_session_to_db(request.session_id, analysis_sessions_temp.get(request.session_id, {}))

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
async def get_session_endpoint(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Get session details and analysis results"""
    db_session = get_session(session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_to_dict(db_session)


@app.get("/file/{session_id}/{file_path:path}")
async def get_file_content(
    session_id: str,
    file_path: str,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Get content of a specific file"""
    # Validate session_id format
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    # Validate file_path to prevent path traversal
    try:
        safe_file_path = sanitize_filename(file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    db_session = get_session(session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_to_dict(db_session)

    # Find file by path (use sanitized path)
    target_file = None
    for file_info in session["files"]:
        if file_info["name"] == safe_file_path:
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
async def download_fixed_code(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Download ZIP file with all fixed code"""
    # Validate session_id format
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    db_session = get_session(session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_to_dict(db_session)

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
async def download_report(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Download PDF report of analysis and fixes"""
    # Validate session_id format
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    db_session = get_session(session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_to_dict(db_session)
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
    """Detailed health check - SECURITY: Does not expose API key details"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services_configured": 0,
        "database": "unknown"
    }

    try:
        # Check API keys without exposing them
        services = {
            "openai": settings.OPENAI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "replicate": settings.REPLICATE_API_TOKEN
        }

        configured_count = sum(1 for key in services.values() if key)
        health_status["services_configured"] = configured_count

        # Check if at least one service is available (without exposing which ones)
        if configured_count == 0:
            health_status["status"] = "degraded"
            health_status["message"] = "No LLM services configured"
        elif configured_count < len(services):
            health_status["status"] = "degraded"
            health_status["message"] = f"{configured_count}/{len(services)} LLM services configured"
        
        # Check database connectivity
        try:
            test_session = get_session("test")  # This will fail but test connection
            health_status["database"] = "connected"
        except Exception:
            # Try to create a test session to verify DB works
            try:
                from database import SessionLocal
                db = SessionLocal()
                db.close()
                health_status["database"] = "connected"
            except Exception as db_error:
                health_status["database"] = "error"
                health_status["status"] = "degraded"
                logger.warning(f"Database check failed: {str(db_error)}")

    except Exception as e:
        health_status["status"] = "error"
        health_status["error"] = "Health check failed"
        logger.error(f"Health check error: {str(e)}")

    return health_status


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    # Create temp directories
    Path(settings.TEMP_SESSIONS_DIR).mkdir(exist_ok=True)
    
    # Initialize database
    init_db()
    
    # Clean up expired sessions
    deleted_count = delete_expired_sessions()
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} expired sessions on startup")
    
    # Log configuration
    api_key_count = sum(1 for k in [
        settings.OPENAI_API_KEY, 
        settings.ANTHROPIC_API_KEY, 
        settings.DEEPSEEK_API_KEY,
        settings.REPLICATE_API_TOKEN
    ] if k)
    logger.info(f"Starting Infotainment Accessibility Analyzer")
    logger.info(f"API Keys configured: {api_key_count}/4")
    logger.info(f"Rate limiting: {'enabled' if settings.RATE_LIMIT_ENABLED else 'disabled'}")
    logger.info(f"Max file size: {settings.MAX_FILE_SIZE / (1024*1024):.1f} MB")
    logger.info(f"Max total size: {settings.MAX_TOTAL_SIZE / (1024*1024):.1f} MB")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Infotainment Accessibility Analyzer")
    uvicorn.run(app, host="0.0.0.0", port=8000)