"""
Telegram Command & Message Handlers
Premium user experience with state management
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Dict, Any
import math

from domain import Monitor, MonitorType, MonitorStatus, Incident, IncidentStatus, IncidentSeverity
from application import MonitorService, IncidentService, UserService
from infrastructure import ai_engine, AsyncSessionLocal
from monitoring import monitoring_engine
from telegram.formatters import MessageFormatter
from telegram.keyboards import Keyboards

router = Router()


# FSM States for monitor creation
class AddMonitorStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_url = State()
    waiting_for_name = State()
    waiting_for_interval = State()
    waiting_for_confirm = State()


class EditMonitorStates(StatesGroup):
    waiting_for_field = State()
    waiting_for_value = State()


# ═══════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command - Welcome & Dashboard"""
    async with AsyncSessionLocal() as db:
        user_service = UserService(db)
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name or "User",
            last_name=message.from_user.last_name
        )
        
        welcome_text = MessageFormatter.welcome_message(user.first_name)
        
        await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=Keyboards.main_dashboard()
        )


@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message):
    """Handle /dashboard command"""
    async with AsyncSessionLocal() as db:
        await show_dashboard(message, db)


@router.message(Command("monitors"))
async def cmd_monitors(message: Message):
    """Handle /monitors command"""
    async with AsyncSessionLocal() as db:
        await show_monitors_list(message, db, page=1)


@router.message(Command("incidents"))
async def cmd_incidents(message: Message):
    """Handle /incidents command"""
    async with AsyncSessionLocal() as db:
        await show_incidents_list(message, db, page=1)


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    """Handle /add command - Start monitor creation flow"""
    await state.set_state(AddMonitorStates.waiting_for_type)
    await message.answer(
        "<b>➕ Add New Monitor</b>\n\nSelect the monitor type:",
        parse_mode="HTML",
        reply_markup=Keyboards.add_monitor_type()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    await message.answer(
        MessageFormatter.help_message(),
        parse_mode="HTML",
        reply_markup=Keyboards.back_button("dashboard")
    )


# ═══════════════════════════════════════════════════════════════
# CALLBACK HANDLERS - Dashboard
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "dashboard")
async def cb_dashboard(callback: CallbackQuery):
    """Show main dashboard"""
    await callback.answer()
    async with AsyncSessionLocal() as db:
        await show_dashboard(callback.message, db, edit=True)


async def show_dashboard(message_or_callback, db, edit: bool = False):
    """Render dashboard with live stats"""
    monitor_service = MonitorService(db)
    incident_service = IncidentService(db)
    
    monitors = await monitor_service.get_monitors_by_user(message_or_callback.from_user.id)
    active_incidents = await incident_service.get_active_incidents(message_or_callback.from_user.id)
    
    stats = {
        "total_monitors": len(monitors),
        "operational": sum(1 for m in monitors if m.status == MonitorStatus.OPERATIONAL),
        "down": sum(1 for m in monitors if m.status == MonitorStatus.DOWN),
        "degraded": sum(1 for m in monitors if m.status == MonitorStatus.DEGRADED),
        "active_incidents": len(active_incidents),
        "avg_uptime": round(sum(m.uptime_percentage for m in monitors) / len(monitors), 2) if monitors else 100.0
    }
    
    text = MessageFormatter.dashboard(stats)
    
    if edit and hasattr(message_or_callback, 'edit_text'):
        await message_or_callback.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=Keyboards.main_dashboard()
        )
    else:
        await message_or_callback.answer(
            text,
            parse_mode="HTML",
            reply_markup=Keyboards.main_dashboard()
        )


# ═══════════════════════════════════════════════════════════════
# CALLBACK HANDLERS - Monitors
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("monitors:page:"))
async def cb_monitors_page(callback: CallbackQuery):
    """Handle monitor list pagination"""
    await callback.answer()
    page = int(callback.data.split(":")[-1])
    async with AsyncSessionLocal() as db:
        await show_monitors_list(callback.message, db, page=page, edit=True)


