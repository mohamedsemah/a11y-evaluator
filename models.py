from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import os
from typing import Dict, List, Optional

# Database setup
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/llm_analyzer"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Enhanced User model
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

    # Relationships
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")


# Enhanced Analysis model with original file contents storage
class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_names = Column(JSON, nullable=False)  # List of file names
    file_contents = Column(JSON, nullable=False)  # Dict of current file contents (with fixes applied)
    original_file_contents = Column(JSON)  # Dict of original file contents (for undo functionality)
    selected_models = Column(JSON, default=list)  # List of LLM models used
    selected_standards = Column(JSON, default=list)  # List of accessibility standards

    # Infotainment-specific fields
    context_type = Column(String, default="infotainment")  # infotainment, general, mobile, etc.
    interaction_methods = Column(JSON)  # touch, voice, physical_button, steering_wheel

    # Status and timing
    status = Column(String, default="uploaded")  # uploaded, analyzing, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="analyses")
    issues = relationship("Issue", back_populates="analysis", cascade="all, delete-orphan")
    comparisons = relationship("LLMComparison", back_populates="analysis", cascade="all, delete-orphan")
    sessions = relationship("AnalysisSession", back_populates="analysis", cascade="all, delete-orphan")


# Enhanced Issue model with comprehensive infotainment data
class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)

    # Basic issue information
    file_name = Column(String, nullable=False)
    line_number = Column(Integer)
    column_number = Column(Integer)
    issue_type = Column(String, nullable=False)  # accessibility, usability, safety, performance
    severity = Column(String, default="medium")  # low, medium, high, critical
    safety_critical = Column(Boolean, default=False)

    # Content
    description = Column(Text, nullable=False)
    original_code = Column(Text)
    suggested_fix = Column(Text)

    # LLM analysis metadata
    llm_model = Column(String, nullable=False)
    confidence_score = Column(Float)

    # Accessibility standards compliance
    wcag_criteria = Column(JSON)  # List of WCAG success criteria violated
    wcag_level = Column(String)  # A, AA, AAA
    wcag_principle = Column(String)  # Perceivable, Operable, Understandable, Robust

    # Automotive-specific standards
    iso15008_criteria = Column(JSON)  # ISO 15008 sections violated
    nhtsa_criteria = Column(JSON)  # NHTSA guidelines violated
    sae_criteria = Column(JSON)  # SAE standards violated
    gtr8_criteria = Column(JSON)  # GTR8 requirements violated

    # Infotainment-specific metrics
    automotive_metrics = Column(JSON)  # eyes_off_road_time, glance_count, task_time, etc.
    context_conditions = Column(JSON)  # lighting, driving_mode, speed, etc.
    interaction_method = Column(String)  # touch, voice, physical_button, steering_wheel

    # User feedback and fix tracking
    user_rating = Column(Integer)  # 1-5 rating of fix quality
    fix_applied = Column(Boolean, default=False)
    fix_applied_at = Column(DateTime)
    user_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="issues")


# Enhanced LLM Comparison model for A/B testing
class LLMComparison(Base):
    __tablename__ = "llm_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)

    # Comparison location
    file_location = Column(String, nullable=False)  # file:line format

    # Comparison results
    models_agreed = Column(Boolean, default=False)
    model_results = Column(JSON, nullable=False)  # Dict of model -> issue data

    # Consensus analysis
    standards_consensus = Column(JSON)  # Which standards each model flagged
    severity_consensus = Column(JSON)  # Severity rating by each model
    automotive_metrics_variance = Column(JSON)  # Variance in automotive metrics
    safety_critical_consensus = Column(JSON)  # Safety assessment by each model

    # Quality metrics
    explanation_quality_scores = Column(JSON)  # Quality of explanations by model
    fix_quality_scores = Column(JSON)  # Quality of suggested fixes by model

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="comparisons")


# Analysis session tracking
class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)

    # Session details
    model_name = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # Performance metrics
    total_processing_time = Column(Float)  # seconds
    files_processed = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    safety_critical_found = Column(Integer, default=0)

    # Quality metrics
    success_rate = Column(Float, default=0.0)  # percentage
    error_count = Column(Integer, default=0)
    timeout_count = Column(Integer, default=0)

    # Resource usage
    tokens_used = Column(Integer)
    api_calls_made = Column(Integer)
    cost_estimate = Column(Float)

    # Relationships
    analysis = relationship("Analysis", back_populates="sessions")


