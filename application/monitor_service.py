"""
Monitor Service - Business logic for monitoring operations
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Monitor, MonitorStatus, MonitorType, CheckResult
from infrastructure import (
    DBMonitor, DBCheckResult, DBIncident, 
    MonitorStatusEnum, MonitorTypeEnum, IncidentStatusEnum, IncidentSeverityEnum
)


class MonitorService:
    """Service for monitor CRUD and operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_monitor(self, monitor: Monitor) -> Monitor:
        """Create a new monitor"""
        db_monitor = DBMonitor(
            id=monitor.id,
            name=monitor.name,
            url=monitor.url,
            monitor_type=MonitorTypeEnum(monitor.monitor_type.value),
            interval=monitor.interval,
            timeout=monitor.timeout,
            retries=monitor.retries,
            retry_delay=monitor.retry_delay,
            expected_status_codes=monitor.expected_status_codes,
            expected_keyword=monitor.expected_keyword,
            custom_headers=monitor.custom_headers,
            description=monitor.description,
            tags=monitor.tags,
            environment=monitor.environment,
            priority=monitor.priority,
            region=monitor.region,
            user_id=monitor.user_id,
            team_id=monitor.team_id,
            workspace_id=monitor.workspace_id,
            is_active=monitor.is_active,
            is_favorite=monitor.is_favorite
        )
        self.db.add(db_monitor)
        await self.db.commit()
        await self.db.refresh(db_monitor)
        return self._to_domain(db_monitor)
    
    async def get_monitor(self, monitor_id: str, user_id: int) -> Optional[Monitor]:
        """Get monitor by ID with user ownership check"""
        result = await self.db.execute(
            select(DBMonitor).where(
                DBMonitor.id == monitor_id,
                DBMonitor.user_id == user_id
            )
        )
        db_monitor = result.scalar_one_or_none()
        return self._to_domain(db_monitor) if db_monitor else None
    
    async def get_monitors_by_user(
        self, 
        user_id: int, 
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Monitor]:
        """Get all monitors for a user with optional filters"""
        query = select(DBMonitor).where(DBMonitor.user_id == user_id)
        
        if status:
            query = query.where(DBMonitor.status == MonitorStatusEnum(status))
        if is_active is not None:
            query = query.where(DBMonitor.is_active == is_active)
        
        query = query.order_by(desc(DBMonitor.is_favorite), desc(DBMonitor.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return [self._to_domain(m) for m in result.scalars().all()]
    
    async def update_monitor(self, monitor_id: str, user_id: int, updates: Dict[str, Any]) -> Optional[Monitor]:
        """Update monitor fields"""
        result = await self.db.execute(
            select(DBMonitor).where(
                DBMonitor.id == monitor_id,
                DBMonitor.user_id == user_id
            )
        )
        db_monitor = result.scalar_one_or_none()
        if not db_monitor:
            return None
        
        for key, value in updates.items():
            if hasattr(db_monitor, key):
                setattr(db_monitor, key, value)
        
        db_monitor.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(db_monitor)
        return self._to_domain(db_monitor)
    
    async def delete_monitor(self, monitor_id: str, user_id: int) -> bool:
        """Delete a monitor"""
        result = await self.db.execute(
            select(DBMonitor).where(
                DBMonitor.id == monitor_id,
                DBMonitor.user_id == user_id
            )
        )
        db_monitor = result.scalar_one_or_none()
        if not db_monitor:
            return False
        
        await self.db.delete(db_monitor)
        await self.db.commit()
        return True
    
    async def toggle_monitor(self, monitor_id: str, user_id: int) -> Optional[Monitor]:
        """Toggle monitor active/paused state"""
        monitor = await self.get_monitor(monitor_id, user_id)
        if not monitor:
            return None
        
        return await self.update_monitor(
            monitor_id, user_id,
            {"is_active": not monitor.is_active}
        )
    
    async def toggle_favorite(self, monitor_id: str, user_id: int) -> Optional[Monitor]:
        """Toggle favorite status"""
        monitor = await self.get_monitor(monitor_id, user_id)
        if not monitor:
            return None
        
        return await self.update_monitor(
            monitor_id, user_id,
            {"is_favorite": not monitor.is_favorite}
        )
    
    async def update_monitor_status(
        self, 
        monitor_id: str, 
        status: MonitorStatus,
        response_time: float = 0.0
    ) -> None:
        """Update monitor status after check (internal use)"""
        result = await self.db.execute(
            select(DBMonitor).where(DBMonitor.id == monitor_id)
        )
        db_monitor = result.scalar_one_or_none()
        if not db_monitor:
            return
        
        db_monitor.status = MonitorStatusEnum(status.value)
        db_monitor.last_check_at = datetime.utcnow()
        db_monitor.total_checks += 1
        
        if response_time > 0:
            # Exponential moving average for response time
            if db_monitor.avg_response_time == 0:
                db_monitor.avg_response_time = response_time
            else:
                db_monitor.avg_response_time = (
                    db_monitor.avg_response_time * 0.7 + response_time * 0.3
                )
        
        if status == MonitorStatus.DOWN:
            db_monitor.failure_count += 1
            db_monitor.last_failure_at = datetime.utcnow()
        
        # Recalculate uptime percentage
        if db_monitor.total_checks > 0:
            db_monitor.uptime_percentage = round(
                ((db_monitor.total_checks - db_monitor.failure_count) / db_monitor.total_checks) * 100, 2
            )
        
        await self.db.commit()
    
    async def get_monitor_stats(self, monitor_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive monitor statistics"""
        monitor = await self.get_monitor(monitor_id, user_id)
        if not monitor:
            return None
        
        # Get last 24h check results
        day_ago = datetime.utcnow() - timedelta(hours=24)
        result = await self.db.execute(
            select(DBCheckResult).where(
                DBCheckResult.monitor_id == monitor_id,
                DBCheckResult.created_at >= day_ago
            ).order_by(desc(DBCheckResult.created_at))
        )
        checks = result.scalars().all()
        
        if not checks:
            return {
                "monitor": monitor,
                "checks_24h": 0,
                "uptime_24h": 100.0,
                "avg_response_24h": 0.0,
                "incidents_24h": 0
            }
        
        up_checks = sum(1 for c in checks if c.is_up)
        uptime_24h = (up_checks / len(checks)) * 100 if checks else 100.0
        avg_response = sum(c.response_time_ms for c in checks) / len(checks) if checks else 0.0
        
        # Count incidents in last 24h
        incident_result = await self.db.execute(
            select(func.count(DBIncident.id)).where(
                DBIncident.monitor_id == monitor_id,
                DBIncident.created_at >= day_ago
            )
        )
        incidents_24h = incident_result.scalar() or 0
        
        return {
            "monitor": monitor,
            "checks_24h": len(checks),
            "uptime_24h": round(uptime_24h, 2),
            "avg_response_24h": round(avg_response, 2),
            "incidents_24h": incidents_24h,
            "last_checks": [self._check_to_dict(c) for c in checks[:10]]
        }
    
    def _to_domain(self, db_monitor: DBMonitor) -> Monitor:
        """Convert DB model to domain model"""
        return Monitor(
            id=db_monitor.id,
            name=db_monitor.name,
            url=db_monitor.url,
            monitor_type=MonitorType(db_monitor.monitor_type.value),
            status=MonitorStatus(db_monitor.status.value),
            interval=db_monitor.interval,
            timeout=db_monitor.timeout,
            retries=db_monitor.retries,
            retry_delay=db_monitor.retry_delay,
            expected_status_codes=db_monitor.expected_status_codes,
            expected_keyword=db_monitor.expected_keyword,
            custom_headers=db_monitor.custom_headers,
            description=db_monitor.description,
            tags=db_monitor.tags,
            environment=db_monitor.environment,
            priority=db_monitor.priority,
            region=db_monitor.region,
            user_id=db_monitor.user_id,
            team_id=db_monitor.team_id,
            workspace_id=db_monitor.workspace_id,
            uptime_percentage=db_monitor.uptime_percentage,
            avg_response_time=db_monitor.avg_response_time,
            last_check_at=db_monitor.last_check_at,
            last_failure_at=db_monitor.last_failure_at,
            total_checks=db_monitor.total_checks,
            failure_count=db_monitor.failure_count,
            is_active=db_monitor.is_active,
            is_favorite=db_monitor.is_favorite,
            maintenance_window=db_monitor.maintenance_window,
            created_at=db_monitor.created_at,
            updated_at=db_monitor.updated_at
        )
    
    def _check_to_dict(self, check: DBCheckResult) -> Dict[str, Any]:
        """Convert check result to dict"""
        return {
            "id": check.id,
            "is_up": check.is_up,
            "response_time_ms": check.response_time_ms,
            "status_code": check.status_code,
            "error_message": check.error_message,
            "created_at": check.created_at.isoformat() if check.created_at else None
        }

