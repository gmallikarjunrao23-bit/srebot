"""
Incident Service - Business logic for incident management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Incident, IncidentStatus, IncidentSeverity, CheckResult
from infrastructure import (
    DBIncident, DBCheckResult, DBMonitor,
    IncidentStatusEnum, IncidentSeverityEnum
)


class IncidentService:
    """Service for incident lifecycle management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_incident(
        self,
        monitor_id: str,
        monitor_name: str,
        title: str,
        description: Optional[str] = None,
        error_message: Optional[str] = None,
        severity: IncidentSeverity = IncidentSeverity.HIGH
    ) -> Incident:
        """Create a new incident"""
        db_incident = DBIncident(
            monitor_id=monitor_id,
            monitor_name=monitor_name,
            title=title,
            description=description,
            error_message=error_message,
            severity=IncidentSeverityEnum(severity.value),
            status=IncidentStatusEnum.INVESTIGATING
        )
        self.db.add(db_incident)
        await self.db.commit()
        await self.db.refresh(db_incident)
        return self._to_domain(db_incident)
    
    async def get_incident(self, incident_id: str, user_id: int) -> Optional[Incident]:
        """Get incident by ID with ownership verification"""
        result = await self.db.execute(
            select(DBIncident).join(DBMonitor).where(
                DBIncident.id == incident_id,
                DBMonitor.user_id == user_id
            )
        )
        db_incident = result.scalar_one_or_none()
        return self._to_domain(db_incident) if db_incident else None
    
    async def get_incidents_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        monitor_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Incident]:
        """Get incidents for a user with filters"""
        query = select(DBIncident).join(DBMonitor).where(DBMonitor.user_id == user_id)
        
        if status:
            query = query.where(DBIncident.status == IncidentStatusEnum(status))
        if severity:
            query = query.where(DBIncident.severity == IncidentSeverityEnum(severity))
        if monitor_id:
            query = query.where(DBIncident.monitor_id == monitor_id)
        
        query = query.order_by(desc(DBIncident.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return [self._to_domain(i) for i in result.scalars().all()]
    
    async def get_active_incidents(self, user_id: int) -> List[Incident]:
        """Get all non-resolved incidents for a user"""
        result = await self.db.execute(
            select(DBIncident).join(DBMonitor).where(
                DBMonitor.user_id == user_id,
                DBIncident.status != IncidentStatusEnum.RESOLVED,
                DBIncident.status != IncidentStatusEnum.POSTMORTEM
            ).order_by(desc(DBIncident.created_at))
        )
        return [self._to_domain(i) for i in result.scalars().all()]
    
    async def update_incident_status(
        self,
        incident_id: str,
        user_id: int,
        status: IncidentStatus,
        notes: Optional[str] = None
    ) -> Optional[Incident]:
        """Update incident status in lifecycle"""
        incident = await self.get_incident(incident_id, user_id)
        if not incident:
            return None
        
        result = await self.db.execute(
            select(DBIncident).where(DBIncident.id == incident_id)
        )
        db_incident = result.scalar_one()
        
        db_incident.status = IncidentStatusEnum(status.value)
        
        if status == IncidentStatus.RESOLVED:
            db_incident.resolved_at = datetime.utcnow()
            db_incident.resolved_by = user_id
            db_incident.resolution_notes = notes
            if db_incident.started_at:
                db_incident.duration_seconds = int(
                    (db_incident.resolved_at - db_incident.started_at).total_seconds()
                )
        
        db_incident.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(db_incident)
        return self._to_domain(db_incident)
    
    async def add_ai_analysis(
        self,
        incident_id: str,
        analysis: str,
        recommendations: List[str],
        severity_score: float,
        impact_estimate: str,
        recovery_estimate: str
    ) -> Optional[Incident]:
        """Add AI analysis to incident"""
        result = await self.db.execute(
            select(DBIncident).where(DBIncident.id == incident_id)
        )
        db_incident = result.scalar_one_or_none()
        if not db_incident:
            return None
        
        db_incident.ai_analysis = analysis
        db_incident.ai_recommendations = recommendations
        db_incident.ai_severity_score = severity_score
        db_incident.ai_impact_estimate = impact_estimate
        db_incident.ai_recovery_estimate = recovery_estimate
        db_incident.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_incident)
        return self._to_domain(db_incident)
    
    async def add_postmortem(
        self,
        incident_id: str,
        user_id: int,
        postmortem: str
    ) -> Optional[Incident]:
        """Add postmortem to resolved incident"""
        incident = await self.get_incident(incident_id, user_id)
        if not incident:
            return None
        
        result = await self.db.execute(
            select(DBIncident).where(DBIncident.id == incident_id)
        )
        db_incident = result.scalar_one()
        db_incident.postmortem = postmortem
        db_incident.status = IncidentStatusEnum.POSTMORTEM
        db_incident.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_incident)
        return self._to_domain(db_incident)
    
    async def get_incident_check_results(
        self,
        incident_id: str,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get check results related to an incident"""
        incident = await self.get_incident(incident_id, user_id)
        if not incident:
            return []
        
        # Get checks from incident start time
        result = await self.db.execute(
            select(DBCheckResult).where(
                DBCheckResult.monitor_id == incident.monitor_id,
                DBCheckResult.created_at >= incident.started_at
            ).order_by(desc(DBCheckResult.created_at)).limit(limit)
        )
        
        checks = result.scalars().all()
        return [{
            "id": c.id,
            "is_up": c.is_up,
            "response_time_ms": c.response_time_ms,
            "status_code": c.status_code,
            "error_message": c.error_message,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in checks]
    
    async def get_incident_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get incident statistics for a user"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Total incidents
        total_result = await self.db.execute(
            select(func.count(DBIncident.id)).join(DBMonitor).where(
                DBMonitor.user_id == user_id,
                DBIncident.created_at >= since
            )
        )
        total = total_result.scalar() or 0
        
        # By severity
        severity_result = await self.db.execute(
            select(DBIncident.severity, func.count(DBIncident.id)).join(DBMonitor).where(
                DBMonitor.user_id == user_id,
                DBIncident.created_at >= since
            ).group_by(DBIncident.severity)
        )
        by_severity = {s.value: c for s, c in severity_result.all()}
        
        # Average resolution time
        avg_result = await self.db.execute(
            select(func.avg(DBIncident.duration_seconds)).join(DBMonitor).where(
                DBMonitor.user_id == user_id,
                DBIncident.resolved_at.isnot(None),
                DBIncident.created_at >= since
            )
        )
        avg_duration = avg_result.scalar() or 0
        
        # Active incidents
        active = await self.get_active_incidents(user_id)
        
        return {
            "total_incidents": total,
            "active_incidents": len(active),
            "by_severity": by_severity,
            "avg_resolution_time_seconds": round(avg_duration, 2),
            "period_days": days
        }
    
    def _to_domain(self, db_incident: DBIncident) -> Incident:
        """Convert DB model to domain model"""
        return Incident(
            id=db_incident.id,
            monitor_id=db_incident.monitor_id,
            monitor_name=db_incident.monitor_name,
            status=IncidentStatus(db_incident.status.value),
            severity=IncidentSeverity(db_incident.severity.value),
            started_at=db_incident.started_at,
            resolved_at=db_incident.resolved_at,
            duration_seconds=db_incident.duration_seconds,
            affected_services=db_incident.affected_services,
            title=db_incident.title,
            description=db_incident.description,
            root_cause=db_incident.root_cause,
            error_message=db_incident.error_message,
            ai_analysis=db_incident.ai_analysis,
            ai_recommendations=db_incident.ai_recommendations,
            ai_severity_score=db_incident.ai_severity_score,
            ai_impact_estimate=db_incident.ai_impact_estimate,
            ai_recovery_estimate=db_incident.ai_recovery_estimate,
            resolved_by=db_incident.resolved_by,
            resolution_notes=db_incident.resolution_notes,
            postmortem=db_incident.postmortem,
            alerts_sent=db_incident.alerts_sent,
            created_at=db_incident.created_at,
            updated_at=db_incident.updated_at
        )

