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
    """
    
    # Status emojis
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
    def escape_markdown(text: str) -> str:
        """Escape MarkdownV2 special characters"""
        if not text:
            return ""
        chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in chars:
            text = text.replace(char, f"\\{char}")
        return text
    
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
        
        message = f"""*🚀 SRE Bot — Command Center*

*{health_color} System Health: {avg_uptime}%*

📊 *Overview*
├ Monitors: `{total}`
├ 🟢 Operational: `{operational}`
├ 🟡 Degraded: `{degraded}`
├ 🔴 Down: `{down}`
└ 🚨 Active Incidents: `{active_incidents}`

⏱ _Last updated: {datetime.utcnow().strftime('%H:%M:%S UTC')}_

💡 *Quick Actions:* Use the buttons below to navigate"""
        
        return message
    
    @classmethod
    def monitor_card(cls, monitor: Monitor, detailed: bool = False) -> str:
        """Format a monitor as a beautiful card"""
        status_emoji = cls.STATUS_EMOJIS.get(monitor.status, "⚪")
        fav = "⭐ " if monitor.is_favorite else ""
        
        response_time = f"{monitor.avg_response_time:.0f}ms" if monitor.avg_response_time > 0 else "N/A"
        last_check = monitor.last_check_at.strftime("%H:%M:%S") if monitor.last_check_at else "Never"
        
        message = f"""{fav}*{status_emoji} {cls.escape_markdown(monitor.name)}*

🔗 `{cls.escape_markdown(monitor.url)}`
├ Type: `{monitor.monitor_type.value.upper()}`
├ Status: `{monitor.status.value.upper()}`
├ Uptime: `{monitor.uptime_percentage}%`
├ Avg Response: `{response_time}`
├ Interval: `{monitor.interval}s`
├ Region: `{monitor.region}`
└ Last Check: `{last_check}`
"""
        
        if detailed:
            message += f"""
📋 *Configuration*
├ Timeout: `{monitor.timeout}s`
├ Retries: `{monitor.retries}`
├ Expected Codes: `{', '.join(map(str, monitor.expected_status_codes))}`
├ Environment: `{monitor.environment}`
├ Priority: `{monitor.priority}`
└ Tags: `{', '.join(monitor.tags) if monitor.tags else 'None'}`
"""
        
        if monitor.description:
            message += f"\n📝 {cls.escape_markdown(monitor.description)}"
        
        return message
    
    @classmethod
    def monitor_list(cls, monitors: List[Monitor], page: int = 1, total_pages: int = 1) -> str:
        """Format monitor list"""
        if not monitors:
            return "*📋 Your Monitors*\n\n_No monitors configured yet._\n\nTap ➕ Add Monitor to get started."
        
        message = f"*📋 Your Monitors*  _(Page {page}/{total_pages})_\n\n"
        
        for monitor in monitors:
            status_emoji = cls.STATUS_EMOJIS.get(monitor.status, "⚪")
            fav = "⭐" if monitor.is_favorite else ""
            rt = f"{monitor.avg_response_time:.0f}ms" if monitor.avg_response_time > 0 else "N/A"
            message += f"{fav}{status_emoji} *{cls.escape_markdown(monitor.name)}*\n   └ `{monitor.uptime_percentage}%` · `{rt}` · `{monitor.monitor_type.value.upper()}`\n\n"
        
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
        
        message = f"""{severity_emoji} *INCIDENT: {cls.escape_markdown(incident.title)}*

📍 *Details*
├ Monitor: `{cls.escape_markdown(incident.monitor_name)}`
├ Severity: `{incident.severity.value.upper()}`
├ Status: `{incident.status.value.upper()}`
├ Duration: `{duration}`
└ Started: `{incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`
"""
        
        if incident.error_message:
            message += f"\n❌ *Error:*\n`{cls.escape_markdown(incident.error_message[:200])}`"
        
        if incident.ai_analysis:
            message += f"\n\n🤖 *AI Analysis:*\n{cls.escape_markdown(incident.ai_analysis[:400])}"
        
        if incident.ai_recommendations:
            message += "\n\n💡 *AI Recommendations:*\n"
            for rec in incident.ai_recommendations[:3]:
                message += f"• {cls.escape_markdown(rec)}\n"
        
        if detailed and incident.resolution_notes:
            message += f"\n✅ *Resolution:*\n{cls.escape_markdown(incident.resolution_notes)}"
        
        if detailed and incident.postmortem:
            message += f"\n\n📄 *Postmortem:*\n{cls.escape_markdown(incident.postmortem[:500])}"
        
        return message
    
    @classmethod
    def incident_list(cls, incidents: List[Incident], page: int = 1, total_pages: int = 1) -> str:
        """Format incident list"""
        if not incidents:
            return "*🚨 Incidents*\n\n_No incidents found._\n\nEverything looks healthy! 🎉"
        
        message = f"*🚨 Incidents*  _(Page {page}/{total_pages})_\n\n"
        
        for incident in incidents:
            severity_emoji = cls.SEVERITY_EMOJIS.get(incident.severity, "⚪")
            status = "🔴" if incident.status not in ["resolved", "postmortem"] else "✅"
            message += f"{status}{severity_emoji} *{cls.escape_markdown(incident.title)}*\n   └ `{incident.status.value}` · `{incident.severity.value}` · `{incident.monitor_name}`\n\n"
        
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
        
        message = f"""{emoji} *{title}*

