"""
إعداد النماذج المحلية المجانية - بسام الذكي
نظام تلقائي لتنزيل وتشغيل النماذج المحلية عند الحاجة
"""

import os
import subprocess
import json
import requests
from typing import Dict, List, Optional

class LocalLLMSetup:
    """مدير إعداد النماذج المحلية المجانية"""
    
    def __init__(self):
        self.ollama_installed = self._check_ollama()
        self.available_models = [
            {
                'name': 'llama3.1:8b',
                'size': '4.7GB',
                'description': 'Meta Llama 3.1 8B - نموذج متقدم ومتوازن',
                'priority': 1,
                'supports_arabic': True
            },
            {
                'name': 'mistral:7b', 
                'size': '4.1GB',
                'description': 'Mistral 7B - سريع وفعال',
                'priority': 2,
                'supports_arabic': True
            },
            {
                'name': 'gemma2:9b',
                'size': '5.4GB', 
                'description': 'Google Gemma 2 9B - متطور ومتعدد اللغات',
                'priority': 3,
                'supports_arabic': True
            },
            {
                'name': 'qwen2:7b',
                'size': '4.4GB',
                'description': 'Qwen 2 7B - ممتاز للعربية',
                'priority': 4,
                'supports_arabic': True
            },
            {
                'name': 'phi3:mini',
                'size': '2.3GB',
                'description': 'Microsoft Phi-3 Mini - خفيف وسريع',
                'priority': 5,
                'supports_arabic': False
            }
        ]
        self.installed_models = self._get_installed_models()
    
    def _check_ollama(self) -> bool:
        """فحص إذا كان Ollama مثبت"""
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _get_installed_models(self) -> List[str]:
        """الحصول على قائمة النماذج المثبتة"""
        if not self.ollama_installed:
            return []
        
        try:
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # تجاهل العنوان
                models = []
                for line in lines:
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
                return models
        except:
            pass
        
        return []
    
    def install_ollama(self) -> Dict[str, str]:
        """تثبيت Ollama تلقائياً"""
        if self.ollama_installed:
            return {'status': 'already_installed', 'message': 'Ollama مثبت بالفعل'}
        
        try:
            # تنزيل وتثبيت Ollama
            print("📥 جاري تنزيل Ollama...")
            
            # للأنظمة المختلفة
            import platform
            system = platform.system().lower()
            
            if system == 'linux':
                # تثبيت Ollama على Linux
                install_cmd = 'curl -fsSL https://ollama.ai/install.sh | sh'
                result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.ollama_installed = True
                    return {'status': 'installed', 'message': 'تم تثبيت Ollama بنجاح'}
                else:
                    return {'status': 'error', 'message': f'فشل التثبيت: {result.stderr}'}
            
            else:
                return {
                    'status': 'manual_required',
                    'message': f'يرجى تثبيت Ollama يدوياً من https://ollama.ai للنظام {system}'
                }
        
        except Exception as e:
            return {'status': 'error', 'message': f'خطأ في التثبيت: {e}'}
    
    def install_model(self, model_name: str) -> Dict[str, str]:
        """تثبيت نموذج محدد"""
        if not self.ollama_installed:
            install_result = self.install_ollama()
            if install_result['status'] != 'installed' and install_result['status'] != 'already_installed':
                return install_result
        
        if model_name in self.installed_models:
            return {'status': 'already_installed', 'message': f'النموذج {model_name} مثبت بالفعل'}
        
        try:
            print(f"📥 جاري تنزيل النموذج {model_name}...")
            
            # تنزيل النموذج
            result = subprocess.run(['ollama', 'pull', model_name], 
                                  capture_output=True, text=True, timeout=1800)  # 30 دقيقة
            
            if result.returncode == 0:
                self.installed_models.append(model_name)
                return {'status': 'installed', 'message': f'تم تثبيت {model_name} بنجاح'}
            else:
                return {'status': 'error', 'message': f'فشل تثبيت {model_name}: {result.stderr}'}
        
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'message': 'انتهت مهلة التنزيل - يرجى المحاولة لاحقاً'}
        except Exception as e:
            return {'status': 'error', 'message': f'خطأ في التثبيت: {e}'}
    
    def auto_install_best_model(self) -> Dict[str, str]:
        """تثبيت أفضل نموذج متاح تلقائياً"""
        
        # فحص المساحة المتاحة (تقريبي)
        try:
            import shutil
            free_space_gb = shutil.disk_usage('.').free / (1024**3)
        except:
            free_space_gb = 10  # افتراض 10GB
        
        # اختيار النموذج الأنسب
        for model in sorted(self.available_models, key=lambda x: x['priority']):
            model_size_gb = float(model['size'].replace('GB', ''))
            
            if free_space_gb > model_size_gb + 2:  # 2GB إضافية للأمان
                if model['name'] not in self.installed_models:
                    print(f"🎯 اختيار النموذج {model['name']} ({model['size']})")
                    return self.install_model(model['name'])
                else:
                    return {
                        'status': 'already_installed', 
                        'message': f'النموذج الأفضل {model["name"]} مثبت بالفعل'
                    }
        
        return {'status': 'no_space', 'message': 'لا توجد مساحة كافية لتثبيت أي نموذج'}
    
    def start_ollama_service(self) -> Dict[str, str]:
        """تشغيل خدمة Ollama"""
        if not self.ollama_installed:
            return {'status': 'not_installed', 'message': 'Ollama غير مثبت'}
        
        try:
            # فحص إذا كانت الخدمة تعمل
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {'status': 'running', 'message': 'خدمة Ollama تعمل بالفعل'}
            else:
                # تشغيل الخدمة في الخلفية
                subprocess.Popen(['ollama', 'serve'])
                return {'status': 'started', 'message': 'تم تشغيل خدمة Ollama'}
        
        except Exception as e:
            return {'status': 'error', 'message': f'خطأ في تشغيل الخدمة: {e}'}
    
    def test_model(self, model_name: str) -> Dict[str, str]:
        """اختبار نموذج محدد"""
        if model_name not in self.installed_models:
            return {'status': 'not_installed', 'message': f'النموذج {model_name} غير مثبت'}
        
        try:
            # اختبار بسيط
            test_prompt = "مرحبا، كيف حالك؟"
            result = subprocess.run(['ollama', 'run', model_name, test_prompt], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                return {
                    'status': 'working', 
                    'message': f'النموذج {model_name} يعمل بشكل طبيعي',
                    'response': result.stdout.strip()[:100] + "..."
                }
            else:
                return {'status': 'error', 'message': f'النموذج {model_name} لا يستجيب'}
        
        except Exception as e:
            return {'status': 'error', 'message': f'خطأ في اختبار النموذج: {e}'}
    
    def get_system_info(self) -> Dict[str, any]:
        """معلومات شاملة عن النظام"""
        
        # فحص المساحة
        try:
            import shutil
            total, used, free = shutil.disk_usage('.')
            disk_info = {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2)
            }
        except:
            disk_info = {'error': 'لا يمكن قراءة معلومات القرص'}
        
        return {
            'ollama_installed': self.ollama_installed,
            'installed_models': self.installed_models,
            'available_models': self.available_models,
            'disk_space': disk_info,
            'recommended_model': self._get_recommended_model()
        }
    
    def _get_recommended_model(self) -> Optional[str]:
        """الحصول على النموذج المُوصى به"""
        try:
            import shutil
            free_space_gb = shutil.disk_usage('.').free / (1024**3)
            
            for model in sorted(self.available_models, key=lambda x: x['priority']):
                model_size_gb = float(model['size'].replace('GB', ''))
                if free_space_gb > model_size_gb + 2:
                    return model['name']
            
            return None
        except:
            return self.available_models[0]['name']  # الافتراضي

# إنشاء مثيل عام للاستخدام
local_llm_setup = LocalLLMSetup()