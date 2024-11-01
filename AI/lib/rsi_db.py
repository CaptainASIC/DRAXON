import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger('DraXon_AI')

class RSIDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create members table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rsi_members (
                        discord_id TEXT PRIMARY KEY,
                        handle TEXT UNIQUE,
                        sid TEXT,
                        display_name TEXT,
                        enlisted TEXT,
                        org_status TEXT,
                        org_rank TEXT,
                        org_stars INTEGER,
                        verified BOOLEAN,
                        last_updated TEXT,
                        raw_data TEXT
                    )
                ''')

                # Create role history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS role_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id TEXT,
                        old_rank TEXT,
                        new_rank TEXT,
                        reason TEXT,
                        timestamp TEXT,
                        FOREIGN KEY (discord_id) REFERENCES rsi_members(discord_id)
                    )
                ''')

                # Create verification history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS verification_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id TEXT,
                        action TEXT,
                        status BOOLEAN,
                        timestamp TEXT,
                        details TEXT,
                        FOREIGN KEY (discord_id) REFERENCES rsi_members(discord_id)
                    )
                ''')
                
                conn.commit()
                logger.info("RSI database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    async def store_member(self, discord_id: str, data: Dict) -> bool:
        """Store member RSI data in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if member exists
                cursor.execute('SELECT * FROM rsi_members WHERE discord_id = ?', (discord_id,))
                existing = cursor.fetchone()
                
                # Store essential data in columns and full data as JSON
                cursor.execute('''
                    INSERT OR REPLACE INTO rsi_members (
                        discord_id, handle, sid, display_name, enlisted,
                        org_status, org_rank, org_stars, verified,
                        last_updated, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    discord_id,
                    data.get('handle'),
                    data.get('sid'),
                    data.get('display'),
                    data.get('enlisted'),
                    data.get('org_status'),
                    data.get('org_rank'),
                    data.get('org_stars', 0),
                    data.get('verified', False),
                    datetime.utcnow().isoformat(),
                    json.dumps(data)
                ))

                # Log verification attempt
                cursor.execute('''
                    INSERT INTO verification_history (
                        discord_id, action, status, timestamp, details
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    discord_id,
                    'update' if existing else 'create',
                    True,
                    datetime.utcnow().isoformat(),
                    json.dumps({
                        'handle': data.get('handle'),
                        'org_status': data.get('org_status'),
                        'verified': data.get('verified')
                    })
                ))
                
                conn.commit()
                logger.info(f"Successfully stored data for member {discord_id}")
                return True
        except Exception as e:
            logger.error(f"Error storing member data: {e}")
            return False

    def log_role_change(self, discord_id: str, old_rank: str, new_rank: str, reason: str) -> bool:
        """Log a role change in the history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO role_history (
                        discord_id, old_rank, new_rank, reason, timestamp
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    discord_id,
                    old_rank,
                    new_rank,
                    reason,
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging role change: {e}")
            return False

    def get_member_by_discord_id(self, discord_id: str) -> Optional[Dict]:
        """Retrieve member data by Discord ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT raw_data FROM rsi_members WHERE discord_id = ?', (discord_id,))
                result = cursor.fetchone()
                
                if result:
                    return json.loads(result[0])
                return None
        except Exception as e:
            logger.error(f"Error retrieving member data: {e}")
            return None

    def get_member_by_handle(self, handle: str) -> Optional[Dict]:
        """Retrieve member data by RSI handle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT raw_data FROM rsi_members WHERE handle = ?', (handle,))
                result = cursor.fetchone()
                
                if result:
                    return json.loads(result[0])
                return None
        except Exception as e:
            logger.error(f"Error retrieving member data: {e}")
            return None

    def get_all_members(self) -> List[Dict]:
        """Retrieve all member data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT raw_data FROM rsi_members')
                results = cursor.fetchall()
                
                return [json.loads(row[0]) for row in results]
        except Exception as e:
            logger.error(f"Error retrieving all members: {e}")
            return []

    def search_members(self, query: Dict[str, any]) -> List[Dict]:
        """Search members based on criteria"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build WHERE clause from query
                where_clauses = []
                params = []
                for key, value in query.items():
                    if key in ['discord_id', 'handle', 'sid', 'org_status', 'org_rank']:
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
                
                if where_clauses:
                    sql = f"SELECT raw_data FROM rsi_members WHERE {' AND '.join(where_clauses)}"
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    return [json.loads(row[0]) for row in results]
                
                return []
        except Exception as e:
            logger.error(f"Error searching members: {e}")
            return []

    def get_role_history(self, discord_id: str) -> List[Dict]:
        """Get role change history for a member"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT old_rank, new_rank, reason, timestamp
                    FROM role_history
                    WHERE discord_id = ?
                    ORDER BY timestamp DESC
                ''', (discord_id,))
                
                results = cursor.fetchall()
                return [{
                    'old_rank': row[0],
                    'new_rank': row[1],
                    'reason': row[2],
                    'timestamp': row[3]
                } for row in results]
        except Exception as e:
            logger.error(f"Error retrieving role history: {e}")
            return []

    def get_verification_history(self, discord_id: str) -> List[Dict]:
        """Get verification history for a member"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT action, status, timestamp, details
                    FROM verification_history
                    WHERE discord_id = ?
                    ORDER BY timestamp DESC
                ''', (discord_id,))
                
                results = cursor.fetchall()
                return [{
                    'action': row[0],
                    'status': bool(row[1]),
                    'timestamp': row[2],
                    'details': json.loads(row[3])
                } for row in results]
        except Exception as e:
            logger.error(f"Error retrieving verification history: {e}")
            return []

    def cleanup_old_records(self, days: int = 30) -> bool:
        """Clean up old history records"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cutoff_date = (datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
                
                # Clean up old history records
                cursor.execute('''
                    DELETE FROM role_history 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                cursor.execute('''
                    DELETE FROM verification_history 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
            return False

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                stats = {}
                
                # Get member counts
                cursor.execute('SELECT COUNT(*) FROM rsi_members')
                stats['total_members'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM rsi_members WHERE verified = 1')
                stats['verified_members'] = cursor.fetchone()[0]
                
                # Get org status breakdown
                cursor.execute('''
                    SELECT org_status, COUNT(*) 
                    FROM rsi_members 
                    GROUP BY org_status
                ''')
                stats['org_status_breakdown'] = dict(cursor.fetchall())
                
                # Get history counts
                cursor.execute('SELECT COUNT(*) FROM role_history')
                stats['role_changes'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM verification_history')
                stats['verification_events'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}