async def show_monitors_list(message, db, page: int = 1, edit: bool = False):
    """Render paginated monitor list"""
    monitor_service = MonitorService(db)
    monitors = await monitor_service.get_monitors_by_user(message.from_user.id)
    
    if not monitors:
        text = MessageFormatter.empty_state("monitors")
        keyboard = Keyboards.back_button("dashboard")
    else:
        per_page = 5
        total_pages = max(1, math.ceil(len(monitors) / per_page))
        page = min(page, total_pages)
        
        start = (page - 1) * per_page
        end = start + per_page
        page_monitors = monitors[start:end]
        
        text = MessageFormatter.monitor_list(page_monitors, page, total_pages)
        keyboard = Keyboards.monitor_list(page_monitors, page, total_pages)
    
    if edit and hasattr(message, 'edit_text'):
        await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("monitor:view:"))
async def cb_monitor_view(callback: CallbackQuery):
    """Show monitor details"""
    await callback.answer()
    monitor_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        monitor = await monitor_service.get_monitor(monitor_id, callback.from_user.id)
        
        if not monitor:
            await callback.message.edit_text(
                MessageFormatter.error_message("Monitor not found"),
                parse_mode="HTML",
                reply_markup=Keyboards.back_button("monitors:page:1")
            )
            return
        
        text = MessageFormatter.monitor_card(monitor, detailed=True)
        keyboard = Keyboards.monitor_detail(monitor.id, monitor.is_active, monitor.is_favorite)
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("monitor:toggle:"))
async def cb_monitor_toggle(callback: CallbackQuery):
    """Toggle monitor active/paused"""
    monitor_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        monitor = await monitor_service.toggle_monitor(monitor_id, callback.from_user.id)
        if monitor:
            status = "paused" if not monitor.is_active else "resumed"
            await callback.answer(f"Monitor {status}")
            
            # Refresh view
            text = MessageFormatter.monitor_card(monitor, detailed=True)
            keyboard = Keyboards.monitor_detail(monitor.id, monitor.is_active, monitor.is_favorite)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.answer("Failed to toggle monitor")


@router.callback_query(F.data.startswith("monitor:favorite:"))
async def cb_monitor_favorite(callback: CallbackQuery):
    """Toggle monitor favorite"""
    monitor_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        monitor = await monitor_service.toggle_favorite(monitor_id, callback.from_user.id)
        if monitor:
            action = "added to favorites" if monitor.is_favorite else "removed from favorites"
            await callback.answer(f"Monitor {action}")
            
            text = MessageFormatter.monitor_card(monitor, detailed=True)
            keyboard = Keyboards.monitor_detail(monitor.id, monitor.is_active, monitor.is_favorite)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.answer("Failed to update favorite")


@router.callback_query(F.data.startswith("monitor:delete:"))
async def cb_monitor_delete(callback: CallbackQuery):
    """Show delete confirmation"""
    await callback.answer("⚠️ Confirm deletion")
    monitor_id = callback.data.split(":")[-1]
    
    await callback.message.edit_text(
        "<b>🗑️ Delete Monitor</b>\n\n<i>Are you sure you want to delete this monitor? This action cannot be undone.</i>",
        parse_mode="HTML",
        reply_markup=Keyboards.confirm_delete(monitor_id)
    )


@router.callback_query(F.data.startswith("monitor:confirm_delete:"))
async def cb_monitor_confirm_delete(callback: CallbackQuery):
    """Confirm and delete monitor"""
    monitor_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        if await monitor_service.delete_monitor(monitor_id, callback.from_user.id):
            await callback.answer("Monitor deleted")
            await show_monitors_list(callback.message, db, page=1, edit=True)
        else:
            await callback.answer("Failed to delete monitor")


@router.callback_query(F.data.startswith("monitor:stats:"))
async def cb_monitor_stats(callback: CallbackQuery):
    """Show monitor statistics"""
    await callback.answer()
    monitor_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        stats = await monitor_service.get_monitor_stats(monitor_id, callback.from_user.id)
        
        if not stats:
            await callback.message.edit_text(
                MessageFormatter.error_message("Monitor not found"),
                parse_mode="HTML",
                reply_markup=Keyboards.back_button(f"monitor:view:{monitor_id}")
            )
            return
        
        text = MessageFormatter.stats_report(stats)
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=Keyboards.back_button(f"monitor:view:{monitor_id}")
        )


