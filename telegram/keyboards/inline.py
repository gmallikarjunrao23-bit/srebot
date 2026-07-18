"""
Telegram Inline Keyboards
Professional navigation and action keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional

from domain import Monitor, Incident


class Keyboards:
    """Factory for all inline keyboards"""
    
    @staticmethod
    def main_dashboard() -> InlineKeyboardMarkup:
        """Main dashboard navigation"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Monitors", callback_data="monitors:page:1"),
                InlineKeyboardButton(text="🚨 Incidents", callback_data="incidents:page:1")
            ],
            [
                InlineKeyboardButton(text="➕ Add Monitor", callback_data="monitor:add"),
                InlineKeyboardButton(text="📊 Statistics", callback_data="stats:overview")
            ],
            [
                InlineKeyboardButton(text="⚙️ Settings", callback_data="settings:menu"),
                InlineKeyboardButton(text="🆘 Help", callback_data="help")
            ]
        ])
    
    @staticmethod
    def monitor_list(monitors: List[Monitor], page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
        """Monitor list with pagination"""
        buttons = []
        
        # Monitor buttons
        for monitor in monitors:
            status_emoji = "🟢" if monitor.status.value == "operational" else "🔴" if monitor.status.value == "down" else "🟡"
            fav = "⭐" if monitor.is_favorite else ""
            buttons.append([
                InlineKeyboardButton(
                    text=f"{fav}{status_emoji} {monitor.name}",
                    callback_data=f"monitor:view:{monitor.id}"
                )
            ])
        
        # Pagination
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"monitors:page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️ Next", callback_data=f"monitors:page:{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Actions
        buttons.append([
            InlineKeyboardButton(text="➕ Add Monitor", callback_data="monitor:add"),
            InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def monitor_detail(monitor_id: str, is_active: bool = True, is_favorite: bool = False) -> InlineKeyboardMarkup:
        """Monitor detail actions"""
        buttons = []
        
        # Primary actions
        action_row = [
            InlineKeyboardButton(text="📊 Stats", callback_data=f"monitor:stats:{monitor_id}"),
            InlineKeyboardButton(text="📝 Edit", callback_data=f"monitor:edit:{monitor_id}")
        ]
        buttons.append(action_row)
        
        # Toggle states
        toggle_row = [
            InlineKeyboardButton(
                text="⏸️ Pause" if is_active else "▶️ Resume",
                callback_data=f"monitor:toggle:{monitor_id}"
            ),
            InlineKeyboardButton(
                text="⭐ Unfavorite" if is_favorite else "☆ Favorite",
                callback_data=f"monitor:favorite:{monitor_id}"
            )
        ]
        buttons.append(toggle_row)
        
        # Danger zone
        buttons.append([
            InlineKeyboardButton(text="🗑️ Delete", callback_data=f"monitor:delete:{monitor_id}"),
            InlineKeyboardButton(text="🔍 Check Now", callback_data=f"monitor:check:{monitor_id}")
        ])
        
        # Navigation
        buttons.append([
            InlineKeyboardButton(text="◀️ Back to List", callback_data="monitors:page:1"),
            InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def incident_list(incidents: List[Incident], page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
        """Incident list with pagination"""
        buttons = []
        
        for incident in incidents:
            status_emoji = "🔴" if incident.status.value not in ["resolved", "postmortem"] else "✅"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {incident.title[:40]}",
                    callback_data=f"incident:view:{incident.id}"
                )
            ])
        
        # Pagination
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"incidents:page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️ Next", callback_data=f"incidents:page:{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([
            InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def incident_detail(incident_id: str, status: str) -> InlineKeyboardMarkup:
        """Incident detail actions"""
        buttons = []
        
        if status not in ["resolved", "postmortem"]:
            buttons.append([
                InlineKeyboardButton(text="✅ Mark Resolved", callback_data=f"incident:resolve:{incident_id}"),
                InlineKeyboardButton(text="🔍 Investigate", callback_data=f"incident:investigate:{incident_id}")
            ])
        
        buttons.append([
            InlineKeyboardButton(text="📄 Postmortem", callback_data=f"incident:postmortem:{incident_id}"),
            InlineKeyboardButton(text="📊 Details", callback_data=f"incident:details:{incident_id}")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="◀️ Back to Incidents", callback_data="incidents:page:1"),
            InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def add_monitor_type() -> InlineKeyboardMarkup:
        """Monitor type selection"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 HTTPS", callback_data="monitor:add_type:https"),
                InlineKeyboardButton(text="🌐 HTTP", callback_data="monitor:add_type:http")
            ],
            [
                InlineKeyboardButton(text="🔌 TCP", callback_data="monitor:add_type:tcp"),
                InlineKeyboardButton(text="📡 PING", callback_data="monitor:add_type:ping")
            ],
            [
                InlineKeyboardButton(text="🔍 DNS", callback_data="monitor:add_type:dns"),
                InlineKeyboardButton(text="🔒 SSL", callback_data="monitor:add_type:ssl")
            ],
            [
                InlineKeyboardButton(text="🔤 Keyword", callback_data="monitor:add_type:keyword"),
                InlineKeyboardButton(text="🔌 API", callback_data="monitor:add_type:api")
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="monitors:page:1")
            ]
        ])
    
    @staticmethod
    def add_monitor_interval() -> InlineKeyboardMarkup:
        """Check interval selection"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1 min", callback_data="monitor:interval:60"),
                InlineKeyboardButton(text="5 min", callback_data="monitor:interval:300"),
                InlineKeyboardButton(text="10 min", callback_data="monitor:interval:600")
            ],
            [
                InlineKeyboardButton(text="30 min", callback_data="monitor:interval:1800"),
                InlineKeyboardButton(text="1 hour", callback_data="monitor:interval:3600"),
                InlineKeyboardButton(text="6 hours", callback_data="monitor:interval:21600")
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="monitors:page:1")
            ]
        ])
    
    @staticmethod
    def confirm_delete(monitor_id: str) -> InlineKeyboardMarkup:
        """Delete confirmation"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yes, Delete", callback_data=f"monitor:confirm_delete:{monitor_id}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data=f"monitor:view:{monitor_id}")
            ]
        ])
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Settings menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌍 Timezone", callback_data="settings:timezone"),
                InlineKeyboardButton(text="🔔 Notifications", callback_data="settings:notifications")
            ],
            [
                InlineKeyboardButton(text="👤 Profile", callback_data="settings:profile"),
                InlineKeyboardButton(text="📊 Limits", callback_data="settings:limits")
            ],
            [
                InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard")
            ]
        ])
    
    @staticmethod
    def back_button(target: str = "dashboard") -> InlineKeyboardMarkup:
        """Simple back button"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data=target)]
        ])
    
    @staticmethod
    def cancel_button(target: str = "dashboard") -> InlineKeyboardMarkup:
        """Cancel action button"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=target)]
        ])

