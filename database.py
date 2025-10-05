#!/usr/bin/env python3

import aiosqlite
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import os

class Database:
    def __init__(self, db_path: str = "onboarding_tracker.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Initialize the database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Role tracking table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS role_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    role_id INTEGER NOT NULL,
                    role_name TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK (event_type IN ('added', 'removed')),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    guild_id INTEGER NOT NULL,
                    source_channel TEXT,
                    source_type TEXT DEFAULT 'unknown'
                )
            ''')
            
            # User tracking table for additional metadata
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_metadata (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    join_date DATETIME,
                    first_role_date DATETIME,
                    total_roles_gained INTEGER DEFAULT 0,
                    total_roles_lost INTEGER DEFAULT 0,
                    last_activity DATETIME,
                    guild_id INTEGER NOT NULL
                )
            ''')
            
            # Tracked roles configuration
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tracked_roles (
                    role_id INTEGER PRIMARY KEY,
                    role_name TEXT NOT NULL,
                    guild_id INTEGER NOT NULL,
                    category TEXT DEFAULT 'onboarding',
                    is_active BOOLEAN DEFAULT TRUE,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Member join tracking table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS member_joins (
                    user_id INTEGER,
                    guild_id INTEGER,
                    username TEXT NOT NULL,
                    join_time DATETIME NOT NULL,
                    leave_time DATETIME,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            # Onboarding completion tracking
            await db.execute('''
                CREATE TABLE IF NOT EXISTS onboarding_completions (
                    user_id INTEGER,
                    guild_id INTEGER,
                    completion_time DATETIME NOT NULL,
                    roles_gained TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            # Guild settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER,
                    setting_key TEXT,
                    setting_value TEXT,
                    PRIMARY KEY (guild_id, setting_key)
                )
            ''')
            
            # Guild enabled/disabled status
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_status (
                    guild_id INTEGER PRIMARY KEY,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    enabled_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    disabled_date DATETIME
                )
            ''')
            
            # Add source_info column to role_events if it doesn't exist
            try:
                await db.execute('ALTER TABLE role_events ADD COLUMN source_info TEXT DEFAULT "{}"')
            except aiosqlite.OperationalError:
                pass  # Column already exists
            
            await db.commit()
    
    async def add_role_event(self, user_id: int, username: str, role_id: int, 
                           role_name: str, event_type: str, guild_id: int,
                           source_channel: str = None, source_type: str = 'unknown',
                           source_info: dict = None):
        """Add a role event to the database"""
        import json
        source_info_json = json.dumps(source_info or {})
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO role_events 
                (user_id, username, role_id, role_name, event_type, guild_id, source_channel, source_type, source_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, role_id, role_name, event_type, guild_id, source_channel, source_type, source_info_json))
            
            # Update user metadata
            await self._update_user_metadata(db, user_id, username, guild_id, event_type)
            await db.commit()
    
    async def _update_user_metadata(self, db, user_id: int, username: str, 
                                  guild_id: int, event_type: str):
        """Update user metadata table"""
        # Check if user exists
        async with db.execute(
            'SELECT user_id FROM user_metadata WHERE user_id = ?', (user_id,)
        ) as cursor:
            exists = await cursor.fetchone()
        
        if not exists:
            # Create new user record
            await db.execute('''
                INSERT INTO user_metadata (user_id, username, guild_id, last_activity)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, guild_id, datetime.now(timezone.utc)))
        
        # Update counters and last activity
        if event_type == 'added':
            await db.execute('''
                UPDATE user_metadata 
                SET total_roles_gained = total_roles_gained + 1,
                    last_activity = ?,
                    username = ?
                WHERE user_id = ?
            ''', (datetime.now(timezone.utc), username, user_id))
        elif event_type == 'removed':
            await db.execute('''
                UPDATE user_metadata 
                SET total_roles_lost = total_roles_lost + 1,
                    last_activity = ?,
                    username = ?
                WHERE user_id = ?
            ''', (datetime.now(timezone.utc), username, user_id))
    
    async def add_tracked_role(self, role_id: int, role_name: str, guild_id: int, 
                             category: str = 'onboarding'):
        """Add a role to track"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO tracked_roles (role_id, role_name, guild_id, category)
                VALUES (?, ?, ?, ?)
            ''', (role_id, role_name, guild_id, category))
            await db.commit()
    
    async def remove_tracked_role(self, role_id: int):
        """Remove a role from tracking"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE tracked_roles SET is_active = FALSE WHERE role_id = ?', 
                (role_id,)
            )
            await db.commit()
    
    async def get_tracked_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all tracked roles for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT role_id, role_name, category, added_date
                FROM tracked_roles 
                WHERE guild_id = ? AND is_active = TRUE
            ''', (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        'role_id': row[0],
                        'role_name': row[1], 
                        'category': row[2],
                        'added_date': row[3]
                    }
                    for row in rows
                ]
    
    async def is_role_tracked(self, role_id: int) -> bool:
        """Check if a role is being tracked"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT 1 FROM tracked_roles WHERE role_id = ? AND is_active = TRUE', 
                (role_id,)
            ) as cursor:
                return await cursor.fetchone() is not None
    
    async def get_role_events(self, guild_id: int, start_date: datetime = None, 
                            end_date: datetime = None) -> List[Dict[str, Any]]:
        """Get role events within a date range"""
        query = '''
            SELECT re.*, tr.category
            FROM role_events re
            LEFT JOIN tracked_roles tr ON re.role_id = tr.role_id
            WHERE re.guild_id = ?
        '''
        params = [guild_id]
        
        if start_date:
            query += ' AND re.timestamp >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND re.timestamp <= ?'
            params.append(end_date)
        
        query += ' ORDER BY re.timestamp DESC'
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM user_metadata WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def get_summary_stats(self, guild_id: int, start_date: datetime = None,
                              end_date: datetime = None) -> Dict[str, Any]:
        """Get summary statistics for the guild"""
        query_conditions = 'WHERE guild_id = ?'
        params = [guild_id]
        
        if start_date:
            query_conditions += ' AND timestamp >= ?'
            params.append(start_date)
        
        if end_date:
            query_conditions += ' AND timestamp <= ?'
            params.append(end_date)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Total events
            async with db.execute(f'''
                SELECT 
                    COUNT(*) as total_events,
                    COALESCE(SUM(CASE WHEN event_type = 'added' THEN 1 ELSE 0 END), 0) as roles_added,
                    COALESCE(SUM(CASE WHEN event_type = 'removed' THEN 1 ELSE 0 END), 0) as roles_removed,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT role_id) as roles_affected
                FROM role_events {query_conditions}
            ''', params) as cursor:
                row = await cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                stats = dict(zip(columns, row))
            
            # Role breakdown
            async with db.execute(f'''
                SELECT 
                    role_name,
                    COALESCE(SUM(CASE WHEN event_type = 'added' THEN 1 ELSE 0 END), 0) as added_count,
                    COALESCE(SUM(CASE WHEN event_type = 'removed' THEN 1 ELSE 0 END), 0) as removed_count
                FROM role_events {query_conditions}
                GROUP BY role_id, role_name
                ORDER BY added_count DESC
            ''', params) as cursor:
                role_breakdown = await cursor.fetchall()
                stats['role_breakdown'] = [
                    {
                        'role_name': row[0],
                        'added': row[1],
                        'removed': row[2],
                        'net_change': row[1] - row[2]
                    }
                    for row in role_breakdown
                ]
            
            return stats
    
    async def record_member_join(self, user_id: int, username: str, guild_id: int, join_time: datetime):
        """Record when a member joins the server"""
        timestamp = join_time.isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO member_joins 
                (user_id, username, guild_id, join_time)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, guild_id, timestamp))
            await db.commit()
    
    async def record_member_leave(self, user_id: int, guild_id: int, leave_time: datetime):
        """Record when a member leaves the server"""
        timestamp = leave_time.isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE member_joins 
                SET leave_time = ? 
                WHERE user_id = ? AND guild_id = ?
            """, (timestamp, user_id, guild_id))
            await db.commit()
    
    async def mark_onboarding_complete(self, user_id: int, guild_id: int, completion_time: datetime, roles_gained: list):
        """Mark a user's onboarding as complete"""
        import json
        timestamp = completion_time.isoformat()
        roles_json = json.dumps(roles_gained)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO onboarding_completions 
                (user_id, guild_id, completion_time, roles_gained)
                VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, timestamp, roles_json))
            await db.commit()
    
    async def get_guild_settings(self, guild_id: int = None):
        """Get guild-specific settings"""
        if not guild_id:
            return {}
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT setting_key, setting_value FROM guild_settings 
                WHERE guild_id = ?
            """, (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                import json
                return {row[0]: json.loads(row[1]) for row in rows}
    
    async def set_guild_setting(self, guild_id: int, key: str, value):
        """Set a guild-specific setting"""
        import json
        value_json = json.dumps(value)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO guild_settings 
                (guild_id, setting_key, setting_value)
                VALUES (?, ?, ?)
            """, (guild_id, key, value_json))
            await db.commit()
    
    async def update_guild_settings(self, guild_id: int, settings: dict):
        """Update multiple guild settings at once"""
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in settings.items():
                await self.set_guild_setting(guild_id, key, value)
    
    async def enable_guild(self, guild_id: int):
        """Enable tracking for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO guild_status (guild_id, is_enabled, enabled_date)
                VALUES (?, TRUE, ?)
            ''', (guild_id, datetime.now(timezone.utc)))
            await db.commit()
    
    async def disable_guild(self, guild_id: int):
        """Disable tracking for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO guild_status (guild_id, is_enabled, disabled_date)
                VALUES (?, FALSE, ?)
            ''', (guild_id, datetime.now(timezone.utc)))
            await db.commit()
    
    async def is_guild_enabled(self, guild_id: int) -> bool:
        """Check if tracking is enabled for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT is_enabled FROM guild_status WHERE guild_id = ?', 
                (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else True  # Default to enabled if not set
    
    async def get_guild_status(self, guild_id: int) -> dict:
        """Get detailed status information for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT is_enabled, enabled_date, disabled_date 
                FROM guild_status WHERE guild_id = ?
            ''', (guild_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        'is_enabled': result[0],
                        'enabled_date': result[1],
                        'disabled_date': result[2]
                    }
                return {'is_enabled': True, 'enabled_date': None, 'disabled_date': None}
