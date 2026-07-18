"""
Celery Background Tasks
Continuous monitoring and alerting engine
"""
import asyncio
import os
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from config import settings
from infrastructure import AsyncSessionLocal, init_db, ai_engine
from application import MonitorService, IncidentService
from monitoring import monitoring_engine
from domain import MonitorStatus, IncidentSeverity

# Celery app
celery_app = Celery(
    "srebot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60,
    worker_prefetch_multiplier=1,
)


async def run_monitor_check(monitor_id: str):
    """Run a single monitor check and handle incidents"""
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        incident_service = IncidentService(db)
        
        # Get all monitors (simplified - in production, fetch by ID)
        monitors = await monitor_service.get_monitors_by_user(user_id=0)  # You'll need to adjust this
        
        for monitor in monitors:
            if monitor.id != monitor_id or not monitor.is_active:
                continue
            
            # Run check
            result = await monitoring_engine.check_with_retries(monitor)
            
            # Update monitor status
            new_status = MonitorStatus.OPERATIONAL if result.is_up else MonitorStatus.DOWN
            await monitor_service.update_monitor_status(monitor.id, new_status, result.response_time_ms)
            
            # Handle incident creation/recovery
            if not result.is_up and monitor.status != MonitorStatus.DOWN:
                # Create incident
                incident = await incident_service.create_incident(
                    monitor_id=monitor.id,
                    monitor_name=monitor.name,
                    title=f"{monitor.name} is down",
                    error_message=result.error_message,
                    severity=IncidentSeverity.HIGH
                )
                
                # AI Analysis
                try:
                    previous_checks = []  # Fetch from DB in production
                    ai_result = await ai_engine.analyze_incident(
                        monitor_name=monitor.name,
                        monitor_type=monitor.monitor_type.value,
                        error_message=result.error_message or "Unknown error",
                        status_code=result.status_code,
                        response_time=result.response_time_ms,
                        previous_checks=previous_checks
                    )
                    
                    await incident_service.add_ai_analysis(
                        incident.id,
                        ai_result["analysis"],
                        ai_result["recommendations"],
                        ai_result["severity_score"],
                        ai_result["impact_estimate"],
                        ai_result["recovery_estimate"]
                    )
                except Exception as e:
                    print(f"AI analysis failed: {e}")
                
                # Send alert (implement Telegram bot send here)
                print(f"ALERT: {monitor.name} is DOWN")
            
            elif result.is_up and monitor.status == MonitorStatus.DOWN:
                # Resolve active incidents
                active = await incident_service.get_active_incidents(monitor.user_id)
                for inc in active:
                    if inc.monitor_id == monitor.id:
                        await incident_service.update_incident_status(
                            inc.id, monitor.user_id, 
                            IncidentStatus.RESOLVED,
                            "Service recovered"
                        )
                        print(f"RECOVERY: {monitor.name} is UP")


@celery_app.task(bind=True, max_retries=3)
def check_monitor(self, monitor_id: str):
    """Celery task to check a monitor"""
    try:
        asyncio.run(run_monitor_check(monitor_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def generate_daily_reports():
    """Generate daily analytics reports"""
    print("Generating daily reports...")
    # Implementation for daily report generation


@celery_app.task
def cleanup_old_data():
    """Cleanup old check results (retention policy)"""
    print("Cleaning up old data...")
    # Implementation for data cleanup