# Accessibility standards reference
class AccessibilityStandard(Base):
    __tablename__ = "accessibility_standards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_id = Column(String, unique=True, nullable=False)  # WCAG-2.2, ISO15008, etc.
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # web, automotive, safety, etc.
    applicable_contexts = Column(JSON)  # List of applicable contexts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# WCAG Success Criteria reference - FIXED COLUMN MAPPING
class WCAGSuccessCriteria(Base):
    __tablename__ = "wcag_success_criteria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # FIXED: Map Python attribute 'criterion_id' to database column 'criterion_code'
    criterion_id = Column(String, name='criterion_code', unique=True, nullable=False)  # 1.1.1, 2.1.1, etc.
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    level = Column(String, nullable=False)  # A, AA, AAA
    principle = Column(String, nullable=False)  # Perceivable, Operable, etc.
    guideline = Column(String, nullable=False)
    automotive_relevance = Column(String)  # high, medium, low
    infotainment_examples = Column(JSON)  # Examples specific to infotainment
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Infotainment context reference
class InfotainmentContext(Base):
    __tablename__ = "infotainment_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_name = Column(String, unique=True, nullable=False)
    description = Column(Text)

    # Context parameters
    driving_conditions = Column(JSON)  # parked, moving, highway, city
    lighting_conditions = Column(JSON)  # daylight, night, twilight
    interaction_methods = Column(JSON)  # touch, voice, physical
    user_experience_levels = Column(JSON)  # novice, experienced

    # Safety constraints
    max_eyes_off_road_time = Column(Float, default=2.0)  # seconds
    max_task_completion_time = Column(Float, default=12.0)  # seconds
    max_menu_depth = Column(Integer, default=3)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Enhanced helper functions without vehicle context