@router.callback_query(F.data.startswith("monitor:check:"))
async def cb_monitor_check_now(callback: CallbackQuery, bot: Bot):
    """Run immediate check on monitor"""
    monitor_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        monitor = await monitor_service.get_monitor(monitor_id, callback.from_user.id)
        if not monitor:
            await callback.answer("Monitor not found")
            return
        
        await callback.answer("🔍 Running check...")
        
        try:
            result = await monitoring_engine.check_with_retries(monitor)
            
            status_emoji = "🟢" if result.is_up else "🔴"
            status_text = "UP" if result.is_up else "DOWN"
            
            text = f"""{status_emoji} <b>Check Result: {MessageFormatter.escape_html(monitor.name)}</b>

├ Status: <code>{status_text}</code>
├ Response Time: <code>{result.response_time_ms:.0f}ms</code>
├ Status Code: <code>{result.status_code or 'N/A'}</code>
└ Checked At: <code>{result.completed_at.strftime('%H:%M:%S UTC') if result.completed_at else 'N/A'}</code>
"""
            if result.error_message:
                text += f"\n❌ <b>Error:</b>\n<code>{MessageFormatter.escape_html(result.error_message[:200])}</code>"
            
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=Keyboards.back_button(f"monitor:view:{monitor_id}")
            )
            
        except Exception as e:
            await callback.message.answer(
                MessageFormatter.error_message(str(e), "Check failed unexpectedly"),
                parse_mode="HTML",
                reply_markup=Keyboards.back_button(f"monitor:view:{monitor_id}")
            )


# ═══════════════════════════════════════════════════════════════
# ADD MONITOR FLOW
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("monitor:add"))
async def cb_add_monitor(callback: CallbackQuery, state: FSMContext):
    """Start add monitor flow"""
    await callback.answer()
    
    if callback.data == "monitor:add":
        await state.set_state(AddMonitorStates.waiting_for_type)
        await callback.message.edit_text(
            "<b>➕ Add New Monitor</b>\n\nSelect the type of resource to monitor:",
            parse_mode="HTML",
            reply_markup=Keyboards.add_monitor_type()
        )
    elif callback.data.startswith("monitor:add_type:"):
        monitor_type = callback.data.split(":")[-1]
        await state.update_data(monitor_type=monitor_type)
        await state.set_state(AddMonitorStates.waiting_for_url)
        
        type_hints = {
            "https": "https://example.com",
            "http": "http://example.com",
            "tcp": "tcp://example.com:8080",
            "ping": "ping://example.com",
            "dns": "dns://example.com",
            "ssl": "ssl://example.com",
            "keyword": "https://example.com",
            "api": "https://api.example.com/endpoint"
        }
        
        hint = type_hints.get(monitor_type, "https://example.com")
        await callback.message.edit_text(
            f"<b>➕ Add Monitor</b>  <i>Step 2/4</i>\n\nEnter the URL to monitor:\n\n<i>Example: <code>{hint}</code></i>",
            parse_mode="HTML",
            reply_markup=Keyboards.cancel_button("monitors:page:1")
        )


@router.message(AddMonitorStates.waiting_for_url)
async def process_monitor_url(message: Message, state: FSMContext):
    """Process monitor URL input"""
    url = message.text.strip()
    
    # Basic URL validation
    if not url.startswith(("http://", "https://", "tcp://", "ping://", "dns://", "ssl://")):
        await message.answer(
            MessageFormatter.error_message(
                "Invalid URL format",
                "URL must start with http://, https://, tcp://, ping://, dns://, or ssl://"
            ),
            parse_mode="HTML",
            reply_markup=Keyboards.cancel_button("monitors:page:1")
        )
        return
    
    await state.update_data(url=url)
    await state.set_state(AddMonitorStates.waiting_for_name)
    
    await message.answer(
        "<b>➕ Add Monitor</b>  <i>Step 3/4</i>\n\nEnter a friendly name for this monitor:\n\n<i>Example: <code>My Production API</code></i>",
        parse_mode="HTML",
        reply_markup=Keyboards.cancel_button("monitors:page:1")
    )


