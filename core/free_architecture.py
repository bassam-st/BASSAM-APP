"""
الخريطة المعمارية المجانية لبسام الذكي
Free-First Architecture للحصول على أقصى استفادة من الخدمات المجانية
"""

import os
import sqlite3
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import diskcache as dc

@dataclass
class FreeResourceLimits:
    """حدود الموارد المجانية"""
    # Render.com Free Tier
    render_build_minutes: int = 500  # دقيقة/شهر
    render_bandwidth: int = 100  # GB/شهر
    render_sleep_after: int = 15  # دقيقة عدم نشاط
    
    # Gemini Free Tier
    gemini_requests_per_minute: int = 15
    gemini_requests_per_day: int = 1500
    gemini_tokens_per_minute: int = 32000
    
    # DiskCache Limits
    disk_cache_size: int = 100  # MB
    cache_retention_days: int = 7
    
    # Database Limits
    db_max_connections: int = 5
    db_query_timeout: int = 10  # ثانية

class FreeArchitectureManager:
    """مدير الخريطة المعمارية المجانية"""
    
    def __init__(self):
        self.limits = FreeResourceLimits()
        self.cache = dc.Cache('./cache', size_limit=self.limits.disk_cache_size * 1024 * 1024)
        self.usage_stats = self._load_usage_stats()
        self.db_path = './data/bassam_free.db'
        self._setup_database()
    
    def _setup_database(self):
        """إعداد قاعدة بيانات SQLite المجانية"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    queries_count INTEGER DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    service TEXT,
                    operation TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    response_time REAL,
                    success BOOLEAN
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cached_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT UNIQUE,
                    query_text TEXT,
                    response_data TEXT,
                    model_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            ''')
    
    def _load_usage_stats(self) -> Dict[str, Any]:
        """تحميل إحصائيات الاستخدام"""
        stats_file = './data/usage_stats.json'
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            'daily_limits': {
                'gemini_requests': 0,
                'gemini_tokens': 0,
                'last_reset': time.strftime('%Y-%m-%d')
            },
            'monthly_stats': {
                'render_build_minutes': 0,
                'render_bandwidth_gb': 0,
                'last_reset': time.strftime('%Y-%m')
            }
        }
    
    def _save_usage_stats(self):
        """حفظ إحصائيات الاستخدام"""
        os.makedirs('./data', exist_ok=True)
        with open('./data/usage_stats.json', 'w', encoding='utf-8') as f:
            json.dump(self.usage_stats, f, ensure_ascii=False, indent=2)
    
    def check_rate_limits(self, service: str) -> Dict[str, Any]:
        """فحص حدود الاستخدام"""
        current_date = time.strftime('%Y-%m-%d')
        
        # إعادة تعيين الحدود اليومية
        if self.usage_stats['daily_limits']['last_reset'] != current_date:
            self.usage_stats['daily_limits'] = {
                'gemini_requests': 0,
                'gemini_tokens': 0,
                'last_reset': current_date
            }
            self._save_usage_stats()
        
        if service == 'gemini':
            requests_used = self.usage_stats['daily_limits']['gemini_requests']
            tokens_used = self.usage_stats['daily_limits']['gemini_tokens']
            
            return {
                'allowed': requests_used < self.limits.gemini_requests_per_day,
                'requests_remaining': max(0, self.limits.gemini_requests_per_day - requests_used),
                'tokens_remaining': max(0, self.limits.gemini_tokens_per_minute - tokens_used),
                'reset_time': f"غداً في {current_date}"
            }
        
        return {'allowed': True}
    
    def record_usage(self, service: str, operation: str, tokens_used: int = 0, 
                    response_time: float = 0, success: bool = True):
        """تسجيل الاستخدام"""
        
        # تحديث إحصائيات الاستخدام
        if service == 'gemini':
            self.usage_stats['daily_limits']['gemini_requests'] += 1
            self.usage_stats['daily_limits']['gemini_tokens'] += tokens_used
        
        # حفظ في قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO usage_logs (service, operation, tokens_used, response_time, success)
                VALUES (?, ?, ?, ?, ?)
            ''', (service, operation, tokens_used, response_time, success))
        
        self._save_usage_stats()
    
    def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """الحصول على رد مخزن مؤقتاً"""
        query_hash = str(hash(query.strip().lower()))
        
        # البحث في DiskCache أولاً
        cached = self.cache.get(query_hash)
        if cached:
            return cached
        
        # البحث في قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT response_data, model_used FROM cached_responses 
                WHERE query_hash = ? AND 
                      datetime(created_at) > datetime('now', '-7 days')
            ''', (query_hash,))
            
            row = cursor.fetchone()
            if row:
                response_data = json.loads(row[0])
                response_data['from_cache'] = True
                response_data['model_used'] = row[1]
                
                # تحديث عداد الوصول
                conn.execute('''
                    UPDATE cached_responses 
                    SET access_count = access_count + 1 
                    WHERE query_hash = ?
                ''', (query_hash,))
                
                # إضافة للذاكرة المؤقتة السريعة
                self.cache.set(query_hash, response_data, expire=3600)  # ساعة واحدة
                
                return response_data
        
        return None
    
    def cache_response(self, query: str, response_data: Dict[str, Any], model_used: str):
        """تخزين الرد مؤقتاً"""
        query_hash = str(hash(query.strip().lower()))
        
        # تخزين في DiskCache
        self.cache.set(query_hash, response_data, expire=86400)  # 24 ساعة
        
        # تخزين في قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO cached_responses 
                (query_hash, query_text, response_data, model_used)
                VALUES (?, ?, ?, ?)
            ''', (query_hash, query[:500], json.dumps(response_data, ensure_ascii=False), model_used))
    
    def optimize_for_free_hosting(self) -> Dict[str, Any]:
        """تحسين للاستضافة المجانية"""
        optimizations = {}
        
        # تنظيف الذاكرة المؤقتة
        cache_size = self.cache.volume()
        if cache_size > self.limits.disk_cache_size * 1024 * 1024 * 0.8:  # 80% من الحد الأقصى
            self.cache.clear()
            optimizations['cache_cleared'] = True
        
        # تنظيف قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            # حذف الجلسات القديمة
            conn.execute('''
                DELETE FROM user_sessions 
                WHERE datetime(last_activity) < datetime('now', '-7 days')
            ''')
            
            # حذف السجلات القديمة
            conn.execute('''
                DELETE FROM usage_logs 
                WHERE datetime(timestamp) < datetime('now', '-30 days')
            ''')
            
            # حذف الردود المخزنة القديمة
            conn.execute('''
                DELETE FROM cached_responses 
                WHERE datetime(created_at) < datetime('now', '-7 days')
                AND access_count < 2
            ''')
            
            rows_deleted = conn.total_changes
            if rows_deleted > 0:
                optimizations['db_cleaned'] = rows_deleted
        
        return optimizations
    
    def get_system_health(self) -> Dict[str, Any]:
        """فحص صحة النظام"""
        health = {
            'cache': {
                'size_mb': round(self.cache.volume() / (1024 * 1024), 2),
                'items': len(self.cache),
                'hit_rate': getattr(self.cache, 'stats', {}).get('hits', 0)
            },
            'database': {
                'size_mb': round(os.path.getsize(self.db_path) / (1024 * 1024), 2) if os.path.exists(self.db_path) else 0,
                'tables': []
            },
            'usage': self.usage_stats,
            'limits': asdict(self.limits)
        }
        
        # إحصائيات قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            for table in ['user_sessions', 'usage_logs', 'cached_responses']:
                cursor = conn.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                health['database']['tables'].append({
                    'name': table,
                    'rows': count
                })
        
        return health
    
    def export_data(self) -> Dict[str, str]:
        """تصدير البيانات للنسخ الاحتياطي"""
        export_data = {}
        
        # تصدير إحصائيات الاستخدام
        export_data['usage_stats'] = json.dumps(self.usage_stats, ensure_ascii=False, indent=2)
        
        # تصدير بيانات قاعدة البيانات
        with sqlite3.connect(self.db_path) as conn:
            # تصدير الردود المخزنة الأكثر استخداماً
            cursor = conn.execute('''
                SELECT query_text, response_data, model_used, access_count
                FROM cached_responses 
                WHERE access_count > 1
                ORDER BY access_count DESC
                LIMIT 100
            ''')
            
            popular_responses = []
            for row in cursor.fetchall():
                popular_responses.append({
                    'query': row[0],
                    'response': json.loads(row[1]),
                    'model': row[2],
                    'usage_count': row[3]
                })
            
            export_data['popular_responses'] = json.dumps(popular_responses, ensure_ascii=False, indent=2)
        
        return export_data

# إنشاء مثيل عام للاستخدام
free_architecture = FreeArchitectureManager()