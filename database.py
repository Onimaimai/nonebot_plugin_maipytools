import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime
from .config import plugin_config
from .models import UserData

class Database:
    def __init__(self):
        self.data_dir = Path(plugin_config.maimai_data_path)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "user_data.db"
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id TEXT PRIMARY KEY,
                    credentials TEXT,
                    import_token TEXT,
                    last_updated TIMESTAMP
                )
            ''')
            conn.commit()

    def get_user_data(self, user_id: str) -> Optional[UserData]:
        """获取用户数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return UserData(
                    user_id=row[0],
                    credentials=row[1],
                    import_token=row[2],
                    last_updated=datetime.fromisoformat(row[3])
                )
            return None

    def update_user_data(self, user_id: str, **kwargs) -> UserData:
        """更新用户数据"""
        user_data = self.get_user_data(user_id)
        if not user_data:
            user_data = UserData(user_id=user_id)
        
        for key, value in kwargs.items():
            setattr(user_data, key, value)
        user_data.last_updated = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_data (user_id, credentials, import_token, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (
                user_data.user_id,
                user_data.credentials,
                user_data.import_token,
                user_data.last_updated.isoformat()
            ))
            conn.commit()
        
        return user_data

    def get_all_users(self) -> dict:
        """获取所有用户数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_data')
            rows = cursor.fetchall()
            
            return {
                row[0]: UserData(
                    user_id=row[0],
                    credentials=row[1],
                    import_token=row[2],
                    last_updated=datetime.fromisoformat(row[3])
                )
                for row in rows
            } 