@router.message(AddMonitorStates.waiting_for_name)
async def process_monitor_name(message: Message, state: FSMContext):
    """Process monitor name input"""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 200:
        await message.answer(
            MessageFormatter.error_message(
                "Invalid name",
                "Name must be between 2 and 200 characters"
            ),
            parse_mode="HTML",
            reply_markup=Keyboards.cancel_button("monitors:page:1")
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(AddMonitorStates.waiting_for_interval)
    
    await message.answer(
        "<b>➕ Add Monitor</b>  <i>Step 4/4</i>\n\nSelect check interval:",
        parse_mode="HTML",
        reply_markup=Keyboards.add_monitor_interval()
    )


@router.callback_query(AddMonitorStates.waiting_for_interval, F.data.startswith("monitor:interval:"))
async def process_monitor_interval(callback: CallbackQuery, state: FSMContext):
    """Process interval selection and create monitor"""
    await callback.answer("Creating monitor...")
    
    interval = int(callback.data.split(":")[-1])
    data = await state.get_data()
    
    monitor = Monitor(
        name=data["name"],
        url=data["url"],
        monitor_type=MonitorType(data["monitor_type"]),
        interval=interval,
        user_id=callback.from_user.id
    )
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        created = await monitor_service.create_monitor(monitor)
    
    await state.clear()
    
    if created:
        text = MessageFormatter.success_message(
            "Monitor created",
            f"<b>{MessageFormatter.escape_html(created.name)}</b> is now being monitored every <code>{created.interval}</code> seconds."
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=Keyboards.monitor_detail(created.id, True, False)
        )
    else:
        await callback.message.edit_text(
            MessageFormatter.error_message("Failed to create monitor"),
            parse_mode="HTML",
            reply_markup=Keyboards.back_button("monitors:page:1")
        )


# ═══════════════════════════════════════════════════════════════
# CALLBACK HANDLERS - Incidents
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("incidents:page:"))
async def cb_incidents_page(callback: CallbackQuery):
    """Handle incident list pagination"""
    await callback.answer()
    page = int(callback.data.split(":")[-1])
    async with AsyncSessionLocal() as db:
        await show_incidents_list(callback.message, db, page=page, edit=True)


async def show_incidents_list(message, db, page: int = 1, edit: bool = False):
    """Render paginated incident list"""
    incident_service = IncidentService(db)
    incidents = await incident_service.get_incidents_by_user(message.from_user.id)
    
    if not incidents:
        text = MessageFormatter.empty_state("incidents")
        keyboard = Keyboards.back_button("dashboard")
    else:
        per_page = 5
        total_pages = max(1, math.ceil(len(incidents) / per_page))
        page = min(page, total_pages)
        
        start = (page - 1) * per_page
        end = start + per_page
        page_incidents = incidents[start:end]
        
        text = MessageFormatter.incident_list(page_incidents, page, total_pages)
        keyboard = Keyboards.incident_list(page_incidents, page, total_pages)
    
    if edit and hasattr(message, 'edit_text'):
        await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("incident:view:"))
async def cb_incident_view(callback: CallbackQuery):
    """Show incident details"""
    await callback.answer()
    incident_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        incident_service = IncidentService(db)
        incident = await incident_service.get_incident(incident_id, callback.from_user.id)
        
        if not incident:
            await callback.message.edit_text(
                MessageFormatter.error_message("Incident not found"),
                parse_mode="HTML",
                reply_markup=Keyboards.back_button("incidents:page:1")
            )
            return
        
        text = MessageFormatter.incident_card(incident, detailed=True)
        keyboard = Keyboards.incident_detail(incident.id, incident.status.value)
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("incident:resolve:"))
async def cb_incident_resolve(callback: CallbackQuery):
    """Resolve an incident"""
    incident_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        incident_service = IncidentService(db)
        incident = await incident_service.update_incident_status(
            incident_id,
            callback.from_user.id,
            IncidentStatus.RESOLVED,
            "Resolved via Telegram"
        )
        
        if incident:
            await callback.answer("Incident resolved")
            text = MessageFormatter.incident_card(incident, detailed=True)
            keyboard = Keyboards.incident_detail(incident.id, incident.status.value)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.answer("Failed to resolve incident")


