from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import json
import zipfile
import tempfile
import shutil
import asyncio
from typing import List, Optional, Dict
import uuid
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from dotenv import load_dotenv
import re

load_dotenv()

from models import (
    Base, User, Analysis, Issue, LLMComparison, AccessibilityStandard,
    WCAGSuccessCriteria, InfotainmentContext, AnalysisSession, get_db,
    create_infotainment_analysis, create_infotainment_issue, get_infotainment_analysis_summary
)
from llm_analyzer import InfotainmentLLMAnalyzer

# Initialize FastAPI
app = FastAPI(title="Infotainment Accessibility Analyzer")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecret123")
ALGORITHM = "HS256"

# Initialize database
from models import engine

Base.metadata.create_all(bind=engine)

# Initialize Infotainment LLM analyzer
llm_analyzer = InfotainmentLLMAnalyzer()

# Security
security = HTTPBearer()

# File filtering configuration
EXCLUDED_DIRECTORIES = {
    'node_modules', '.git', '.svn', '.hg', '__pycache__', '.pytest_cache',
    'build', 'dist', 'out', '.next', '.nuxt', 'target', 'bin', 'obj',
    'coverage', '.nyc_output', 'logs', 'log', 'tmp', 'temp', '.cache',
    '.vscode', '.idea', '.vs', 'bower_components', 'vendor', 'packages',
    '.sass-cache', '.gradle', '.m2', 'Pods', 'DerivedData'
}

EXCLUDED_FILES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.gitkeep', '.npmignore',
    'package-lock.json', 'yarn.lock', 'composer.lock', 'Gemfile.lock',
    '.env', '.env.local', '.env.development', '.env.production'
}

EXCLUDED_EXTENSIONS = {
    # Binary files
    '.exe', '.dll', '.so', '.dylib', '.bin', '.obj', '.o', '.a', '.lib',
    # Images (unless they have accessibility concerns)
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff', '.webp',
    # Videos and audio
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mp3', '.wav', '.ogg', '.flac',
    # Archives
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # Fonts
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    # Compiled/minified files
    '.min.js', '.min.css', '.map',
    # Lock/log files
    '.lock', '.log', '.pid', '.tmp'
}

RELEVANT_EXTENSIONS = {
    # Web files
    '.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte',
    # React/JSX files
    '.mjs', '.cjs',
    # Automotive/embedded files
    '.qml', '.ui', '.xml', '.xaml',
    # Native mobile
    '.swift', '.kt', '.java', '.dart',
    # Configuration files that might affect accessibility
    '.json', '.yaml', '.yml', '.toml', '.ini', '.conf',
    # Style files
    '.scss', '.sass', '.less', '.styl',
    # Template files
    '.hbs', '.mustache', '.ejs', '.pug', '.jade',
    # Documentation that might contain accessibility info
    '.md', '.mdx', '.txt'
}

MAX_FILE_SIZE = 1024 * 1024  # 1MB per file
MAX_TOTAL_FILES = 1000  # Maximum files to process


def _should_exclude_path(path: str) -> bool:
    """Check if a file path should be excluded from analysis."""
    path_parts = path.split('/')

    # Check for excluded directories at any level
    for part in path_parts:
        if part.lower() in EXCLUDED_DIRECTORIES:
            return True

    # Check for excluded file names
    filename = os.path.basename(path)
    if filename in EXCLUDED_FILES:
        return True

    # Check for excluded extensions
    for ext in EXCLUDED_EXTENSIONS:
        if path.lower().endswith(ext):
            return True

    # Check if file is too large (might be a build artifact)
    return False


def _is_relevant_for_analysis(path: str, content_size: int) -> bool:
    """Check if a file is relevant for infotainment accessibility analysis."""

    # Skip if excluded
    if _should_exclude_path(path):
        return False

    # Skip if too large
    if content_size > MAX_FILE_SIZE:
        print(f"Skipping {path} - too large ({content_size} bytes)")
        return False

    filename = os.path.basename(path).lower()

    # Check for relevant extensions
    has_relevant_extension = any(path.lower().endswith(ext) for ext in RELEVANT_EXTENSIONS)

    # Check for infotainment-specific keywords in path/filename
    infotainment_keywords = [
        'hmi', 'dashboard', 'cluster', 'infotainment', 'vehicle', 'automotive',
        'carplay', 'androidauto', 'navigation', 'media', 'climate', 'settings',
        'radio', 'music', 'phone', 'contacts', 'maps', 'traffic', 'voice',
        'component', 'widget', 'screen', 'page', 'view', 'dialog', 'modal'
    ]

    has_relevant_keywords = any(keyword in path.lower() for keyword in infotainment_keywords)

    # Include if has relevant extension OR contains infotainment keywords
    return has_relevant_extension or has_relevant_keywords


