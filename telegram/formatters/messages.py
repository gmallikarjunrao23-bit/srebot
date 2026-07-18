"""
Telegram Message Formatters
Premium enterprise-grade message formatting for SRE Bot
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from domain import Monitor, MonitorStatus, Incident, IncidentSeverity, CheckResult


class MessageFormatter:
    """
    Premium message formatter
    Creates beautiful, professional Telegram messages
    Uses HTML parse mode (much more reliable than MarkdownV2)
    """
    
    STATUS_EMOJIS = {
        MonitorStatus.OPERATIONAL: "🟢",
        MonitorStatus.DEGRADED: "🟡",
        MonitorStatus.DOWN: "🔴",
        MonitorStatus.PAUSED: "⏸️",
        MonitorStatus.MAINTENANCE: "🔧",
        MonitorStatus.UNKNOWN: "⚪"
    }
    
    SEVERITY_EMOJIS = {
        IncidentSeverity.CRITICAL: "🔴",
        IncidentSeverity.HIGH: "🟠",
        IncidentSeverity.MEDIUM: "🟡",
        IncidentSeverity.LOW: "🔵",
        IncidentSeverity.INFORMATIONAL: "⚪"
    }
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
    
    @classmethod
    def dashboard(cls, stats: Dict[str, Any]) -> str:
        """Main dashboard message"""
        total = stats.get("total_monitors", 0)
        operational = stats.get("operational", 0)
        down = stats.get("down", 0)
        degraded = stats.get("degraded", 0)
        active_incidents = stats.get("active_incidents", 0)
        avg_uptime = stats.get("avg_uptime", 100.0)
        
        health_color = "🟢" if avg_uptime >= 99 else "🟡" if avg_uptime >= 95 else "🔴"
        
        return f"""<b>🚀 SRE Bot — Command Center</b>

<b>{health_color} System Health: {avg_uptime}%</b>

📊 <b>Overview</b>
├ Monitors: <code>{total}</code>
├ 🟢 Operational: <code>{operational}</code>
├ 🟡 Degraded: <code>{degraded}</code>
├ 🔴 Down: <code>{down}</code>
└ 🚨 Active Incidents: <code>{active_incidents}</code>

<i>Last updated: {datetime.utcnow().strftime('%H:%M:%S UTC')}</i>

💡 <b>Quick Actions:</b> Use the buttons below to navigate"""
    
    @classmethod
    def monitor_card(cls, monitor: Monitor, detailed: bool = False) -> str:
        """Format a monitor as a beautiful card"""
        status_emoji = cls.STATUS_EMOJIS.get(monitor.status, "⚪")
        fav = "⭐ " if monitor.is_favorite else ""
        
        response_time = f"{monitor.avg_response_time:.0f}ms" if monitor.avg_response_time > 0 else "N/A"
        last_check = monitor.last_check_at.strftime("%H:%M:%S") if monitor.last_check_at else "Never"
        
        message = f"""{fav}<b>{status_emoji} {cls.escape_html(monitor.name)}</b>

🔗 <code>{cls.escape_html(monitor.url)}</code>
├ Type: <code>{monitor.monitor_type.value.upper()}</code>
├ Status: <code>{monitor.status.value.upper()}</code>
├ Uptime: <code>{monitor.uptime_percentage}%</code>
├ Avg Response: <code>{response_time}</code>
├ Interval: <code>{monitor.interval}s</code>
├ Region: <code>{monitor.region}</code>
└ Last Check: <code>{last_check}</code>
"""
        
        if detailed:
            message += f"""
