from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks, Header
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
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

# Initialize database
from models import engine
Base.metadata.create_all(bind=engine)

# Initialize Infotainment LLM analyzer
llm_analyzer = InfotainmentLLMAnalyzer()

# Security
security = HTTPBearer()


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
    vehicle_context: Optional[Dict] = None


class VehicleContextRequest(BaseModel):
    driving_mode: bool = True
    lighting_condition: str = "variable"  # daylight, night, twilight, variable
    speed_range: str = "0-120"  # 0, 1-30, 31-60, 61+
    interaction_methods: List[str] = ["touch", "voice", "physical_button"]
    user_experience_level: str = "experienced"  # novice, experienced


# Enhanced Authentication endpoints with better error handling
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


# Enhanced file upload with user validation
@app.post("/api/upload")
async def upload_files(
        files: List[UploadFile] = File(...),
        user_id: str = Depends(get_current_user_with_validation),  # Enhanced validation
        db: Session = Depends(get_db)
):
    analysis_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp()

    try:
        file_contents = {}
        infotainment_file_count = 0

        for file in files:
            if file.size > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 50MB limit")

            content = await file.read()

            # Handle ZIP files
            if file.filename.endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    for name in zf.namelist():
                        if not name.endswith('/'):
                            try:
                                file_content = zf.read(name).decode('utf-8', errors='ignore')
                                file_contents[name] = file_content
                                if _is_infotainment_relevant(name):
                                    infotainment_file_count += 1
                            except Exception as e:
                                print(f"Error reading {name} from ZIP: {e}")
                                continue
            else:
                try:
                    file_content = content.decode('utf-8', errors='ignore')
                    file_contents[file.filename] = file_content
                    if _is_infotainment_relevant(file.filename):
                        infotainment_file_count += 1
                except Exception as e:
                    print(f"Error reading {file.filename}: {e}")
                    continue

        if infotainment_file_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No infotainment-relevant files found. Please upload HTML, JS, CSS, QML, or other UI files."
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
            "context_type": "infotainment"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        shutil.rmtree(temp_dir)


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


# Enhanced analysis endpoint with user validation
@app.post("/api/analyze/{analysis_id}")
async def analyze_code(
        analysis_id: str,
        payload: InfotainmentAnalyzeRequest,
        background_tasks: BackgroundTasks,
        user_id: str = Depends(get_current_user_with_validation),  # Enhanced validation
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

    # Set vehicle context with defaults
    if payload.vehicle_context:
        analysis.vehicle_context = payload.vehicle_context
    else:
        analysis.vehicle_context = {
            "driving_mode": True,
            "lighting_condition": "variable",
            "speed_range": "0-120",
            "interaction_methods": ["touch", "voice", "physical_button"],
            "user_experience_level": "experienced"
        }

    db.commit()

    # Start background infotainment analysis
    background_tasks.add_task(run_infotainment_analysis, analysis_id, payload.llm_models, payload.standards, db)

    return {
        "status": "started",
        "analysis_id": analysis_id,
        "context": "infotainment",
        "standards": payload.standards,
        "models": payload.llm_models
    }


async def run_infotainment_analysis(analysis_id: str, llm_models: List[str], standards: List[str], db: Session):
    """Enhanced analysis specifically for infotainment systems."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

    try:
        all_issues = {}
        analysis_sessions = {}

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
                    analysis_id
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


# All other endpoints updated with enhanced user validation
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
        "vehicle_context": analysis.vehicle_context,
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


@app.post("/api/issue/{issue_id}/apply")
async def apply_fix(
        issue_id: str,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue.fix_applied = True
    issue.fix_applied_at = datetime.utcnow()
    db.commit()

    return {"status": "success"}


@app.post("/api/analysis/{analysis_id}/apply-batch")
async def apply_batch_fixes(
        analysis_id: str,
        payload: BatchFixRequest,
        user_id: str = Depends(get_current_user_with_validation),
        db: Session = Depends(get_db)
):
    issues = db.query(Issue).filter(
        Issue.analysis_id == analysis_id,
        Issue.id.in_(payload.issue_ids)
    ).all()

    for issue in issues:
        issue.fix_applied = True
        issue.fix_applied_at = datetime.utcnow()

    db.commit()

    return {"status": "success", "applied_count": len(issues)}


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
    data = [['File', 'Line', 'Type', 'Severity', 'Safety Critical', 'Model', 'Standards']]

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
            ', '.join(standards)
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
            "vehicle_context": analysis.vehicle_context,
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
    """Get available LLM models for analysis."""
    return {
        "models": [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "OpenAI",
                "description": "Advanced reasoning and code analysis",
                "capabilities": ["Code review", "WCAG compliance", "Automotive safety analysis"]
            },
            {
                "id": "claude-3-sonnet",
                "name": "Claude 3 Sonnet",
                "provider": "Anthropic",
                "description": "Balanced performance for accessibility analysis",
                "capabilities": ["Accessibility review", "Standards compliance", "Detailed explanations"]
            },
            {
                "id": "deepseek-coder",
                "name": "DeepSeek Coder",
                "provider": "DeepSeek",
                "description": "Specialized code analysis and debugging",
                "capabilities": ["Code optimization", "Bug detection", "Performance analysis"]
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