def _analyze_zip_structure(zip_file_path: str) -> Dict:
    """Analyze ZIP structure and provide filtering recommendations."""
    structure = {
        'total_files': 0,
        'excluded_files': 0,
        'relevant_files': 0,
        'large_files': 0,
        'directories_found': set(),
        'extensions_found': set(),
        'sample_relevant_files': [],
        'excluded_reasons': {}
    }

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zf:
            for file_info in zf.filelist:
                if file_info.is_dir():
                    continue

                structure['total_files'] += 1

                # Analyze directory structure
                path_parts = file_info.filename.split('/')
                for part in path_parts[:-1]:  # Exclude filename
                    if part:
                        structure['directories_found'].add(part)

                # Analyze extensions
                if '.' in file_info.filename:
                    ext = '.' + file_info.filename.split('.')[-1].lower()
                    structure['extensions_found'].add(ext)

                # Check if file should be included
                if _should_exclude_path(file_info.filename):
                    structure['excluded_files'] += 1
                    # Track exclusion reasons
                    reason = 'unknown'
                    if any(dir_name in file_info.filename.lower() for dir_name in EXCLUDED_DIRECTORIES):
                        reason = 'excluded_directory'
                    elif any(file_info.filename.lower().endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                        reason = 'excluded_extension'
                    elif os.path.basename(file_info.filename) in EXCLUDED_FILES:
                        reason = 'excluded_filename'

                    structure['excluded_reasons'][reason] = structure['excluded_reasons'].get(reason, 0) + 1

                elif file_info.file_size > MAX_FILE_SIZE:
                    structure['large_files'] += 1
                elif _is_relevant_for_analysis(file_info.filename, file_info.file_size):
                    structure['relevant_files'] += 1
                    if len(structure['sample_relevant_files']) < 20:
                        structure['sample_relevant_files'].append({
                            'path': file_info.filename,
                            'size': file_info.file_size
                        })

    except Exception as e:
        print(f"Error analyzing ZIP structure: {e}")

    return structure


# Enhanced Authentication helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_with_validation(token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get current user with database validation to prevent foreign key errors"""
    user_id = token_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token - missing user ID")

    # Validate that user actually exists in database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found - please log in again"
        )

    return user_id


# Keep backward compatibility
def get_current_user(token_data: dict = Depends(verify_token)):
    return token_data.get("user_id")


# Enhanced request models for infotainment
from pydantic import BaseModel


class AuthRequest(BaseModel):
    email: str
    password: str


class RatingRequest(BaseModel):
    rating: int


class BatchFixRequest(BaseModel):
    issue_ids: List[str]


class InfotainmentAnalyzeRequest(BaseModel):
    llm_models: List[str]
    standards: List[str] = ["WCAG 2.2", "ISO15008", "NHTSA"]


# Fix application helper functions
def apply_code_fix(original_code: str, suggested_fix: str, line_number: int = None) -> str:
    """
    Apply a suggested fix to the original code.
    This is a simple implementation - in production, you might want more sophisticated parsing.
    """
    if not suggested_fix or not original_code:
        return original_code

    try:
        # If we have a line number, try to replace that specific line
        if line_number:
            lines = original_code.split('\n')
            if 0 <= line_number - 1 < len(lines):
                # Try to find the original line in the suggested fix and replace it
                # This is a simplified approach - real implementation might need AST parsing
                lines[line_number - 1] = suggested_fix.strip()
                return '\n'.join(lines)

        # If no line number or line replacement failed, try pattern replacement
        # Look for patterns in the suggested fix that might indicate what to replace
        fix_lines = suggested_fix.split('\n')

        # Simple heuristic: if suggested fix is short, try to replace similar patterns
        if len(fix_lines) <= 3 and len(suggested_fix) < 200:
            # Try to find and replace similar code patterns
            for fix_line in fix_lines:
                fix_line = fix_line.strip()
                if fix_line and not fix_line.startswith('//') and not fix_line.startswith('/*'):
                    # Try to find similar patterns and replace them
                    # This is basic - real implementation would need proper AST parsing
                    original_code = try_pattern_replacement(original_code, fix_line)

        return original_code

    except Exception as e:
        print(f"Error applying fix: {str(e)}")
        return original_code


def try_pattern_replacement(original_code: str, fix_line: str) -> str:
    """
    Try to intelligently replace code patterns.
    This is a simplified implementation.
    """
    try:
        # Remove common prefixes/suffixes that might differ
        fix_line_clean = fix_line.strip()

        # Try to find and replace common accessibility fixes
        accessibility_patterns = [
            # Alt text fixes
            (r'<img([^>]*?)>', lambda m: add_alt_if_missing(m.group(0), fix_line_clean)),
            # ARIA label fixes
            (r'<(button|input|a)([^>]*?)>', lambda m: add_aria_if_missing(m.group(0), fix_line_clean)),
            # Role fixes
            (r'<div([^>]*?)>', lambda m: add_role_if_missing(m.group(0), fix_line_clean)),
        ]

        modified_code = original_code
        for pattern, replacement in accessibility_patterns:
            if re.search(pattern, original_code, re.IGNORECASE):
                modified_code = re.sub(pattern, replacement, modified_code, flags=re.IGNORECASE)
                break

        return modified_code

    except Exception as e:
        print(f"Error in pattern replacement: {str(e)}")
        return original_code


