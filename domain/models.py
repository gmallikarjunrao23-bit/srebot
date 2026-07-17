"""
Domain Models - Core Business Entities
Clean Architecture: Domain layer has no external dependencies
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import uuid


class MonitorStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class MonitorType(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    PING = "ping"
    DNS = "dns"
    SSL = "ssl"
    KEYWORD = "keyword"
    API = "api"


class IncidentStatus(str, Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class AlertChannel(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class Monitor:
    """Core monitor entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    url: str = ""
    monitor_type: MonitorType = MonitorType.HTTPS
    status: MonitorStatus = MonitorStatus.UNKNOWN
    
    # Configuration
    interval: int = 300  # seconds
    timeout: int = 30
    retries: int = 3
    retry_delay: int = 5
    
    # Validation
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    expected_keyword: Optional[str] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    environment: str = "production"
    priority: str = "medium"
    region: str = "global"
    
    # Ownership
    user_id: int = 0
    team_id: Optional[str] = None
    workspace_id: Optional[str] = None
    
    # Statistics
    uptime_percentage: float = 100.0
    avg_response_time: float = 0.0
    last_check_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    total_checks: int = 0
    failure_count: int = 0
    
    # State
    is_active: bool = True
    is_favorite: bool = False
    maintenance_window: Optional[Dict[str, Any]] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CheckResult:
    """Result of a single monitoring check"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    monitor_id: str = ""
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    response_time_ms: float = 0.0
    
    # Result
    is_up: bool = False
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Details
    response_body: Optional[str] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    dns_resolution_time: Optional[float] = None
    ssl_valid: Optional[bool] = None
    ssl_expiry_date: Optional[datetime] = None
    
    # Location
    region: str = "global"
    node_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Incident:
    """Incident entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    monitor_id: str = ""
    monitor_name: str = ""
    
    # Lifecycle
    status: IncidentStatus = IncidentStatus.INVESTIGATING
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    
    # Impact
    started_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    affected_services: List[str] = field(default_factory=list)
    
    # Details
    title: str = ""
    description: Optional[str] = None
    root_cause: Optional[str] = None
    error_message: Optional[str] = None
    
    # AI Analysis
    ai_analysis: Optional[str] = None
    ai_recommendations: List[str] = field(default_factory=list)
    ai_severity_score: Optional[float] = None
    ai_impact_estimate: Optional[str] = None
    ai_recovery_estimate: Optional[str] = None
    
    # Resolution
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    postmortem: Optional[str] = None
    
    # Notifications
    alerts_sent: List[Dict[str, Any]] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    """Alert/Notification entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: Optional[str] = None
    monitor_id: str = ""
    
    channel: AlertChannel = AlertChannel.TELEGRAM
    recipient: str = ""  # chat_id, email, webhook URL
    
    content: str = ""
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class User:
    """User entity"""
    id: int = 0  # Telegram user_id
    username: Optional[str] = None
    first_name: str = ""
    last_name: Optional[str] = None
    
    role: UserRole = UserRole.OWNER
    is_active: bool = True
    
    # Preferences
    timezone: str = "UTC"
    language: str = "en"
    notification_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Limits
    max_monitors: int = 10
    max_teams: int = 1
    max_status_pages: int = 1
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Team:
    """Team/Organization entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    owner_id: int = 0
    
    members: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StatusPage:
    """Public status page entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    description: Optional[str] = None
    
    team_id: str = ""
    is_public: bool = True
    custom_domain: Optional[str] = None
    
    # Branding
    logo_url: Optional[str] = None
    brand_color: str = "#6366F1"
    
    # Services displayed
    monitor_ids: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnalyticsSnapshot:
    """Analytics data snapshot"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    monitor_id: str = ""
    
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    
    # Metrics
    total_checks: int = 0
    uptime_percentage: float = 100.0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    error_rate: float = 0.0
    
    # Incidents
    incident_count: int = 0
    total_downtime_seconds: int = 0
    
    # AI Insights
    health_score: float = 100.0
    trend: str = "stable"
    recommendations: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)

