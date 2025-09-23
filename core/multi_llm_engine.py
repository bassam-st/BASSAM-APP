"""
محرك النماذج اللغوية المتعددة المجاني - بسام الذكي
نظام ذكي يختار أفضل نموذج مجاني متاح تلقائياً
"""

import os
import asyncio
import httpx
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class LLMModel:
    """تعريف نموذج لغوي"""
    name: str
    provider: str
    api_key_env: str
    endpoint: Optional[str] = None
    cost_tier: int = 1  # 1=مجاني، 2=قليل التكلفة، 3=مدفوع
    quality_score: int = 8  # تقييم الجودة من 1-10
    max_tokens: int = 4096
    supports_arabic: bool = True
    local: bool = False

class MultiLLMEngine:
    """محرك النماذج اللغوية المتعددة المجاني"""
    
    def __init__(self):
        self.models = self._initialize_models()
        self.active_models = []
        self.fallback_responses = {
            'ar': "عذراً، جميع النماذج المجانية غير متوفرة حالياً. يرجى المحاولة لاحقاً.",
            'en': "Sorry, all free models are currently unavailable. Please try again later."
        }
        self._check_available_models()
    
    def _initialize_models(self) -> List[LLMModel]:
        """تهيئة قائمة النماذج المجانية المتاحة"""
        return [
            # النماذج المجانية الرئيسية
            LLMModel(
                name="Gemini 1.5 Flash",
                provider="google",
                api_key_env="GEMINI_API_KEY",
                cost_tier=1,
                quality_score=9,
                max_tokens=8192,
                supports_arabic=True
            ),
            LLMModel(
                name="Claude 3 Haiku", 
                provider="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                cost_tier=2,
                quality_score=8,
                max_tokens=4096,
                supports_arabic=True
            ),
            LLMModel(
                name="Perplexity Sonar",
                provider="perplexity", 
                api_key_env="PERPLEXITY_API_KEY",
                endpoint="https://api.perplexity.ai/chat/completions",
                cost_tier=2,
                quality_score=8,
                max_tokens=4096,
                supports_arabic=True
            ),
            
            # النماذج المحلية المجانية (عبر Ollama)
            LLMModel(
                name="Llama 3.1 8B",
                provider="ollama",
                api_key_env="",
                endpoint="http://localhost:11434/api/generate",
                cost_tier=1,
                quality_score=8,
                max_tokens=8192,
                supports_arabic=True,
                local=True
            ),
            LLMModel(
                name="Mistral 7B",
                provider="ollama",
                api_key_env="",
                endpoint="http://localhost:11434/api/generate", 
                cost_tier=1,
                quality_score=7,
                max_tokens=4096,
                supports_arabic=True,
                local=True
            ),
            LLMModel(
                name="Gemma 2 9B",
                provider="ollama",
                api_key_env="",
                endpoint="http://localhost:11434/api/generate",
                cost_tier=1,
                quality_score=7,
                max_tokens=4096,
                supports_arabic=True,
                local=True
            ),
            
            # نماذج النسخ الاحتياطي المجانية
            LLMModel(
                name="Hugging Face Inference",
                provider="huggingface",
                api_key_env="HF_TOKEN",
                endpoint="https://api-inference.huggingface.co/models/microsoft/DialoGPT-large",
                cost_tier=1,
                quality_score=6,
                max_tokens=2048,
                supports_arabic=False,
                local=False
            )
        ]
    
    def _check_available_models(self):
        """فحص النماذج المتاحة"""
        self.active_models = []
        
        for model in self.models:
            if self._is_model_available(model):
                self.active_models.append(model)
                print(f"✅ {model.name} متوفر ({model.provider})")
            else:
                print(f"❌ {model.name} غير متوفر ({model.provider})")
        
        # ترتيب النماذج حسب الأولوية (مجاني أولاً، ثم الجودة)
        self.active_models.sort(key=lambda m: (m.cost_tier, -m.quality_score))
        
        if self.active_models:
            print(f"🎯 {len(self.active_models)} نموذج متوفر للاستخدام")
        else:
            print("⚠️ لا توجد نماذج متوفرة - سيتم استخدام الردود الاحتياطية")
    
    def _is_model_available(self, model: LLMModel) -> bool:
        """التحقق من توفر النموذج"""
        # للنماذج المحلية، فحص الاتصال
        if model.local and model.endpoint:
            try:
                import requests
                response = requests.get(model.endpoint.replace('/api/generate', '/api/tags'), timeout=2)
                return response.status_code == 200
            except:
                return False
        
        # للنماذج السحابية، فحص API key
        if model.api_key_env:
            api_key = os.getenv(model.api_key_env)
            return bool(api_key and len(api_key) > 10)
        
        return True
    
    async def generate_response(self, prompt: str, context: str = "", max_tokens: int = 1000) -> Dict[str, Any]:
        """توليد رد ذكي باستخدام أفضل نموذج متاح"""
        
        if not self.active_models:
            return {
                'success': False,
                'response': self.fallback_responses['ar'],
                'model': 'fallback',
                'provider': 'local'
            }
        
        # تجربة النماذج بالترتيب
        for model in self.active_models:
            try:
                response = await self._call_model(model, prompt, context, max_tokens)
                if response['success']:
                    return response
            except Exception as e:
                print(f"❌ خطأ في {model.name}: {e}")
                continue
        
        # إذا فشلت جميع النماذج
        return {
            'success': False,
            'response': self.fallback_responses['ar'],
            'model': 'fallback',
            'provider': 'local'
        }
    
    async def _call_model(self, model: LLMModel, prompt: str, context: str, max_tokens: int) -> Dict[str, Any]:
        """استدعاء نموذج محدد"""
        
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        
        if model.provider == "google":
            return await self._call_gemini(model, full_prompt, max_tokens)
        elif model.provider == "anthropic":
            return await self._call_anthropic(model, full_prompt, max_tokens)
        elif model.provider == "perplexity":
            return await self._call_perplexity(model, full_prompt, max_tokens)
        elif model.provider == "ollama":
            return await self._call_ollama(model, full_prompt, max_tokens)
        elif model.provider == "huggingface":
            return await self._call_huggingface(model, full_prompt, max_tokens)
        else:
            raise ValueError(f"مقدم خدمة غير مدعوم: {model.provider}")
    
    async def _call_gemini(self, model: LLMModel, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """استدعاء Gemini"""
        try:
            import google.generativeai as genai
            
            api_key = os.getenv(model.api_key_env)
            genai.configure(api_key=api_key)
            
            model_instance = genai.GenerativeModel('gemini-1.5-flash')
            response = model_instance.generate_content(prompt)
            
            return {
                'success': True,
                'response': response.text,
                'model': model.name,
                'provider': model.provider,
                'tokens_used': len(response.text.split())
            }
        except Exception as e:
            raise Exception(f"Gemini error: {e}")
    
    async def _call_anthropic(self, model: LLMModel, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """استدعاء Claude"""
        try:
            import anthropic
            
            api_key = os.getenv(model.api_key_env)
            client = anthropic.Anthropic(api_key=api_key)
            
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                'success': True,
                'response': message.content[0].text,
                'model': model.name,
                'provider': model.provider,
                'tokens_used': message.usage.output_tokens
            }
        except Exception as e:
            raise Exception(f"Claude error: {e}")
    
    async def _call_perplexity(self, model: LLMModel, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """استدعاء Perplexity"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {os.getenv(model.api_key_env)}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
                
                response = await client.post(model.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                return {
                    'success': True,
                    'response': data['choices'][0]['message']['content'],
                    'model': model.name,
                    'provider': model.provider,
                    'tokens_used': data.get('usage', {}).get('total_tokens', 0)
                }
        except Exception as e:
            raise Exception(f"Perplexity error: {e}")
    
    async def _call_ollama(self, model: LLMModel, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """استدعاء Ollama (نماذج محلية)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": model.name.lower().replace(" ", "-"),
                    "prompt": prompt,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7
                    }
                }
                
                response = await client.post(model.endpoint, json=payload)
                response.raise_for_status()
                
                data = response.json()
                return {
                    'success': True,
                    'response': data.get('response', ''),
                    'model': model.name,
                    'provider': model.provider,
                    'tokens_used': len(data.get('response', '').split())
                }
        except Exception as e:
            raise Exception(f"Ollama error: {e}")
    
    async def _call_huggingface(self, model: LLMModel, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """استدعاء Hugging Face Inference"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {os.getenv(model.api_key_env)}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": 0.7,
                        "return_full_text": False
                    }
                }
                
                response = await client.post(model.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                generated_text = data[0]['generated_text'] if isinstance(data, list) else data.get('generated_text', '')
                
                return {
                    'success': True,
                    'response': generated_text,
                    'model': model.name,
                    'provider': model.provider,
                    'tokens_used': len(generated_text.split())
                }
        except Exception as e:
            raise Exception(f"Hugging Face error: {e}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة النماذج المتاحة"""
        return [
            {
                'name': model.name,
                'provider': model.provider,
                'cost_tier': model.cost_tier,
                'quality_score': model.quality_score,
                'local': model.local,
                'supports_arabic': model.supports_arabic
            }
            for model in self.active_models
        ]
    
    def get_model_stats(self) -> Dict[str, Any]:
        """إحصائيات النماذج"""
        free_models = len([m for m in self.active_models if m.cost_tier == 1])
        local_models = len([m for m in self.active_models if m.local])
        
        return {
            'total_models': len(self.active_models),
            'free_models': free_models,
            'local_models': local_models,
            'cloud_models': len(self.active_models) - local_models,
            'best_model': self.active_models[0].name if self.active_models else None
        }

# إنشاء مثيل عام للاستخدام
multi_llm_engine = MultiLLMEngine()