"""
Database Infrastructure
Async SQLAlchemy with PostgreSQL
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Enum as SQLEnum, BigInteger
)
from datetime import datetime
import enum

from config import settings

Base = declarative_base()


class MonitorStatusEnum(str, enum.Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class MonitorTypeEnum(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    PING = "ping"
    DNS = "dns"
    SSL = "ssl"
    KEYWORD = "keyword"
    API = "api"


class IncidentStatusEnum(str, enum.Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"


class IncidentSeverityEnum(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class UserRoleEnum(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


# Database Models
class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    role = Column(SQLEnum(UserRoleEnum), default=UserRoleEnum.OWNER)
    is_active = Column(Boolean, default=True)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    notification_preferences = Column(JSON, default=dict)
    max_monitors = Column(Integer, default=10)
    max_teams = Column(Integer, default=1)
    max_status_pages = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    monitors = relationship("DBMonitor", back_populates="user", cascade="all, delete-orphan")
    incidents = relationship("DBIncident", back_populates="resolved_by_user")


class DBMonitor(Base):
    __tablename__ = "monitors"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    url = Column(Text, nullable=False)
    monitor_type = Column(SQLEnum(MonitorTypeEnum), default=MonitorTypeEnum.HTTPS)
    status = Column(SQLEnum(MonitorStatusEnum), default=MonitorStatusEnum.UNKNOWN)
    
    interval = Column(Integer, default=300)
    timeout = Column(Integer, default=30)
    retries = Column(Integer, default=3)
    retry_delay = Column(Integer, default=5)
    
    expected_status_codes = Column(JSON, default=lambda: [200])
    expected_keyword = Column(String(500), nullable=True)
    custom_headers = Column(JSON, default=dict)
    
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    environment = Column(String(50), default="production")
    priority = Column(String(20), default="medium")
    region = Column(String(50), default="global")
    
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    workspace_id = Column(String(36), nullable=True)
    
    uptime_percentage = Column(Float, default=100.0)
    avg_response_time = Column(Float, default=0.0)
    last_check_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    total_checks = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    is_favorite = Column(Boolean, default=False)
    maintenance_window = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("DBUser", back_populates="monitors")
    check_results = relationship("DBCheckResult", back_populates="monitor", cascade="all, delete-orphan")
    incidents = relationship("DBIncident", back_populates="monitor", cascade="all, delete-orphan")


class DBCheckResult(Base):
    __tablename__ = "check_results"
    
    id = Column(String(36), primary_key=True)
    monitor_id = Column(String(36), ForeignKey("monitors.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    response_time_ms = Column(Float, default=0.0)
    is_up = Column(Boolean, default=False)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, default=dict)
    dns_resolution_time = Column(Float, nullable=True)
    ssl_valid = Column(Boolean, nullable=True)
    ssl_expiry_date = Column(DateTime, nullable=True)
    region = Column(String(50), default="global")
    node_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    monitor = relationship("DBMonitor", back_populates="check_results")


class DBIncident(Base):
    __tablename__ = "incidents"
    
    id = Column(String(36), primary_key=True)
    monitor_id = Column(String(36), ForeignKey("monitors.id"), nullable=False)
    monitor_name = Column(String(200), nullable=False)
    status = Column(SQLEnum(IncidentStatusEnum), default=IncidentStatusEnum.INVESTIGATING)
    severity = Column(SQLEnum(IncidentSeverityEnum), default=IncidentSeverityEnum.MEDIUM)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    affected_services = Column(JSON, default=list)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    ai_analysis = Column(Text, nullable=True)
    ai_recommendations = Column(JSON, default=list)
    ai_severity_score = Column(Float, nullable=True)
    ai_impact_estimate = Column(Text, nullable=True)
    ai_recovery_estimate = Column(Text, nullable=True)
    
    resolved_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    postmortem = Column(Text, nullable=True)
    alerts_sent = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    monitor = relationship("DBMonitor", back_populates="incidents")
    resolved_by_user = relationship("DBUser", back_populates="incidents")


class DBTeam(Base):
    __tablename__ = "teams"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    members = Column(JSON, default=list)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class DBStatusPage(Base):
    __tablename__ = "status_pages"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=False)
    is_public = Column(Boolean, default=True)
    custom_domain = Column(String(200), nullable=True)
    logo_url = Column(String(500), nullable=True)
    brand_color = Column(String(20), default="#6366F1")
    monitor_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class DBAlert(Base):
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True)
    incident_id = Column(String(36), nullable=True)
    monitor_id = Column(String(36), nullable=False)
    channel = Column(String(50), default="telegram")
    recipient = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    severity = Column(SQLEnum(IncidentSeverityEnum), default=IncidentSeverityEnum.MEDIUM)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database Engine & Session
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