def add_alt_if_missing(img_tag: str, fix_line: str) -> str:
    """Add alt attribute if missing from img tag"""
    if 'alt=' not in img_tag.lower():
        # Extract alt text from fix line if possible
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', fix_line, re.IGNORECASE)
        alt_text = alt_match.group(1) if alt_match else "Accessibility description"
        return img_tag.replace('>', f' alt="{alt_text}">')
    return img_tag


def add_aria_if_missing(tag: str, fix_line: str) -> str:
    """Add aria-label if missing from interactive elements"""
    if 'aria-label=' not in tag.lower() and 'aria-labelledby=' not in tag.lower():
        # Extract aria-label from fix line if possible
        aria_match = re.search(r'aria-label=["\']([^"\']*)["\']', fix_line, re.IGNORECASE)
        aria_text = aria_match.group(1) if aria_match else "Interactive element"
        return tag.replace('>', f' aria-label="{aria_text}">')
    return tag


def add_role_if_missing(tag: str, fix_line: str) -> str:
    """Add role attribute if suggested in fix"""
    if 'role=' in fix_line.lower() and 'role=' not in tag.lower():
        role_match = re.search(r'role=["\']([^"\']*)["\']', fix_line, re.IGNORECASE)
        if role_match:
            role_value = role_match.group(1)
            return tag.replace('>', f' role="{role_value}">')
    return tag


# Enhanced authentication endpoints with better error handling
@app.post("/api/register")
async def register(payload: AuthRequest, db: Session = Depends(get_db)):
    email = payload.email
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(email=email, password_hash=hashed.decode('utf-8'))

        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token({"user_id": str(user.id)})
        return {"token": token, "user_id": str(user.id)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/api/login")
async def login(payload: AuthRequest, db: Session = Depends(get_db)):
    email = payload.email
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"user_id": str(user.id)})
        return {"token": token, "user_id": str(user.id)}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")