def create_infotainment_analysis(
        db: Session,
        user_id: str,
        file_contents: dict,
        selected_models: list,
        selected_standards: list = None
) -> Analysis:
    """Create a new infotainment accessibility analysis with enhanced validation."""

    # Validate user exists before creating analysis
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found in database")

    if selected_standards is None:
        selected_standards = ["WCAG 2.2", "ISO15008", "NHTSA"]

    try:
        analysis = Analysis(
            user_id=user_id,
            file_names=list(file_contents.keys()),
            file_contents=file_contents,
            original_file_contents=None,  # Will be set when first fix is applied
            selected_models=selected_models,
            selected_standards=selected_standards,
            context_type="infotainment",
            status="uploaded"
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    except Exception as e:
        db.rollback()
        print(f"Database error in create_infotainment_analysis: {str(e)}")
        raise


def create_infotainment_issue(
        db: Session,
        analysis_id: str,
        model_name: str,
        issue_data: dict
) -> Issue:
    """Create an issue with comprehensive infotainment data."""

    try:
        # Extract automotive metrics if present
        automotive_metrics = issue_data.get('automotive_metrics', {})

        # Determine safety criticality based on multiple factors
        safety_critical = (
                issue_data.get('safety_critical', False) or
                issue_data.get('severity') == 'critical' or
                automotive_metrics.get('eyes_off_road_time', 0) > 2.0 or
                automotive_metrics.get('task_time', 0) > 12.0 or
                any(criteria.get('safety_impact') == 'high'
                    for criteria in issue_data.get('nhtsa_criteria', []))
        )

        issue = Issue(
            analysis_id=analysis_id,
            file_name=issue_data['file'],
            line_number=issue_data.get('line'),
            column_number=issue_data.get('column'),
            issue_type=issue_data.get('type', 'accessibility'),
            severity=issue_data.get('severity', 'medium'),
            safety_critical=safety_critical,
            description=issue_data['description'],
            original_code=issue_data.get('original_code'),
            suggested_fix=issue_data.get('suggested_fix'),
            llm_model=model_name,
            confidence_score=issue_data.get('confidence_score'),

            # WCAG compliance
            wcag_criteria=issue_data.get('wcag_criteria'),
            wcag_level=issue_data.get('wcag_level'),
            wcag_principle=issue_data.get('wcag_principle'),

            # Automotive standards
            iso15008_criteria=issue_data.get('iso15008_criteria'),
            nhtsa_criteria=issue_data.get('nhtsa_criteria'),
            sae_criteria=issue_data.get('sae_criteria'),
            gtr8_criteria=issue_data.get('gtr8_criteria'),

            # Infotainment metrics
            automotive_metrics=automotive_metrics,
            context_conditions=issue_data.get('context_conditions'),
            interaction_method=issue_data.get('interaction_method', 'touch')
        )

        db.add(issue)
        db.flush()  # Get the ID without committing
        return issue

    except Exception as e:
        print(f"Error creating infotainment issue: {str(e)}")
        raise


def get_infotainment_analysis_summary(db: Session, analysis_id: str) -> Optional[Dict]:
    """Get comprehensive analysis summary for infotainment systems."""

    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return None

        issues = db.query(Issue).filter(Issue.analysis_id == analysis_id).all()

        # Calculate comprehensive statistics
        total_issues = len(issues)
        safety_critical_count = len([i for i in issues if i.safety_critical])
        applied_fixes_count = len([i for i in issues if i.fix_applied])

        # Severity breakdown
        severity_breakdown = {}
        for severity in ['low', 'medium', 'high', 'critical']:
            severity_breakdown[severity] = len([i for i in issues if i.severity == severity])

        # WCAG level breakdown
        wcag_level_breakdown = {}
        for level in ['A', 'AA', 'AAA']:
            wcag_level_breakdown[level] = len([i for i in issues if i.wcag_level == level])

        # Standards compliance
        standards_breakdown = {
            'wcag': len([i for i in issues if i.wcag_criteria]),
            'iso15008': len([i for i in issues if i.iso15008_criteria]),
            'nhtsa': len([i for i in issues if i.nhtsa_criteria]),
            'sae': len([i for i in issues if i.sae_criteria]),
            'gtr8': len([i for i in issues if i.gtr8_criteria])
        }

        # Interaction method breakdown
        interaction_breakdown = {}
        for method in ['touch', 'voice', 'physical_button', 'steering_wheel']:
            interaction_breakdown[method] = len([i for i in issues if i.interaction_method == method])

        # Automotive metrics analysis
        metrics_analysis = {
            'avg_eyes_off_road_time': 0.0,
            'max_eyes_off_road_time': 0.0,
            'violations_over_2s': 0,
            'avg_task_time': 0.0,
            'max_task_time': 0.0,
            'violations_over_12s': 0
        }

        eyes_off_times = []
        task_times = []

        for issue in issues:
            if issue.automotive_metrics:
                metrics = issue.automotive_metrics

                eyes_off_time = metrics.get('eyes_off_road_time', 0.0)
                if eyes_off_time > 0:
                    eyes_off_times.append(eyes_off_time)
                    if eyes_off_time > 2.0:
                        metrics_analysis['violations_over_2s'] += 1

                task_time = metrics.get('task_time', 0.0)
                if task_time > 0:
                    task_times.append(task_time)
                    if task_time > 12.0:
                        metrics_analysis['violations_over_12s'] += 1

        if eyes_off_times:
            metrics_analysis['avg_eyes_off_road_time'] = sum(eyes_off_times) / len(eyes_off_times)
            metrics_analysis['max_eyes_off_road_time'] = max(eyes_off_times)

        if task_times:
            metrics_analysis['avg_task_time'] = sum(task_times) / len(task_times)
            metrics_analysis['max_task_time'] = max(task_times)

        return {
            "analysis_info": {
                "id": str(analysis.id),
                "status": analysis.status,
                "created_at": analysis.created_at.isoformat(),
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "file_count": len(analysis.file_names),
                "models_used": analysis.selected_models,
                "standards_applied": analysis.selected_standards,
                "context_type": analysis.context_type,
                "has_applied_fixes": applied_fixes_count > 0,
                "applied_fixes_count": applied_fixes_count
            },
            "issue_summary": {
                "total_issues": total_issues,
                "safety_critical_count": safety_critical_count,
                "applied_fixes_count": applied_fixes_count,
                "severity_breakdown": severity_breakdown,
                "wcag_level_breakdown": wcag_level_breakdown,
                "standards_breakdown": standards_breakdown,
                "interaction_breakdown": interaction_breakdown,
                "automotive_metrics": metrics_analysis
            }
        }

    except Exception as e:
        print(f"Error generating infotainment analysis summary: {str(e)}")
        return None


def initialize_infotainment_standards(db: Session):
    """Initialize the database with infotainment accessibility standards."""

    # Initialize WCAG Success Criteria relevant to infotainment
    infotainment_wcag_criteria = [
        {
            'criterion_id': '1.1.1',
            'title': 'Non-text Content',
            'description': 'All non-text content has text alternatives',
            'level': 'A',
            'principle': 'Perceivable',
            'guideline': 'Text Alternatives',
            'automotive_relevance': 'high',
            'infotainment_examples': ['Icons need alt text', 'Audio alerts need visual indicators']
        },
        {
            'criterion_id': '1.4.3',
            'title': 'Contrast (Minimum)',
            'description': 'Text has contrast ratio of at least 4.5:1',
            'level': 'AA',
            'principle': 'Perceivable',
            'guideline': 'Distinguishable',
            'automotive_relevance': 'high',
            'infotainment_examples': ['Dashboard text visibility in sunlight', 'Night mode contrast']
        },
        {
            'criterion_id': '2.1.1',
            'title': 'Keyboard',
            'description': 'All functionality available from keyboard',
            'level': 'A',
            'principle': 'Operable',
            'guideline': 'Keyboard Accessible',
            'automotive_relevance': 'high',
            'infotainment_examples': ['Steering wheel controls', 'Voice commands as keyboard alternative']
        },
        {
            'criterion_id': '2.2.1',
            'title': 'Timing Adjustable',
            'description': 'User can turn off, adjust, or extend time limits',
            'level': 'A',
            'principle': 'Operable',
            'guideline': 'Enough Time',
            'automotive_relevance': 'high',
            'infotainment_examples': ['Navigation input timeouts', 'Menu auto-dismiss timers']
        }
    ]

    try:
        for criteria_data in infotainment_wcag_criteria:
            # FIXED: Query using the correct Python attribute name
            existing = db.query(WCAGSuccessCriteria).filter(
                WCAGSuccessCriteria.criterion_id == criteria_data['criterion_id']
            ).first()

            if not existing:
                criteria = WCAGSuccessCriteria(**criteria_data)
                db.add(criteria)

        # Initialize infotainment contexts
        default_contexts = [
            {
                'context_name': 'highway_driving',
                'description': 'High-speed highway driving conditions',
                'driving_conditions': ['highway', 'high_speed'],
                'lighting_conditions': ['daylight', 'night'],
                'interaction_methods': ['voice', 'steering_wheel'],
                'user_experience_levels': ['experienced'],
                'max_eyes_off_road_time': 1.5,
                'max_task_completion_time': 8.0,
                'max_menu_depth': 2
            },
            {
                'context_name': 'city_driving',
                'description': 'Urban city driving with frequent stops',
                'driving_conditions': ['city', 'stop_and_go'],
                'lighting_conditions': ['daylight', 'twilight', 'night'],
                'interaction_methods': ['touch', 'voice', 'physical_button'],
                'user_experience_levels': ['novice', 'experienced'],
                'max_eyes_off_road_time': 2.0,
                'max_task_completion_time': 12.0,
                'max_menu_depth': 3
            },
            {
                'context_name': 'parked',
                'description': 'Vehicle parked with engine running',
                'driving_conditions': ['parked'],
                'lighting_conditions': ['daylight', 'night'],
                'interaction_methods': ['touch', 'voice', 'physical_button', 'steering_wheel'],
                'user_experience_levels': ['novice', 'experienced'],
                'max_eyes_off_road_time': 30.0,
                'max_task_completion_time': 60.0,
                'max_menu_depth': 5
            }
        ]

        for context_data in default_contexts:
            existing = db.query(InfotainmentContext).filter(
                InfotainmentContext.context_name == context_data['context_name']
            ).first()

            if not existing:
                context = InfotainmentContext(**context_data)
                db.add(context)

        db.commit()
        print("Infotainment standards initialized successfully")

    except Exception as e:
        db.rollback()
        print(f"Error initializing infotainment standards: {str(e)}")
        raise


# Create all tables
def create_tables():
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")

        # Initialize standards data
        db = SessionLocal()
        try:
            initialize_infotainment_standards(db)
        finally:
            db.close()

    except Exception as e:
        print(f"Error creating database tables: {str(e)}")
        raise


if __name__ == "__main__":
    create_tables()


# Add this to the bottom of your models.py file

def run_migration_if_needed():
    """
    Check if migration is needed and run it automatically
    This will add the original_file_contents column if it doesn't exist
    """
    from sqlalchemy import text

    try:
        db = SessionLocal()

        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='analyses' AND column_name='original_file_contents';
        """)).fetchone()

        if not result:
            print("🔄 Running database migration: Adding original_file_contents column...")

            # Add the column
            db.execute(text("ALTER TABLE analyses ADD COLUMN original_file_contents JSON;"))

            # Add indexes for better performance
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);"))
            db.execute(
                text("CREATE INDEX IF NOT EXISTS idx_analyses_user_created ON analyses(user_id, created_at DESC);"))

            db.commit()
            print("✅ Migration completed successfully!")
        else:
            print("✅ Database schema is up to date")

        db.close()

    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        if 'db' in locals():
            db.rollback()
            db.close()


# Run migration check when models.py is imported
if __name__ == "__main__":
    create_tables()
    run_migration_if_needed()
else:
    # Auto-run migration check when imported
    try:
        run_migration_if_needed()
    except Exception as e:
        print(f"Warning: Could not check/run migration: {e}")