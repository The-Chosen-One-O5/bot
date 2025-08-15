import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

class BotDatabase:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Groups table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS groups (
                        chat_id INTEGER PRIMARY KEY,
                        group_name TEXT,
                        timezone TEXT DEFAULT 'UTC',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Scheduled messages table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scheduled_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        message_type TEXT, -- 'daily', 'countdown'
                        schedule_time TEXT, -- HH:MM format
                        message_template TEXT,
                        target_date TEXT, -- For countdown messages
                        title TEXT, -- For countdown messages
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES groups (chat_id)
                    )
                ''')
                
                # Admin users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS group_admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        user_id INTEGER,
                        username TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES groups (chat_id)
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
    
    def add_group(self, chat_id: int, group_name: str, timezone: str = "UTC") -> bool:
        """Add a new group to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO groups (chat_id, group_name, timezone)
                    VALUES (?, ?, ?)
                ''', (chat_id, group_name, timezone))
                conn.commit()
                logging.info(f"Added group {group_name} (ID: {chat_id})")
                return True
        except Exception as e:
            logging.error(f"Error adding group: {e}")
            return False
    
    def add_scheduled_message(self, chat_id: int, message_type: str, schedule_time: str, 
                            message_template: str, target_date: str = None, title: str = None) -> bool:
        """Add a scheduled message"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scheduled_messages 
                    (chat_id, message_type, schedule_time, message_template, target_date, title)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (chat_id, message_type, schedule_time, message_template, target_date, title))
                conn.commit()
                logging.info(f"Added scheduled message for group {chat_id}")
                return True
        except Exception as e:
            logging.error(f"Error adding scheduled message: {e}")
            return False
    
    def get_scheduled_messages(self, chat_id: int = None) -> List[Dict]:
        """Get scheduled messages for a specific group or all groups"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if chat_id:
                    cursor.execute('''
                        SELECT sm.*, g.timezone, g.group_name
                        FROM scheduled_messages sm
                        JOIN groups g ON sm.chat_id = g.chat_id
                        WHERE sm.chat_id = ? AND sm.is_active = 1
                    ''', (chat_id,))
                else:
                    cursor.execute('''
                        SELECT sm.*, g.timezone, g.group_name
                        FROM scheduled_messages sm
                        JOIN groups g ON sm.chat_id = g.chat_id
                        WHERE sm.is_active = 1
                    ''')
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Error getting scheduled messages: {e}")
            return []
    
    def remove_scheduled_message(self, message_id: int, chat_id: int) -> bool:
        """Remove a scheduled message"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE scheduled_messages 
                    SET is_active = 0 
                    WHERE id = ? AND chat_id = ?
                ''', (message_id, chat_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error removing scheduled message: {e}")
            return False
    
    def add_group_admin(self, chat_id: int, user_id: int, username: str = None) -> bool:
        """Add a group admin"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO group_admins (chat_id, user_id, username)
                    VALUES (?, ?, ?)
                ''', (chat_id, user_id, username))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding group admin: {e}")
            return False
    
    def is_group_admin(self, chat_id: int, user_id: int) -> bool:
        """Check if user is a group admin"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 1 FROM group_admins 
                    WHERE chat_id = ? AND user_id = ?
                ''', (chat_id, user_id))
                return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"Error checking admin status: {e}")
            return False
    
    def get_group_timezone(self, chat_id: int) -> str:
        """Get timezone for a group"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT timezone FROM groups WHERE chat_id = ?', (chat_id,))
                result = cursor.fetchone()
                return result[0] if result else "UTC"
        except Exception as e:
            logging.error(f"Error getting group timezone: {e}")
            return "UTC"
    
    def update_group_timezone(self, chat_id: int, timezone: str) -> bool:
        """Update group timezone"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE groups SET timezone = ? WHERE chat_id = ?
                ''', (timezone, chat_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating group timezone: {e}")
            return False