"""
نظام النشر المجاني المحسن - بسام الذكي
تحسين للنشر على Render، Vercel، Replit مع أقصى استفادة من الخدمات المجانية
"""

import os
import json
import yaml
from typing import Dict, Any, List

class FreeDeploymentOptimizer:
    """محسن النشر المجاني"""
    
    def __init__(self):
        self.platforms = {
            'render': {
                'build_minutes': 500,  # شهرياً
                'bandwidth_gb': 100,   # شهرياً
                'sleep_minutes': 15,   # بعد عدم النشاط
                'memory_mb': 512,      # مجاني
                'databases': 1         # PostgreSQL مجاني
            },
            'vercel': {
                'executions': 100000,  # شهرياً
                'bandwidth_gb': 100,   # شهرياً
                'build_minutes': 400,  # شهرياً
                'serverless': True
            },
            'replit': {
                'always_on': False,    # غير مجاني
                'databases': True,     # PostgreSQL مجاني
                'storage_gb': 1,       # مجاني
                'bandwidth_unlimited': True  # مجاني
            }
        }
    
    def generate_render_config(self) -> Dict[str, Any]:
        """إنشاء ملف render.yaml محسن"""
        return {
            'services': [
                {
                    'type': 'web',
                    'name': 'bassam-smart-ai',
                    'runtime': 'python',
                    'plan': 'free',
                    'region': 'oregon',  # أسرع منطقة مجانية
                    'buildCommand': 'pip install --upgrade pip && pip install -r requirements.txt',
                    'startCommand': 'gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 1 --timeout 120 main:app',
                    'healthCheckPath': '/health',
                    'envVars': [
                        {'key': 'PYTHON_VERSION', 'value': '3.11.7'},
                        {'key': 'PYTHONUNBUFFERED', 'value': '1'},
                        {'key': 'WEB_CONCURRENCY', 'value': '1'},  # تحسين للذاكرة المحدودة
                        {'key': 'MAX_WORKERS', 'value': '1'},
                        {'key': 'CACHE_SIZE_MB', 'value': '50'},  # تقليل استخدام الذاكرة
                        {'key': 'ENABLE_LOCAL_MODELS', 'value': 'false'}  # تعطيل النماذج المحلية للخادم
                    ],
                    'disk': {
                        'name': 'bassam-cache',
                        'sizeGB': 1,
                        'mountPath': '/opt/render/project/src/cache'
                    }
                }
            ]
        }
    
    def generate_vercel_config(self) -> Dict[str, Any]:
        """إنشاء ملف vercel.json محسن"""
        return {
            'version': 2,
            'name': 'bassam-smart-ai',
            'builds': [
                {
                    'src': 'main.py',
                    'use': '@vercel/python',
                    'config': {
                        'maxLambdaSize': '50mb',
                        'runtime': 'python3.11'
                    }
                }
            ],
            'routes': [
                {'src': '/(.*)', 'dest': 'main.py'}
            ],
            'env': {
                'PYTHONPATH': './core',
                'CACHE_SIZE_MB': '20',
                'ENABLE_LOCAL_MODELS': 'false'
            },
            'functions': {
                'main.py': {
                    'memory': 1024,  # MB
                    'maxDuration': 30  # ثانية للخطة المجانية
                }
            }
        }
    
    def generate_replit_config(self) -> Dict[str, Any]:
        """إنشاء ملف .replit محسن"""
        return {
            'language': 'python3',
            'run': 'uvicorn main:app --host 0.0.0.0 --port 5000 --reload',
            'entrypoint': 'main.py',
            'modules': ['python-3.11'],
            'env': {
                'CACHE_SIZE_MB': '100',
                'ENABLE_LOCAL_MODELS': 'true',  # Replit يدعم النماذج المحلية
                'PYTHONPATH': './core'
            },
            'gitignore': [
                'cache/',
                'data/',
                '__pycache__/',
                '*.pyc',
                '.env',
                'logs/'
            ]
        }
    
    def generate_docker_config(self) -> str:
        """إنشاء Dockerfile محسن للخدمات المجانية"""
        dockerfile = """# Dockerfile محسن لبسام الذكي
FROM python:3.11-slim

# تحسين الحجم
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# إعداد المشروع
WORKDIR /app
COPY requirements.txt .

# تثبيت المتطلبات مع تحسين الحجم
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# متغيرات البيئة للتحسين
ENV PYTHONUNBUFFERED=1
ENV CACHE_SIZE_MB=50
ENV ENABLE_LOCAL_MODELS=false
ENV MAX_WORKERS=1

# إنشاء مجلدات الكاش
RUN mkdir -p cache data

# تشغيل التطبيق
EXPOSE 5000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "main:app"]
"""
        return dockerfile
    
    def generate_optimized_requirements(self) -> List[str]:
        """قائمة متطلبات محسنة للنشر المجاني"""
        return [
            # الأساسيات
            'fastapi==0.115.0',
            'uvicorn[standard]==0.30.6',
            'gunicorn>=20.1.0',
            'httpx>=0.28.1',
            'python-multipart==0.0.9',
            
            # الذكاء الاصطناعي (الأساسي فقط)
            'google-generativeai>=0.3.0',
            'anthropic>=0.68.0',
            
            # الرياضيات (مخفف)
            'sympy==1.13.2',
            'numpy==1.26.4',
            'matplotlib>=3.8.0',
            
            # البحث والتلخيص (مخفف)
            'duckduckgo-search>=5.0.0',
            'beautifulsoup4>=4.12.0',
            'sumy==0.11.0',
            
            # التخزين المؤقت
            'diskcache>=5.6.3',
            
            # المساعدات
            'rapidfuzz==3.9.6',
            'deep-translator==1.11.4'
        ]
    
    def generate_environment_configs(self) -> Dict[str, Dict[str, str]]:
        """إعدادات متغيرات البيئة لكل منصة"""
        return {
            'render': {
                'PYTHON_VERSION': '3.11.7',
                'PYTHONUNBUFFERED': '1',
                'WEB_CONCURRENCY': '1',
                'CACHE_SIZE_MB': '50',
                'ENABLE_LOCAL_MODELS': 'false',
                'DATABASE_MAX_CONNECTIONS': '3'
            },
            'vercel': {
                'PYTHONPATH': './core',
                'CACHE_SIZE_MB': '20',
                'ENABLE_LOCAL_MODELS': 'false',
                'VERCEL_TIMEOUT': '30'
            },
            'replit': {
                'CACHE_SIZE_MB': '100',
                'ENABLE_LOCAL_MODELS': 'true',
                'PYTHONPATH': './core',
                'DATABASE_MAX_CONNECTIONS': '5'
            },
            'heroku': {
                'PYTHON_VERSION': '3.11.7',
                'CACHE_SIZE_MB': '30',
                'ENABLE_LOCAL_MODELS': 'false',
                'WEB_CONCURRENCY': '1'
            }
        }
    
    def generate_monitoring_config(self) -> Dict[str, Any]:
        """إعداد المراقبة المجانية"""
        return {
            'health_checks': {
                'endpoint': '/health',
                'interval_seconds': 300,  # 5 دقائق
                'timeout_seconds': 30,
                'failure_threshold': 3
            },
            'logging': {
                'level': 'INFO',
                'format': 'json',
                'max_size_mb': 10,
                'retention_days': 7
            },
            'metrics': {
                'enabled': True,
                'endpoint': '/metrics',
                'track_requests': True,
                'track_errors': True,
                'track_performance': True
            }
        }
    
    def create_deployment_files(self) -> Dict[str, str]:
        """إنشاء جميع ملفات النشر"""
        files = {}
        
        # Render
        files['render.yaml'] = yaml.dump(self.generate_render_config(), 
                                       default_flow_style=False, allow_unicode=True)
        
        # Vercel  
        files['vercel.json'] = json.dumps(self.generate_vercel_config(), 
                                        indent=2, ensure_ascii=False)
        
        # Replit
        files['.replit'] = json.dumps(self.generate_replit_config(), 
                                    indent=2, ensure_ascii=False)
        
        # Docker
        files['Dockerfile'] = self.generate_docker_config()
        
        # Requirements محسن
        files['requirements-deploy.txt'] = '\n'.join(self.generate_optimized_requirements())
        
        # متغيرات البيئة
        env_configs = self.generate_environment_configs()
        for platform, config in env_configs.items():
            files[f'.env.{platform}'] = '\n'.join([f'{k}={v}' for k, v in config.items()])
        
        # مراقبة
        files['monitoring.json'] = json.dumps(self.generate_monitoring_config(), 
                                            indent=2, ensure_ascii=False)
        
        return files
    
    def get_deployment_guide(self) -> str:
        """دليل النشر الشامل"""
        return """
# 🚀 دليل النشر المجاني الشامل - بسام الذكي

## 📋 الخطوات السريعة:

### 1️⃣ Render.com (مُوصى به للخلفية):
```bash
git add .
git commit -m "🚀 بسام الذكي - جاهز للنشر"
git push origin main
```
- اذهب إلى render.com
- اربط مستودع GitHub
- اختر "Web Service"
- استخدم الإعدادات من render.yaml

### 2️⃣ Vercel (مُوصى به للواجهة):
```bash
npm i -g vercel
vercel --prod
```

### 3️⃣ Replit (للتطوير والاختبار):
- استورد المشروع من GitHub
- التطبيق سيعمل تلقائياً

## 🔑 متغيرات البيئة المطلوبة:
```
GEMINI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here (اختياري)
PERPLEXITY_API_KEY=your_key_here (اختياري)
```

## 🎯 التحسينات المطبقة:
- ✅ استخدام الحد الأدنى من الذاكرة
- ✅ تحسين أوقات البناء
- ✅ تخزين مؤقت ذكي
- ✅ مراقبة مجانية
- ✅ نماذج محلية (عند الإمكان)

## 📊 حدود الخدمات المجانية:
- **Render**: 500 دقيقة بناء/شهر، 100GB نقل
- **Vercel**: 100k تنفيذ/شهر، 100GB نقل  
- **Replit**: 1GB تخزين، نقل غير محدود

## 🆘 حل المشاكل:
1. **انتهاء الذاكرة**: قلل CACHE_SIZE_MB
2. **بطء في البناء**: استخدم requirements-deploy.txt
3. **انقطاع الاتصال**: فعّل النماذج المحلية
"""

# إنشاء مثيل عام
free_deployment = FreeDeploymentOptimizer()