📍 *{cls.escape_markdown(monitor_name)}*
├ Status: `{status.upper()}`
├ Response Time: `{response_time:.0f}ms`
└ Time: `{datetime.utcnow().strftime('%H:%M:%S UTC')}`
"""
        
        if error:
            message += f"\n❌ *Error:*\n`{cls.escape_markdown(error[:200])}`"
        
        if ai_analysis:
            message += f"\n\n🤖 *AI Insight:*\n{cls.escape_markdown(ai_analysis[:300])}"
        
        return message
    
    @classmethod
    def stats_report(cls, stats: Dict[str, Any]) -> str:
        """Format statistics report"""
        monitor = stats.get("monitor")
        if not monitor:
            return "*📊 Statistics*\n\n_No data available._"
        
        message = f"""*📊 Statistics: {cls.escape_markdown(monitor.name)}*

📈 *24-Hour Overview*
├ Checks: `{stats.get('checks_24h', 0)}`
├ Uptime: `{stats.get('uptime_24h', 100)}%`
├ Avg Response: `{stats.get('avg_response_24h', 0)}ms`
└ Incidents: `{stats.get('incidents_24h', 0)}`

📉 *All-Time*
├ Total Checks: `{monitor.total_checks}`
├ Overall Uptime: `{monitor.uptime_percentage}%`
├ Failures: `{monitor.failure_count}`
└ Avg Response: `{monitor.avg_response_time:.0f}ms`
"""
        
        return message
    
    @classmethod
    def help_message(cls) -> str:
        """Format help message"""
        return """*🆘 SRE Bot Help*

*Commands:*
/start — Open dashboard
/monitors — List all monitors
/add — Add new monitor
/incidents — View incidents
/stats — View statistics
/settings — Configure preferences
/help — Show this help

*Quick Tips:*
• Tap any monitor to view details
• Use ⭐ to favorite important monitors
• AI automatically analyzes all incidents
• Alerts are sent via Telegram instantly

*Need Support?*
Contact: @support
"""
    
    @classmethod
    def welcome_message(cls, first_name: str) -> str:
        """Format welcome message for new users"""
        return f"""*Welcome to SRE Bot, {cls.escape_markdown(first_name)}!* 🚀

I'm your AI-powered Site Reliability Engineering assistant. I monitor your infrastructure 24/7 and alert you before problems become outages.

*What I can do:*
🌐 Monitor websites, APIs, servers
🤖 AI-powered incident analysis
📊 Performance analytics & reports
🚨 Instant Telegram alerts
📄 Auto-generated postmortems

*Get Started:*
Tap the button below to add your first monitor.

_Your infrastructure's guardian angel._ ✨
"""
    
    @classmethod
    def empty_state(cls, entity_type: str) -> str:
        """Format empty state messages"""
        messages = {
            "monitors": "*📋 Monitors*\n\n_No monitors yet._\n\nAdd your first monitor to start protecting your infrastructure.",
            "incidents": "*🚨 Incidents*\n\n_No incidents detected._\n\nEverything is running smoothly! 🎉",
            "alerts": "*🔔 Alerts*\n\n_No alerts in this period._\n\nQuiet is good. 😊",
            "status_pages": "*📄 Status Pages*\n\n_No status pages configured._\n\nCreate one to share with your customers."
        }
        return messages.get(entity_type, "*Empty*\n\n_No data available._")
    
    @classmethod
    def error_message(cls, error: str, suggestion: Optional[str] = None) -> str:
        """Format error message"""
        message = f"""*⚠️ Error*

`{cls.escape_markdown(error)}`
"""
        if suggestion:
            message += f"\n💡 *Suggestion:* {cls.escape_markdown(suggestion)}"
        
        message += "\n\n_Try again or contact support if the issue persists._"
        return message
    
    @classmethod
    def success_message(cls, action: str, details: Optional[str] = None) -> str:
        """Format success message"""
        message = f"✅ *Success: {cls.escape_markdown(action)}*"
        if details:
            message += f"\n\n{cls.escape_markdown(details)}"
        return message