# Enhanced file upload with intelligent filtering
@app.post("/api/upload")
async def upload_files(
        files: List[UploadFile] = File(...),
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp()

    try:
        file_contents = {}
        infotainment_file_count = 0
        total_files_processed = 0
        skipped_files = 0
        filtering_stats = {
            'excluded_directories': 0,
            'excluded_extensions': 0,
            'too_large': 0,
            'not_relevant': 0
        }

        for file in files:
            if file.size > 50 * 1024 * 1024:  # 50MB limit for individual files
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 50MB limit")

            content = await file.read()

            # Handle ZIP files with intelligent filtering
            if file.filename.endswith('.zip'):
                print(f"Processing ZIP file: {file.filename}")

                # Save ZIP temporarily for analysis
                zip_path = os.path.join(temp_dir, file.filename)
                with open(zip_path, 'wb') as f:
                    f.write(content)

                # Analyze ZIP structure first
                structure = _analyze_zip_structure(zip_path)
                print(
                    f"ZIP Analysis - Total files: {structure['total_files']}, Relevant: {structure['relevant_files']}, Excluded: {structure['excluded_files']}")

                # Warn if too many files
                if structure['total_files'] > MAX_TOTAL_FILES:
                    print(f"WARNING: ZIP contains {structure['total_files']} files. Processing only relevant ones.")

                with zipfile.ZipFile(zip_path) as zf:
                    processed_count = 0
                    for file_info in zf.filelist:
                        if file_info.is_dir():
                            continue

                        total_files_processed += 1

                        # Apply intelligent filtering
                        if _should_exclude_path(file_info.filename):
                            skipped_files += 1
                            # Track exclusion reason
                            if any(dir_name in file_info.filename.lower() for dir_name in EXCLUDED_DIRECTORIES):
                                filtering_stats['excluded_directories'] += 1
                            elif any(file_info.filename.lower().endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                                filtering_stats['excluded_extensions'] += 1
                            continue

                        if file_info.file_size > MAX_FILE_SIZE:
                            skipped_files += 1
                            filtering_stats['too_large'] += 1
                            continue

                        if not _is_relevant_for_analysis(file_info.filename, file_info.file_size):
                            skipped_files += 1
                            filtering_stats['not_relevant'] += 1
                            continue

                        # Limit total files processed
                        if processed_count >= MAX_TOTAL_FILES:
                            print(f"Reached maximum file limit ({MAX_TOTAL_FILES}). Stopping processing.")
                            break

                        try:
                            file_content = zf.read(file_info.filename).decode('utf-8', errors='ignore')
                            if len(file_content.strip()) > 0:  # Skip empty files
                                file_contents[file_info.filename] = file_content
                                processed_count += 1
                                if _is_infotainment_relevant(file_info.filename):
                                    infotainment_file_count += 1
                        except Exception as e:
                            print(f"Error reading {file_info.filename} from ZIP: {e}")
                            continue

                print(f"ZIP Processing Complete - Processed: {processed_count}, Skipped: {skipped_files}")

            else:
                # Handle individual files
                try:
                    if _should_exclude_path(file.filename):
                        skipped_files += 1
                        continue

                    if not _is_relevant_for_analysis(file.filename, len(content)):
                        skipped_files += 1
                        continue

                    file_content = content.decode('utf-8', errors='ignore')
                    if len(file_content.strip()) > 0:
                        file_contents[file.filename] = file_content
                        total_files_processed += 1
                        if _is_infotainment_relevant(file.filename):
                            infotainment_file_count += 1
                except Exception as e:
                    print(f"Error reading {file.filename}: {e}")
                    continue

        if infotainment_file_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"No infotainment-relevant files found. Processed {len(file_contents)} files, skipped {skipped_files}. Please upload HTML, JS, CSS, QML, or other UI files."
            )

        # Create analysis record with validated user_id
        analysis = create_infotainment_analysis(
            db=db,
            user_id=user_id,
            file_contents=file_contents,
            selected_models=[],  # Will be set when analysis starts
            selected_standards=["WCAG 2.2", "ISO15008", "NHTSA"]
        )

        return {
            "analysis_id": str(analysis.id),
            "files": list(file_contents.keys()),
            "total_files": len(file_contents),
            "infotainment_files": infotainment_file_count,
            "skipped_files": skipped_files,
            "filtering_stats": filtering_stats,
            "context_type": "infotainment",
            "message": f"Successfully processed {len(file_contents)} relevant files out of {total_files_processed + skipped_files} total files"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _is_infotainment_relevant(filename: str) -> bool:
    """Check if file is relevant for infotainment accessibility analysis."""
    # Web-based infotainment files
    web_extensions = ['.html', '.htm', '.jsx', '.tsx', '.js', '.ts', '.css', '.vue', '.svelte']

    # Embedded infotainment files
    embedded_extensions = ['.qml', '.ui', '.xml', '.cpp', '.c', '.h', '.hpp', '.swift', '.kt', '.java']

    # Configuration and resource files
    config_extensions = ['.json', '.yaml', '.yml', '.plist', '.properties', '.cfg']

    # Check file extension
    if any(filename.lower().endswith(ext) for ext in web_extensions + embedded_extensions + config_extensions):
        return True

    # Check for infotainment-specific keywords in filename
    infotainment_keywords = [
        'hmi', 'dashboard', 'cluster', 'infotainment', 'vehicle', 'automotive',
        'carplay', 'androidauto', 'navigation', 'media', 'climate', 'settings',
        'radio', 'music', 'phone', 'contacts', 'maps', 'traffic', 'voice'
    ]

    return any(keyword in filename.lower() for keyword in infotainment_keywords)


# Enhanced analysis endpoint without vehicle context
@app.post("/api/analyze/{analysis_id}")
async def analyze_code(
        analysis_id: str,
        payload: InfotainmentAnalyzeRequest,
        background_tasks: BackgroundTasks,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Update analysis with infotainment-specific settings
    analysis.status = "analyzing"
    analysis.selected_models = payload.llm_models
    analysis.selected_standards = payload.standards

    db.commit()

    # Start background infotainment analysis
    background_tasks.add_task(run_infotainment_analysis, analysis_id, payload.llm_models, payload.standards, db)

    return {
        "status": "started",
        "analysis_id": analysis_id,
        "context": "infotainment",
        "standards": payload.standards,
        "models": payload.llm_models,
        "files_to_analyze": len(analysis.file_contents)
    }


async def run_infotainment_analysis(analysis_id: str, llm_models: List[str], standards: List[str], db: Session):
    """Enhanced analysis specifically for infotainment systems."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

    try:
        all_issues = {}
        analysis_sessions = {}

        print(f"Starting infotainment analysis for {len(analysis.file_contents)} files with models: {llm_models}")

        for model in llm_models:
            try:
                # Create analysis session tracking
                session = AnalysisSession(
                    analysis_id=analysis_id,
                    model_name=model,
                    started_at=datetime.utcnow()
                )
                db.add(session)
                db.flush()  # Get the session ID
                analysis_sessions[model] = session

                print(f"Starting infotainment analysis with {model} for {len(analysis.file_contents)} files")

                # Analyze with each model using infotainment-specific analyzer
                start_time = datetime.utcnow()
                issues = await llm_analyzer.analyze_code(
                    analysis.file_contents,
                    model,
                    analysis_id,
                    standards  # Pass selected standards to analyzer
                )
                end_time = datetime.utcnow()

                all_issues[model] = issues

                # Update session with results
                session.completed_at = end_time
                session.total_processing_time = (end_time - start_time).total_seconds()
                session.files_processed = len(
                    [f for f in analysis.file_contents.keys() if _is_infotainment_relevant(f)])
                session.issues_found = len(issues)
                session.safety_critical_found = len([i for i in issues if i.get('safety_critical', False)])
                session.success_rate = 100.0  # Assume success if we got here

                # Store issues in database with enhanced infotainment data
                for issue_data in issues:
                    try:
                        issue = create_infotainment_issue(
                            db=db,
                            analysis_id=analysis_id,
                            model_name=model,
                            issue_data=issue_data
                        )
                    except Exception as e:
                        print(f"Error storing issue: {str(e)}")
                        continue

                print(f"Completed {model} analysis: {len(issues)} issues found")

            except Exception as e:
                print(f"Error analyzing with {model}: {str(e)}")
                # Update session with error info
                if model in analysis_sessions:
                    session = analysis_sessions[model]
                    session.completed_at = datetime.utcnow()
                    session.error_count = 1
                    session.success_rate = 0.0
                continue

        # Create enhanced comparisons for infotainment A/B testing
        if len(llm_models) > 1:
            create_infotainment_comparisons(analysis_id, all_issues, db)

        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()

    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        print(f"Analysis failed: {str(e)}")

    db.commit()


def create_infotainment_comparisons(analysis_id: str, all_issues: Dict, db: Session):
    """Create enhanced comparisons for infotainment systems."""
    # Group issues by file and line for comparison
    issue_map = {}

    for model, issues in all_issues.items():
        for issue in issues:
            key = f"{issue['file']}:{issue['line']}"
            if key not in issue_map:
                issue_map[key] = {}
            issue_map[key][model] = issue

    # Create comparison records with infotainment-specific analysis
    for key, model_issues in issue_map.items():
        # Analyze consensus across different dimensions
        safety_critical_consensus = {}
        severity_consensus = {}
        standards_consensus = {}
        automotive_metrics_variance = {}

        for model, issue in model_issues.items():
            safety_critical_consensus[model] = issue.get('safety_critical', False)
            severity_consensus[model] = issue.get('severity', 'medium')

            # Track which standards each model flagged
            standards_flagged = []
            if issue.get('wcag_criteria'):
                standards_flagged.append('WCAG')
            if issue.get('iso15008_criteria'):
                standards_flagged.append('ISO15008')
            if issue.get('nhtsa_criteria'):
                standards_flagged.append('NHTSA')
            if issue.get('sae_criteria'):
                standards_flagged.append('SAE')
            if issue.get('gtr8_criteria'):
                standards_flagged.append('GTR8')

            standards_consensus[model] = standards_flagged

            # Track automotive metrics variance
            metrics = issue.get('automotive_metrics', {})
            automotive_metrics_variance[model] = {
                'eyes_off_road_time': metrics.get('eyes_off_road_time', 0.0),
                'glance_count': metrics.get('glance_count', 0),
                'task_time': metrics.get('task_time', 0.0)
            }

        comparison = LLMComparison(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            file_location=key,
            models_agreed=len(set(i['type'] for i in model_issues.values())) == 1,
            model_results=model_issues,
            standards_consensus=standards_consensus,
            severity_consensus=severity_consensus,
            automotive_metrics_variance=automotive_metrics_variance,
            safety_critical_consensus=safety_critical_consensus
        )
        db.add(comparison)


# Updated get_analysis endpoint without vehicle context
@app.get("/api/analysis/{analysis_id}")
async def get_analysis(
        analysis_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Get comprehensive infotainment analysis summary
    summary = get_infotainment_analysis_summary(db, analysis_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Analysis summary not found")

    issues = db.query(Issue).filter(Issue.analysis_id == analysis_id).all()
    comparisons = db.query(LLMComparison).filter(LLMComparison.analysis_id == analysis_id).all()
    sessions = db.query(AnalysisSession).filter(AnalysisSession.analysis_id == analysis_id).all()

    return {
        "analysis": summary["analysis_info"],
        "summary": summary["issue_summary"],
        "issues": [
            {
                "id": str(issue.id),
                "file": issue.file_name,
                "line": issue.line_number,
                "type": issue.issue_type,
                "severity": issue.severity,
                "safety_critical": issue.safety_critical,
                "description": issue.description,
                "original_code": issue.original_code,
                "suggested_fix": issue.suggested_fix,
                "model": issue.llm_model,
                "user_rating": issue.user_rating,
                "fix_applied": issue.fix_applied,
                # Enhanced infotainment data
                "wcag_criteria": issue.wcag_criteria,
                "wcag_level": issue.wcag_level,
                "wcag_principle": issue.wcag_principle,
                "iso15008_criteria": issue.iso15008_criteria,
                "nhtsa_criteria": issue.nhtsa_criteria,
                "sae_criteria": issue.sae_criteria,
                "gtr8_criteria": issue.gtr8_criteria,
                "automotive_metrics": issue.automotive_metrics,
                "context_conditions": issue.context_conditions,
                "interaction_method": issue.interaction_method
            }
            for issue in issues
        ],
        "comparisons": [
            {
                "id": str(comp.id),
                "location": comp.file_location,
                "models_agreed": comp.models_agreed,
                "results": comp.model_results,
                "standards_consensus": comp.standards_consensus,
                "severity_consensus": comp.severity_consensus,
                "automotive_metrics_variance": comp.automotive_metrics_variance,
                "safety_critical_consensus": comp.safety_critical_consensus
            }
            for comp in comparisons
        ],
        "analysis_sessions": [
            {
                "model": session.model_name,
                "processing_time": session.total_processing_time,
                "files_processed": session.files_processed,
                "issues_found": session.issues_found,
                "safety_critical_found": session.safety_critical_found,
                "success_rate": session.success_rate
            }
            for session in sessions
        ],
        "file_contents": analysis.file_contents,
        "context_type": analysis.context_type,
        "selected_standards": analysis.selected_standards
    }


@app.get("/api/analysis/{analysis_id}/infotainment-insights")
async def get_infotainment_insights(
        analysis_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    """Get specialized insights for infotainment accessibility."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    issues = db.query(Issue).filter(Issue.analysis_id == analysis_id).all()

    # Calculate infotainment-specific insights
    insights = {
        "safety_assessment": {
            "total_safety_critical": len([i for i in issues if i.safety_critical]),
            "nhtsa_violations": [],
            "eyes_off_road_violations": [],
            "task_time_violations": []
        },
        "interaction_analysis": {
            "touch_issues": len([i for i in issues if i.interaction_method == "touch"]),
            "voice_issues": len([i for i in issues if i.interaction_method == "voice"]),
            "physical_button_issues": len([i for i in issues if i.interaction_method == "physical_button"]),
            "steering_wheel_issues": len([i for i in issues if i.interaction_method == "steering_wheel"])
        },
        "standards_compliance": {
            "wcag_a_violations": len([i for i in issues if i.wcag_level == "A"]),
            "wcag_aa_violations": len([i for i in issues if i.wcag_level == "AA"]),
            "wcag_aaa_violations": len([i for i in issues if i.wcag_level == "AAA"]),
            "iso15008_issues": len([i for i in issues if i.iso15008_criteria]),
            "nhtsa_issues": len([i for i in issues if i.nhtsa_criteria])
        },
        "recommendations": []
    }

    # Analyze automotive metrics for violations
    for issue in issues:
        if issue.automotive_metrics:
            metrics = issue.automotive_metrics

            # NHTSA 2-second rule violations
            if metrics.get('eyes_off_road_time', 0) > 2.0:
                insights["safety_assessment"]["eyes_off_road_violations"].append({
                    "issue_id": str(issue.id),
                    "file": issue.file_name,
                    "time": metrics['eyes_off_road_time']
                })

            # NHTSA 12-second task time violations
            if metrics.get('task_time', 0) > 12.0:
                insights["safety_assessment"]["task_time_violations"].append({
                    "issue_id": str(issue.id),
                    "file": issue.file_name,
                    "time": metrics['task_time']
                })

    # Generate recommendations based on findings
    if insights["safety_assessment"]["total_safety_critical"] > 0:
        insights["recommendations"].append({
            "priority": "critical",
            "category": "safety",
            "message": f"Address {insights['safety_assessment']['total_safety_critical']} safety-critical issues immediately"
        })

    if len(insights["safety_assessment"]["eyes_off_road_violations"]) > 0:
        insights["recommendations"].append({
            "priority": "high",
            "category": "distraction",
            "message": f"Reduce eyes-off-road time for {len(insights['safety_assessment']['eyes_off_road_violations'])} interactions"
        })

    if insights["interaction_analysis"]["voice_issues"] > insights["interaction_analysis"]["touch_issues"]:
        insights["recommendations"].append({
            "priority": "medium",
            "category": "interaction",
            "message": "Consider improving voice interface as it has more accessibility issues than touch"
        })

    return insights


@app.post("/api/issue/{issue_id}/rate")
async def rate_issue(
        issue_id: str,
        payload: RatingRequest,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue.user_rating = payload.rating
    db.commit()

    return {"status": "success"}


# UPDATED: Enhanced apply fix endpoint that actually applies the fix
@app.post("/api/issue/{issue_id}/apply")
async def apply_fix(
        issue_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Get the analysis to access file contents
    analysis = db.query(Analysis).filter(Analysis.id == issue.analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        # Get the original file content
        original_content = analysis.file_contents.get(issue.file_name)
        if not original_content:
            raise HTTPException(status_code=404, detail="Original file content not found")

        # Apply the fix to the content
        if issue.suggested_fix:
            fixed_content = apply_code_fix(
                original_content,
                issue.suggested_fix,
                issue.line_number
            )

            # Store the original content if not already stored (for undo)
            if not analysis.original_file_contents:
                analysis.original_file_contents = analysis.file_contents.copy()

            # Update the file content with the fix
            analysis.file_contents[issue.file_name] = fixed_content

            # Mark the issue as fixed
            issue.fix_applied = True
            issue.fix_applied_at = datetime.utcnow()

            db.commit()

            return {
                "status": "success",
                "message": "Fix applied successfully",
                "fixed_content": fixed_content[:500] + "..." if len(fixed_content) > 500 else fixed_content
            }
        else:
            raise HTTPException(status_code=400, detail="No suggested fix available")

    except Exception as e:
        db.rollback()
        print(f"Error applying fix: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to apply fix: {str(e)}")


# NEW: Undo fix endpoint
@app.post("/api/issue/{issue_id}/undo")
async def undo_fix(
        issue_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    if not issue.fix_applied:
        raise HTTPException(status_code=400, detail="Fix was not applied")

    # Get the analysis to access file contents
    analysis = db.query(Analysis).filter(Analysis.id == issue.analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        # Restore original content if available
        if analysis.original_file_contents and issue.file_name in analysis.original_file_contents:
            analysis.file_contents[issue.file_name] = analysis.original_file_contents[issue.file_name]
        else:
            raise HTTPException(status_code=400, detail="Original content not available for undo")

        # Mark the issue as not fixed
        issue.fix_applied = False
        issue.fix_applied_at = None

        db.commit()

        return {
            "status": "success",
            "message": "Fix undone successfully"
        }

    except Exception as e:
        db.rollback()
        print(f"Error undoing fix: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to undo fix: {str(e)}")


@app.post("/api/analysis/{analysis_id}/apply-batch")
async def apply_batch_fixes(
        analysis_id: str,
        payload: BatchFixRequest,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    issues = db.query(Issue).filter(
        Issue.analysis_id == analysis_id,
        Issue.id.in_(payload.issue_ids)
    ).all()

    if not analysis.original_file_contents:
        analysis.original_file_contents = analysis.file_contents.copy()

    applied_count = 0
    failed_fixes = []

    for issue in issues:
        try:
            if issue.suggested_fix and not issue.fix_applied:
                original_content = analysis.file_contents.get(issue.file_name)
                if original_content:
                    fixed_content = apply_code_fix(
                        original_content,
                        issue.suggested_fix,
                        issue.line_number
                    )
                    analysis.file_contents[issue.file_name] = fixed_content
                    issue.fix_applied = True
                    issue.fix_applied_at = datetime.utcnow()
                    applied_count += 1
        except Exception as e:
            failed_fixes.append({
                "issue_id": str(issue.id),
                "error": str(e)
            })

    db.commit()

    return {
        "status": "success",
        "applied_count": applied_count,
        "failed_fixes": failed_fixes
    }


# NEW: Get updated file contents
@app.get("/api/analysis/{analysis_id}/updated-files")
async def get_updated_files(
        analysis_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Get applied fixes count
    applied_fixes = db.query(Issue).filter(
        Issue.analysis_id == analysis_id,
        Issue.fix_applied == True
    ).count()

    return {
        "status": "success",
        "file_contents": analysis.file_contents,
        "original_file_contents": analysis.original_file_contents,
        "applied_fixes_count": applied_fixes,
        "has_changes": applied_fixes > 0
    }


# NEW: Download updated files as ZIP
@app.get("/api/analysis/{analysis_id}/download-updated")
async def download_updated_files(
        analysis_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Check if there are any applied fixes
    applied_fixes = db.query(Issue).filter(
        Issue.analysis_id == analysis_id,
        Issue.fix_applied == True
    ).count()

    if applied_fixes == 0:
        raise HTTPException(status_code=400, detail="No fixes have been applied")

    try:
        # Create temporary directory for ZIP creation
        temp_dir = tempfile.mkdtemp()
        zip_filename = f"updated_infotainment_files_{analysis_id}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in analysis.file_contents.items():
                # Write each file to the ZIP
                zipf.writestr(filename, content)

            # Add a summary file
            summary_content = f"""# Accessibility Fixes Applied

Analysis ID: {analysis_id}
Applied Fixes: {applied_fixes}
Generated: {datetime.utcnow().isoformat()}

Files Updated:
"""
            # List files that were actually changed
            issues_with_fixes = db.query(Issue).filter(
                Issue.analysis_id == analysis_id,
                Issue.fix_applied == True
            ).all()

            file_changes = {}
            for issue in issues_with_fixes:
                if issue.file_name not in file_changes:
                    file_changes[issue.file_name] = []
                file_changes[issue.file_name].append({
                    "line": issue.line_number,
                    "type": issue.issue_type,
                    "description": issue.description
                })

            for filename, changes in file_changes.items():
                summary_content += f"\n## {filename}\n"
                for change in changes:
                    summary_content += f"- Line {change['line']}: {change['type']} - {change['description']}\n"

            zipf.writestr("FIXES_APPLIED.md", summary_content)

        # Read the ZIP file and return it
        with open(zip_path, 'rb') as zip_file:
            zip_data = zip_file.read()

        # Clean up temporary files
        os.remove(zip_path)
        os.rmdir(temp_dir)

        # Return the ZIP file as a response
        return Response(
            content=zip_data,
            media_type='application/zip',
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}"
            }
        )

    except Exception as e:
        print(f"Error creating ZIP: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP file: {str(e)}")


@app.get("/api/analysis/{analysis_id}/report")
async def generate_report(
        analysis_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    issues = db.query(Issue).filter(Issue.analysis_id == analysis_id).all()
    summary = get_infotainment_analysis_summary(db, analysis_id)

    # Generate enhanced PDF report for infotainment
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph("Infotainment Accessibility Analysis Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", styles['Heading1']))
    elements.append(Paragraph(f"Analysis ID: {analysis_id}", styles['Normal']))
    elements.append(Paragraph(f"Date: {analysis.created_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Files Analyzed: {len(analysis.file_names)}", styles['Normal']))
    elements.append(Paragraph(f"Models Used: {', '.join(analysis.selected_models)}", styles['Normal']))
    elements.append(Paragraph(f"Standards Applied: {', '.join(analysis.selected_standards)}", styles['Normal']))

    # Safety critical summary
    safety_critical_count = len([i for i in issues if i.safety_critical])
    if safety_critical_count > 0:
        elements.append(Paragraph(f"⚠️ SAFETY CRITICAL ISSUES: {safety_critical_count}", styles['Normal']))

    # Applied fixes summary
    applied_fixes_count = len([i for i in issues if i.fix_applied])
    elements.append(Paragraph(f"✅ FIXES APPLIED: {applied_fixes_count}", styles['Normal']))

    elements.append(Spacer(1, 12))

    # Standards compliance breakdown
    elements.append(Paragraph("Standards Compliance", styles['Heading2']))
    if summary and summary["issue_summary"]:
        wcag_breakdown = summary["issue_summary"].get("wcag_level_breakdown", {})
        for level, count in wcag_breakdown.items():
            elements.append(Paragraph(f"WCAG {level} violations: {count}", styles['Normal']))

    elements.append(Spacer(1, 12))

    # Issues table
    elements.append(Paragraph("Detailed Issues", styles['Heading2']))
    data = [['File', 'Line', 'Type', 'Severity', 'Safety Critical', 'Model', 'Standards', 'Fixed']]

    for issue in issues[:50]:  # Limit to first 50 issues for PDF
        standards = []
        if issue.wcag_criteria:
            standards.append('WCAG')
        if issue.iso15008_criteria:
            standards.append('ISO15008')
        if issue.nhtsa_criteria:
            standards.append('NHTSA')

        data.append([
            issue.file_name[:30],
            str(issue.line_number or 'N/A'),
            issue.issue_type or 'Unknown',
            issue.severity or 'Medium',
            '⚠️' if issue.safety_critical else '',
            issue.llm_model or 'Unknown',
            ', '.join(standards),
            '✅' if issue.fix_applied else ''
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    # Save report
    report_path = f"/tmp/report_{analysis_id}.pdf"
    with open(report_path, 'wb') as f:
        f.write(buffer.getvalue())

    return FileResponse(
        report_path,
        media_type='application/pdf',
        filename=f"infotainment_accessibility_report_{analysis_id}.pdf"
    )


@app.get("/api/analyses")
async def get_analyses(
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    analyses = db.query(Analysis).filter(Analysis.user_id == user_id).order_by(Analysis.created_at.desc()).all()
    return [
        {
            "id": str(analysis.id),
            "files": analysis.file_names,
            "status": analysis.status,
            "created_at": analysis.created_at.isoformat(),
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
            "context_type": analysis.context_type,
            "models": analysis.selected_models,
            "standards": analysis.selected_standards,
            "error_message": analysis.error_message
        }
        for analysis in analyses
    ]


@app.get("/api/standards")
async def get_standards():
    """Get available accessibility standards for infotainment systems."""
    return {
        "standards": [
            {
                "id": "WCAG 2.2",
                "name": "Web Content Accessibility Guidelines 2.2",
                "description": "International standard for web accessibility",
                "category": "Web Standards",
                "applicable_to": ["HTML", "CSS", "JavaScript", "Web-based HMI"]
            },
            {
                "id": "ISO15008",
                "name": "ISO 15008:2017",
                "description": "Road vehicles — Ergonomic aspects of transport information and control systems",
                "category": "Automotive Standards",
                "applicable_to": ["All infotainment interfaces"]
            },
            {
                "id": "NHTSA",
                "name": "NHTSA Driver Distraction Guidelines",
                "description": "US safety guidelines for in-vehicle electronic devices",
                "category": "Safety Standards",
                "applicable_to": ["All driver-accessible interfaces"]
            },
            {
                "id": "SAE J3016",
                "name": "SAE J3016 Levels of Driving Automation",
                "description": "Standard for automotive automation levels",
                "category": "Automation Standards",
                "applicable_to": ["Automated driving systems"]
            },
            {
                "id": "GTR8",
                "name": "Global Technical Regulation No. 8",
                "description": "UN regulation for Electronic Stability Control systems",
                "category": "International Standards",
                "applicable_to": ["Safety-critical automotive systems"]
            }
        ]
    }


@app.get("/api/models")
async def get_models():
    """Get available LLM models for analysis - now including Llama Maverick."""
    return {
        "models": [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "description": "Advanced reasoning and code analysis",
                "capabilities": ["Code review", "WCAG compliance", "Automotive safety analysis"]
            },
            {
                "id": "claude-opus-4",
                "name": "Claude Opus 4",
                "provider": "Anthropic",
                "description": "Balanced performance for accessibility analysis",
                "capabilities": ["Accessibility review", "Standards compliance", "Detailed explanations"]
            },
            {
                "id": "Deepseek-V3",
                "name": "DeepSeek V3",
                "provider": "DeepSeek",
                "description": "Specialized code analysis and debugging",
                "capabilities": ["Code optimization", "Bug detection", "Performance analysis"]
            },
            {
                "id": "llama-maverick",
                "name": "Llama Maverick",
                "provider": "Meta/Replicate",
                "description": "Latest Llama model with enhanced automotive domain knowledge",
                "capabilities": ["Automotive UI analysis", "Safety-critical code review", "Multi-modal understanding"]
            }
        ]
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Infotainment Accessibility Analyzer",
        "version": "1.0.0"
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)