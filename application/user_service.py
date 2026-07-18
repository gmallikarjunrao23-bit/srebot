"""
User Service - Business logic for user management
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import User, UserRole
from infrastructure import DBUser, UserRoleEnum


class UserService:
    """Service for user operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: str = "",
        last_name: Optional[str] = None
    ) -> User:
        """Get existing user or create new one"""
        result = await self.db.execute(
            select(DBUser).where(DBUser.id == telegram_id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            # Update user info
            if username and db_user.username != username:
                db_user.username = username
            if first_name and db_user.first_name != first_name:
                db_user.first_name = first_name
            if last_name and db_user.last_name != last_name:
                db_user.last_name = last_name
            await self.db.commit()
            await self.db.refresh(db_user)
            return self._to_domain(db_user)
        
        # Create new user
        db_user = DBUser(
            id=telegram_id,
            username=username,
            first_name=first_name or "User",
            last_name=last_name,
            role=UserRoleEnum.OWNER,
            is_active=True
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return self._to_domain(db_user)
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        result = await self.db.execute(
            select(DBUser).where(DBUser.id == telegram_id)
        )
        db_user = result.scalar_one_or_none()
        return self._to_domain(db_user) if db_user else None
    
    async def update_user_preferences(
        self,
        telegram_id: int,
        preferences: Dict[str, Any]
    ) -> Optional[User]:
        """Update user preferences"""
        result = await self.db.execute(
            select(DBUser).where(DBUser.id == telegram_id)
        )
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None
        
        # Merge preferences
        current = db_user.notification_preferences or {}
        current.update(preferences)
        db_user.notification_preferences = current
        
        await self.db.commit()
        await self.db.refresh(db_user)
        return self._to_domain(db_user)
    
    async def update_timezone(self, telegram_id: int, timezone: str) -> Optional[User]:
        """Update user timezone"""
        result = await self.db.execute(
            select(DBUser).where(DBUser.id == telegram_id)
        )
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None
        
        db_user.timezone = timezone
        await self.db.commit()
        await self.db.refresh(db_user)
        return self._to_domain(db_user)
    
    async def can_create_monitor(self, telegram_id: int) -> bool:
        """Check if user can create more monitors"""
        user = await self.get_user(telegram_id)
        if not user:
            return False
        
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(DBUser.monitors)).where(DBUser.id == telegram_id)
        )
        monitor_count = result.scalar() or 0
        
        return monitor_count < user.max_monitors
    
    def _to_domain(self, db_user: DBUser) -> User:
        """Convert DB model to domain model"""
        return User(
            id=db_user.id,
            username=db_user.username,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            role=UserRole(db_user.role.value),
            is_active=db_user.is_active,
            timezone=db_user.timezone,
            language=db_user.language,
            notification_preferences=db_user.notification_preferences or {},
            max_monitors=db_user.max_monitors,
            max_teams=db_user.max_teams,
            max_status_pages=db_user.max_status_pages,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )

