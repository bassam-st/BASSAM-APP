"""
وحدة البحث والتلخيص
البحث عبر DuckDuckGo مع تلخيص المحتوى باستخدام SUMY و BM25
"""

import httpx
import re
from typing import Dict, List, Optional, Any
from duckduckgo_search import DDGS
from core.utils import is_arabic, clean_html, normalize_text

# استيراد مكتبات التلخيص
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    from sumy.nlp.stemmers import Stemmer
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False
    PlaintextParser = None
    Tokenizer = None
    LsaSummarizer = None
    Stemmer = None

try:
    from rank_bm25 import BM25Okapi
    from rapidfuzz import fuzz
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None

class SearchEngine:
    def __init__(self):
        self.ddgs = DDGS()
        self.session = httpx.Client(
            headers={"User-Agent": "BassamBot/1.0"},
            timeout=30.0
        )
    
    def search_web(self, query: str, max_results: int = 10) -> List[Dict]:
        """البحث في الويب باستخدام DuckDuckGo"""
        try:
            results = []
            ddgs_results = self.ddgs.text(query, max_results=max_results)
            
            for result in ddgs_results:
                results.append({
                    'title': result.get('title', ''),
                    'body': result.get('body', ''),
                    'href': result.get('href', ''),
                    'source': 'duckduckgo'
                })
            
            return results
        except Exception as e:
            print(f"خطأ في البحث: {e}")
            return []
    
    def search_images(self, query: str, max_results: int = 10) -> List[Dict]:
        """البحث عن الصور"""
        try:
            results = []
            ddgs_results = self.ddgs.images(query, max_results=max_results)
            
            for result in ddgs_results:
                results.append({
                    'title': result.get('title', ''),
                    'image': result.get('image', ''),
                    'thumbnail': result.get('thumbnail', ''),
                    'url': result.get('url', ''),
                    'source': result.get('source', '')
                })
            
            return results
        except Exception as e:
            print(f"خطأ في البحث عن الصور: {e}")
            return []
    
    def fetch_page_content(self, url: str) -> Optional[str]:
        """جلب محتوى الصفحة"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            # تنظيف HTML بشكل أساسي
            content = clean_html(response.text)
            return content[:5000]  # تحديد الحجم
            
        except Exception as e:
            print(f"خطأ في جلب المحتوى من {url}: {e}")
            return None
    
    def summarize_with_sumy(self, text: str, sentences_count: int = 3) -> str:
        """تلخيص النص باستخدام SUMY"""
        if not SUMY_AVAILABLE or not text:
            return text[:500] + "..." if len(text) > 500 else text
        
        try:
            # تحديد اللغة
            language = "arabic" if is_arabic(text) else "english"
            
            # إنشاء المحلل والملخص
            parser = PlaintextParser.from_string(text, Tokenizer(language))
            stemmer = Stemmer(language)
            summarizer = LsaSummarizer(stemmer)
            
            # تلخيص النص
            summary = summarizer(parser.document, sentences_count)
            summary_text = " ".join([str(sentence) for sentence in summary])
            
            return summary_text if summary_text else text[:500]
            
        except Exception as e:
            print(f"خطأ في التلخيص: {e}")
            return text[:500] + "..." if len(text) > 500 else text
    
    def rank_results_bm25(self, query: str, results: List[Dict]) -> List[Dict]:
        """ترتيب النتائج باستخدام BM25"""
        if not BM25_AVAILABLE or not results:
            return results
        
        try:
            # تحضير النصوص للترتيب
            documents = []
            for result in results:
                text = f"{result.get('title', '')} {result.get('body', '')}"
                documents.append(normalize_text(text).split())
            
            if not documents:
                return results
            
            # إنشاء نموذج BM25
            bm25 = BM25Okapi(documents)
            query_tokens = normalize_text(query).split()
            
            # حساب النقاط
            scores = bm25.get_scores(query_tokens)
            
            # ترتيب النتائج
            ranked_results = []
            for i, score in enumerate(scores):
                result = results[i].copy()
                result['bm25_score'] = score
                ranked_results.append(result)
            
            # ترتيب حسب النقاط
            ranked_results.sort(key=lambda x: x.get('bm25_score', 0), reverse=True)
            
            return ranked_results
            
        except Exception as e:
            print(f"خطأ في ترتيب النتائج: {e}")
            return results
    
    def search_and_summarize(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """البحث والتلخيص الذكي"""
        try:
            # البحث
            results = self.search_web(query, max_results)
            
            if not results:
                return {
                    'query': query,
                    'summary': 'لم يتم العثور على نتائج.',
                    'results': [],
                    'total_results': 0
                }
            
            # ترتيب النتائج
            ranked_results = self.rank_results_bm25(query, results)
            
            # تحضير النص للتلخيص
            all_content = []
            processed_results = []
            
            for result in ranked_results[:3]:  # أفضل 3 نتائج
                content = f"{result.get('title', '')} {result.get('body', '')}"
                all_content.append(content)
                processed_results.append({
                    'title': result.get('title', ''),
                    'snippet': result.get('body', '')[:200] + "...",
                    'url': result.get('href', ''),
                    'score': result.get('bm25_score', 0)
                })
            
            # تلخيص المحتوى
            combined_text = " ".join(all_content)
            summary = self.summarize_with_sumy(combined_text, sentences_count=4)
            
            return {
                'query': query,
                'summary': summary,
                'results': processed_results,
                'total_results': len(results)
            }
            
        except Exception as e:
            print(f"خطأ في البحث والتلخيص: {e}")
            return {
                'query': query,
                'summary': f'حدث خطأ أثناء البحث: {str(e)}',
                'results': [],
                'total_results': 0
            }

# إنشاء مثيل عام
search_engine = SearchEngine()