@router.callback_query(F.data.startswith("incident:postmortem:"))
async def cb_incident_postmortem(callback: CallbackQuery):
    """Generate AI postmortem"""
    await callback.answer("🤖 Generating postmortem...")
    
    incident_id = callback.data.split(":")[-1]
    
    async with AsyncSessionLocal() as db:
        incident_service = IncidentService(db)
        incident = await incident_service.get_incident(incident_id, callback.from_user.id)
        if not incident:
            await callback.answer("Incident not found")
            return
        
        check_results = await incident_service.get_incident_check_results(
            incident_id, callback.from_user.id
        )
    
    try:
        incident_dict = {
            "id": incident.id,
            "title": incident.title,
            "monitor_name": incident.monitor_name,
            "started_at": incident.started_at.isoformat() if incident.started_at else None,
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            "error_message": incident.error_message,
            "severity": incident.severity.value
        }
        
        postmortem = await ai_engine.generate_postmortem(incident_dict, check_results)
        
        async with AsyncSessionLocal() as db:
            incident_service = IncidentService(db)
            await incident_service.add_postmortem(incident_id, callback.from_user.id, postmortem)
        
        text = f"""<b>📄 Postmortem Report</b>

{MessageFormatter.escape_html(postmortem[:3900])}
"""
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=Keyboards.back_button(f"incident:view:{incident_id}")
        )
        
    except Exception as e:
        await callback.message.answer(
            MessageFormatter.error_message(str(e), "Failed to generate postmortem"),
            parse_mode="HTML",
            reply_markup=Keyboards.back_button(f"incident:view:{incident_id}")
        )


# ═══════════════════════════════════════════════════════════════
# SETTINGS & HELP
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "settings:menu")
async def cb_settings(callback: CallbackQuery):
    """Show settings menu"""
    await callback.answer()
    await callback.message.edit_text(
        "<b>⚙️ Settings</b>\n\nConfigure your SRE Bot preferences:",
        parse_mode="HTML",
        reply_markup=Keyboards.settings_menu()
    )


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    """Show help"""
    await callback.answer()
    await callback.message.edit_text(
        MessageFormatter.help_message(),
        parse_mode="HTML",
        reply_markup=Keyboards.back_button("dashboard")
    )


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    """No-op handler for pagination display buttons"""
    await callback.answer()


@router.callback_query(F.data.startswith("stats:"))
async def cb_stats(callback: CallbackQuery):
    """Show statistics overview"""
    await callback.answer()
    
    async with AsyncSessionLocal() as db:
        monitor_service = MonitorService(db)
        incident_service = IncidentService(db)
        
        monitors = await monitor_service.get_monitors_by_user(callback.from_user.id)
        incident_stats = await incident_service.get_incident_stats(callback.from_user.id)
    
    total_checks = sum(m.total_checks for m in monitors)
    avg_uptime = round(sum(m.uptime_percentage for m in monitors) / len(monitors), 2) if monitors else 100.0
    
    text = f"""<b>📊 Statistics Overview</b>

📈 <b>Monitors</b>
├ Total: <code>{len(monitors)}</code>
├ Total Checks: <code>{total_checks}</code>
└ Average Uptime: <code>{avg_uptime}%</code>

🚨 <b>Incidents (30 days)</b>
├ Total: <code>{incident_stats['total_incidents']}</code>
├ Active: <code>{incident_stats['active_incidents']}</code>
└ Avg Resolution: <code>{incident_stats['avg_resolution_time_seconds']}s</code>

<i>Stats update in real-time as monitors run.</i>
"""
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=Keyboards.back_button("dashboard")
    )