📋 <b>Configuration</b>
├ Timeout: <code>{monitor.timeout}s</code>
├ Retries: <code>{monitor.retries}</code>
├ Expected Codes: <code>{', '.join(map(str, monitor.expected_status_codes))}</code>
├ Environment: <code>{monitor.environment}</code>
├ Priority: <code>{monitor.priority}</code>
└ Tags: <code>{', '.join(monitor.tags) if monitor.tags else 'None'}</code>
"""
        
        if monitor.description:
            message += f"\n📝 {cls.escape_html(monitor.description)}"
        
        return message
    
    @classmethod
    def monitor_list(cls, monitors: List[Monitor], page: int = 1, total_pages: int = 1) -> str:
        """Format monitor list"""
        if not monitors:
            return "<b>📋 Your Monitors</b>\n\n<i>No monitors configured yet.</i>\n\nTap ➕ Add Monitor to get started."
        
        message = f"<b>📋 Your Monitors</b>  <i>(Page {page}/{total_pages})</i>\n\n"
        
        for monitor in monitors:
            status_emoji = cls.STATUS_EMOJIS.get(monitor.status, "⚪")
            fav = "⭐" if monitor.is_favorite else ""
            rt = f"{monitor.avg_response_time:.0f}ms" if monitor.avg_response_time > 0 else "N/A"
            message += f"{fav}{status_emoji} <b>{cls.escape_html(monitor.name)}</b>\n   └ <code>{monitor.uptime_percentage}%</code> · <code>{rt}</code> · <code>{monitor.monitor_type.value.upper()}</code>\n\n"
        
        return message
    
    @classmethod
    def incident_card(cls, incident: Incident, detailed: bool = False) -> str:
        """Format incident as a story card"""
        severity_emoji = cls.SEVERITY_EMOJIS.get(incident.severity, "⚪")
        
        duration = "Ongoing"
        if incident.duration_seconds:
            duration = f"{incident.duration_seconds}s"
        elif incident.resolved_at and incident.started_at:
            delta = incident.resolved_at - incident.started_at
            duration = f"{int(delta.total_seconds())}s"
        
        message = f"""{severity_emoji} <b>INCIDENT: {cls.escape_html(incident.title)}</b>

📍 <b>Details</b>
├ Monitor: <code>{cls.escape_html(incident.monitor_name)}</code>
├ Severity: <code>{incident.severity.value.upper()}</code>
├ Status: <code>{incident.status.value.upper()}</code>
├ Duration: <code>{duration}</code>
└ Started: <code>{incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</code>
"""
        
        if incident.error_message:
            message += f"\n❌ <b>Error:</b>\n<code>{cls.escape_html(incident.error_message[:200])}</code>"
        
        if incident.ai_analysis:
            message += f"\n\n🤖 <b>AI Analysis:</b>\n{cls.escape_html(incident.ai_analysis[:400])}"
        
        if incident.ai_recommendations:
            message += "\n\n💡 <b>AI Recommendations:</b>\n"
            for rec in incident.ai_recommendations[:3]:
                message += f"• {cls.escape_html(rec)}\n"
        
        if detailed and incident.resolution_notes:
            message += f"\n✅ <b>Resolution:</b>\n{cls.escape_html(incident.resolution_notes)}"
        
        if detailed and incident.postmortem:
            message += f"\n\n📄 <b>Postmortem:</b>\n{cls.escape_html(incident.postmortem[:500])}"
        
        return message
    
    @classmethod
    def incident_list(cls, incidents: List[Incident], page: int = 1, total_pages: int = 1) -> str:
        """Format incident list"""
        if not incidents:
            return "<b>🚨 Incidents</b>\n\n<i>No incidents found.</i>\n\nEverything looks healthy! 🎉"
        
        message = f"<b>🚨 Incidents</b>  <i>(Page {page}/{total_pages})</i>\n\n"
        
        for incident in incidents:
            severity_emoji = cls.SEVERITY_EMOJIS.get(incident.severity, "⚪")
            status = "🔴" if incident.status not in ["resolved", "postmortem"] else "✅"
            message += f"{status}{severity_emoji} <b>{cls.escape_html(incident.title)}</b>\n   └ <code>{incident.status.value}</code> · <code>{incident.severity.value}</code> · <code>{incident.monitor_name}</code>\n\n"
        
        return message
    
    @classmethod
    def alert_message(
        cls,
        monitor_name: str,
        status: str,
        error: Optional[str] = None,
        response_time: float = 0.0,
        ai_analysis: Optional[str] = None
    ) -> str:
        """Format alert notification"""
        if status == "down":
            emoji = "🔴"
            title = "ALERT: Service Down"
        elif status == "recovered":
            emoji = "🟢"
            title = "RECOVERED: Service Restored"
        else:
            emoji = "🟡"
            title = "WARNING: Service Degraded"
        
        message = f"""{emoji} <b>{title}</b>

📍 <b>{cls.escape_html(monitor_name)}</b>
├ Status: <code>{status.upper()}</code>
├ Response Time: <code>{response_time:.0f}ms</code>
└ Time: <code>{datetime.utcnow().strftime('%H:%M:%S UTC')}</code>
"""
        
        if error:
            message += f"\n❌ <b>Error:</b>\n<code>{cls.escape_html(error[:200])}</code>"
        
        if ai_analysis:
            message += f"\n\n🤖 <b>AI Insight:</b>\n{cls.escape_html(ai_analysis[:300])}"
        
        return message
    
    @classmethod
    def stats_report(cls, stats: Dict[str, Any]) -> str:
        """Format statistics report"""
        monitor = stats.get("monitor")
        if not monitor:
            return "<b>📊 Statistics</b>\n\n<i>No data available.</i>"
        
        return f"""<b>📊 Statistics: {cls.escape_html(monitor.name)}</b>

📈 <b>24-Hour Overview</b>
├ Checks: <code>{stats.get('checks_24h', 0)}</code>
├ Uptime: <code>{stats.get('uptime_24h', 100)}%</code>
├ Avg Response: <code>{stats.get('avg_response_24h', 0)}ms</code>
└ Incidents: <code>{stats.get('incidents_24h', 0)}</code>

📉 <b>All-Time</b>
├ Total Checks: <code>{monitor.total_checks}</code>
├ Overall Uptime: <code>{monitor.uptime_percentage}%</code>
├ Failures: <code>{monitor.failure_count}</code>
└ Avg Response: <code>{monitor.avg_response_time:.0f}ms</code>
"""
    
    @classmethod
    def help_message(cls) -> str:
        """Format help message"""
        return """<b>🆘 SRE Bot Help</b>

<b>Commands:</b>
/start — Open dashboard
/monitors — List all monitors
/add — Add new monitor
/incidents — View incidents
/stats — View statistics
/settings — Configure preferences
/help — Show this help

<b>Quick Tips:</b>
• Tap any monitor to view details
• Use ⭐ to favorite important monitors
• AI automatically analyzes all incidents
• Alerts are sent via Telegram instantly

<b>Need Support?</b>
Contact: @support
"""
    
    @classmethod
    def welcome_message(cls, first_name: str) -> str:
        """Format welcome message for new users"""
        return f"""<b>Welcome to SRE Bot, {cls.escape_html(first_name)}!</b> 🚀

I'm your AI-powered Site Reliability Engineering assistant. I monitor your infrastructure 24/7 and alert you before problems become outages.

<b>What I can do:</b>
🌐 Monitor websites, APIs, servers
🤖 AI-powered incident analysis
📊 Performance analytics & reports
🚨 Instant Telegram alerts
📄 Auto-generated postmortems

<b>Get Started:</b>
Tap the button below to add your first monitor.

<i>Your infrastructure's guardian angel.</i> ✨
"""
    
    @classmethod
    def empty_state(cls, entity_type: str) -> str:
        """Format empty state messages"""
        messages = {
            "monitors": "<b>📋 Monitors</b>\n\n<i>No monitors yet.</i>\n\nAdd your first monitor to start protecting your infrastructure.",
            "incidents": "<b>🚨 Incidents</b>\n\n<i>No incidents detected.</i>\n\nEverything looks healthy! 🎉",
            "alerts": "<b>🔔 Alerts</b>\n\n<i>No alerts in this period.</i>\n\nQuiet is good. 😊",
            "status_pages": "<b>📄 Status Pages</b>\n\n<i>No status pages configured.</i>\n\nCreate one to share with your customers."
        }
        return messages.get(entity_type, "<b>Empty</b>\n\n<i>No data available.</i>")
    
    @classmethod
    def error_message(cls, error: str, suggestion: Optional[str] = None) -> str:
        """Format error message"""
        message = f"""<b>⚠️ Error</b>

<code>{cls.escape_html(error)}</code>
"""
        if suggestion:
            message += f"\n💡 <b>Suggestion:</b> {cls.escape_html(suggestion)}"
        
        message += "\n\n<i>Try again or contact support if the issue persists.</i>"
        return message
    
    @classmethod
    def success_message(cls, action: str, details: Optional[str] = None) -> str:
        """Format success message"""
        message = f"✅ <b>Success: {cls.escape_html(action)}</b>"
        if details:
            message += f"\n\n{cls.escape_html(details)}"
        return message
