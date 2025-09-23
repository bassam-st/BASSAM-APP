"""
وحدة المحرك الرياضي
حل المسائل الرياضية باستخدام SymPy ورسم المعادلات بـ matplotlib
"""

import re
import base64
import io
from typing import Dict, Optional, List, Any
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sympy import (
    symbols, Matrix, sympify, simplify, diff, integrate, sqrt, sin, cos, tan,
    solve, Eq, factor, expand, limit, oo, series, det, latex,
    ln, log, pi, lambdify, Add, Mul, Pow
)

# وظائف المصفوفات - تم تعطيلها مؤقتاً لتجنب مشاكل الاستيراد
def rank(matrix):
    """حساب رتبة المصفوفة"""
    try:
        return matrix.rank()
    except AttributeError:
        return len(matrix)

from core.utils import convert_arabic_numbers

# رموز x و y للاستخدام في العمليات
x, y = symbols('x y')

class MathEngine:
    def __init__(self):
        plt.style.use('default')
        # إعداد الخط للعربية
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS']
    
    def normalize_math_expression(self, expr: str) -> str:
        """تطبيع التعبير الرياضي"""
        if not expr:
            return ""
        
        # تحويل الأرقام العربية
        expr = convert_arabic_numbers(expr.strip())
        
        # إزالة البادئات
        prefixes = [
            'مشتق:', 'تكامل:', 'حل:', 'تبسيط:', 'تحليل:', 'توسيع:', 'ارسم:', 'نهاية:',
            'diff:', 'integral:', 'solve:', 'simplify:', 'factor:', 'expand:', 'plot:', 'limit:'
        ]
        
        for prefix in prefixes:
            if expr.lower().startswith(prefix.lower()):
                expr = expr[len(prefix):].strip()
                break
        
        # تطبيع العمليات
        expr = expr.replace('^', '**').replace('جذر', 'sqrt').replace('√', 'sqrt')
        expr = re.sub(r'\\cdot', '*', expr)
        expr = re.sub(r'\\(sin|cos|tan|sqrt|ln|log)', r'\1', expr)
        
        # معالجة المسافات (الضرب الضمني)
        expr = re.sub(r'(\d+)\s+([a-zA-Z])', r'\1*\2', expr)
        expr = re.sub(r'([a-zA-Z0-9\)])\s+([a-zA-Z])', r'\1*\2', expr)
        # معالجة الضرب الضمني مع الأقواس (مع تجنب الدوال المعروفة)
        # أولاً، احفظ الدوال المعروفة
        functions = ['sin', 'cos', 'tan', 'sqrt', 'ln', 'log', 'exp', 'abs']
        for func in functions:
            expr = expr.replace(f'{func}*(', f'{func}(')
        # ثم طبق قاعدة الضرب الضمني
        expr = re.sub(r'([a-zA-Z0-9\)])\s*\(', r'\1*(', expr)
        # وأعد الدوال المعروفة
        for func in functions:
            expr = expr.replace(f'{func}*(', f'{func}(')
        
        return expr.strip()
    
    def detect_operation(self, query: str) -> str:
        """كشف نوع العملية الرياضية"""
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ['مشتق', 'diff', 'derivative']):
            return 'derivative'
        elif any(keyword in query_lower for keyword in ['تكامل', 'integral', 'integrate']):
            return 'integral'
        elif any(keyword in query_lower for keyword in ['حل', 'solve', 'equation']):
            return 'solve'
        elif any(keyword in query_lower for keyword in ['تبسيط', 'simplify']):
            return 'simplify'
        elif any(keyword in query_lower for keyword in ['تحليل', 'factor']):
            return 'factor'
        elif any(keyword in query_lower for keyword in ['توسيع', 'expand']):
            return 'expand'
        elif any(keyword in query_lower for keyword in ['ارسم', 'plot', 'graph']):
            return 'plot'
        elif any(keyword in query_lower for keyword in ['نهاية', 'limit']):
            return 'limit'
        elif any(keyword in query_lower for keyword in ['matrix', 'مصفوفة']):
            return 'matrix'
        else:
            return 'evaluate'
    
    def solve_derivative(self, expr_str: str) -> Dict[str, Any]:
        """حساب المشتق مع شرح الخطوات"""
        try:
            expr = sympify(expr_str)
            derivative = diff(expr, x)
            
            # شرح خطوات المشتق
            steps = self._explain_derivative_steps(expr, derivative)
            detailed_explanation = self._format_derivative_explanation(expr_str, derivative, steps)
            
            return {
                'success': True,
                'operation': 'المشتق',
                'original': str(expr),
                'result': str(derivative),
                'steps': steps,
                'explanation': detailed_explanation,
                'latex': latex(derivative) if hasattr(derivative, '_latex') else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في حساب المشتق: {str(e)}'
            }
    
    def solve_integral(self, expr_str: str) -> Dict[str, Any]:
        """حساب التكامل مع شرح الخطوات"""
        try:
            expr = sympify(expr_str)
            integral = integrate(expr, x)
            
            # شرح خطوات التكامل
            steps = self._explain_integral_steps(expr, integral)
            detailed_explanation = self._format_integral_explanation(expr_str, integral, steps)
            
            return {
                'success': True,
                'operation': 'التكامل',
                'original': str(expr),
                'result': str(integral),
                'steps': steps,
                'explanation': detailed_explanation,
                'latex': latex(integral) if hasattr(integral, '_latex') else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في حساب التكامل: {str(e)}'
            }
    
    def solve_equation(self, expr_str: str) -> Dict[str, Any]:
        """حل المعادلات"""
        try:
            # معالجة المعادلات
            if '=' in expr_str:
                left, right = expr_str.split('=', 1)
                equation = Eq(sympify(left.strip()), sympify(right.strip()))
                solutions = solve(equation, x)
            else:
                # حل المعادلة = 0
                expr = sympify(expr_str)
                solutions = solve(expr, x)
            
            return {
                'success': True,
                'operation': 'حل المعادلة',
                'original': expr_str,
                'solutions': [str(sol) for sol in solutions],
                'count': len(solutions)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في حل المعادلة: {str(e)}'
            }
    
    def plot_function(self, expr_str: str, x_range: tuple = (-10, 10)) -> Dict[str, Any]:
        """رسم الدالة"""
        try:
            expr = sympify(expr_str)
            
            # تحويل التعبير إلى دالة رقمية
            func = lambdify(x, expr, 'numpy')
            
            # إنشاء نقاط البيانات
            x_vals = np.linspace(x_range[0], x_range[1], 400)
            
            # تجنب القيم غير المحددة
            try:
                y_vals = func(x_vals)
                # تصفية القيم اللانهائية
                mask = np.isfinite(y_vals)
                x_vals = x_vals[mask]
                y_vals = y_vals[mask]
            except:
                # في حالة فشل التقييم، استخدم نقاط منفصلة
                x_vals_safe = []
                y_vals_safe = []
                for x_val in x_vals:
                    try:
                        y_val = func(x_val)
                        if np.isfinite(y_val):
                            x_vals_safe.append(x_val)
                            y_vals_safe.append(y_val)
                    except:
                        continue
                x_vals = np.array(x_vals_safe)
                y_vals = np.array(y_vals_safe)
            
            if len(x_vals) == 0:
                return {
                    'success': False,
                    'error': 'لا يمكن رسم هذه الدالة في النطاق المحدد'
                }
            
            # إنشاء الرسم البياني
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(x_vals, y_vals, 'b-', linewidth=2, label=f'y = {expr}')
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linewidth=0.5)
            ax.axvline(x=0, color='k', linewidth=0.5)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_title(f'الرسم البياني للدالة: y = {expr}')
            ax.legend()
            
            # تحديد نطاق المحاور
            if len(y_vals) > 0:
                y_margin = (np.max(y_vals) - np.min(y_vals)) * 0.1
                ax.set_ylim(np.min(y_vals) - y_margin, np.max(y_vals) + y_margin)
            
            # تحويل إلى base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
            
            return {
                'success': True,
                'operation': 'الرسم البياني',
                'function': str(expr),
                'image': image_base64,
                'points_count': len(x_vals)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في رسم الدالة: {str(e)}'
            }
    
    def solve_matrix(self, matrix_str: str) -> Dict[str, Any]:
        """عمليات المصفوفات"""
        try:
            import ast
            
            # تنظيف النص
            matrix_str = matrix_str.replace('matrix:', '').strip()
            
            # تحويل آمن باستخدام ast.literal_eval
            try:
                matrix_data = ast.literal_eval(matrix_str)
                # التحقق من أن البيانات قائمة من القوائم أو الأرقام
                if not isinstance(matrix_data, (list, tuple)):
                    raise ValueError("البيانات يجب أن تكون قائمة")
                
                # التحقق من أن كل عنصر رقم أو قائمة من الأرقام
                def validate_matrix_data(data):
                    if isinstance(data, (int, float)):
                        return True
                    elif isinstance(data, (list, tuple)):
                        return all(validate_matrix_data(item) for item in data)
                    else:
                        return False
                
                if not validate_matrix_data(matrix_data):
                    raise ValueError("البيانات يجب أن تحتوي على أرقام فقط")
                
                matrix = Matrix(matrix_data)
            except (ValueError, SyntaxError) as e:
                return {
                    'success': False,
                    'error': f'تنسيق المصفوفة غير صحيح: {str(e)}'
                }
            
            # حساب العمليات المختلفة
            results = {
                'success': True,
                'operation': 'عمليات المصفوفات',
                'matrix': str(matrix),
                'determinant': None,
                'rank': None,
                'inverse': None,
                'shape': matrix.shape
            }
            
            # المحدد (للمصفوفات المربعة فقط)
            if matrix.rows == matrix.cols:
                results['determinant'] = str(det(matrix))
                
                # المعكوس (إذا كان المحدد غير صفر)
                try:
                    if det(matrix) != 0:
                        results['inverse'] = str(matrix.inv())
                except:
                    results['inverse'] = 'غير موجود (المحدد = 0)'
            
            # الرتبة
            try:
                results['rank'] = rank(matrix)
            except:
                results['rank'] = matrix.rank()
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في عمليات المصفوفات: {str(e)}'
            }
    
    def _explain_derivative_steps(self, expr, derivative) -> List[str]:
        """شرح خطوات المشتق"""
        steps = []
        expr_str = str(expr)
        
        # تحديد نوع الدالة وقواعد المشتق
        if expr.is_polynomial():
            steps.append("🔍 هذه دالة كثيرة حدود، سنستخدم قاعدة القوة")
            
            # تحليل كل حد
            terms = Add.make_args(expr)
            for i, term in enumerate(terms, 1):
                if term.has(x):
                    # استخراج المعامل والأس
                    coeff = term.as_coefficients_dict()[x**term.as_coeff_exponent(x)[1]]
                    power = term.as_coeff_exponent(x)[1]
                    
                    if power == 1:
                        steps.append(f"📝 الحد {i}: {coeff}x → المشتق: {coeff} (قاعدة: مشتق cx = c)")
                    elif power == 0:
                        steps.append(f"📝 الحد {i}: {coeff} → المشتق: 0 (قاعدة: مشتق الثابت = 0)")
                    else:
                        new_coeff = coeff * power
                        new_power = power - 1
                        steps.append(f"📝 الحد {i}: {coeff}x^{power} → المشتق: {new_coeff}x^{new_power} (قاعدة القوة: d/dx[x^n] = nx^(n-1))")
        
        elif expr.has(sin) or expr.has(cos) or expr.has(tan):
            steps.append("🌊 تحتوي على دوال مثلثية، سنستخدم قواعد المشتقات المثلثية")
            if expr.has(sin):
                steps.append("📐 قاعدة: مشتق sin(x) = cos(x)")
            if expr.has(cos):
                steps.append("📐 قاعدة: مشتق cos(x) = -sin(x)")
            if expr.has(tan):
                steps.append("📐 قاعدة: مشتق tan(x) = sec²(x)")
        
        elif expr.has(exp) or expr.has(log):
            steps.append("📊 تحتوي على دوال أسية أو لوغاريتمية")
            if expr.has(exp):
                steps.append("⚡ قاعدة: مشتق e^x = e^x")
            if expr.has(log):
                steps.append("📈 قاعدة: مشتق ln(x) = 1/x")
        
        # إضافة الحل النهائي
        steps.append(f"✅ النتيجة النهائية: {derivative}")
        
        return steps
    
    def _explain_integral_steps(self, expr, integral) -> List[str]:
        """شرح خطوات التكامل"""
        steps = []
        expr_str = str(expr)
        
        # تحديد نوع الدالة وقواعد التكامل
        if expr.is_polynomial():
            steps.append("🔍 هذه دالة كثيرة حدود، سنستخدم قاعدة القوة للتكامل")
            
            # تحليل كل حد
            terms = Add.make_args(expr) if expr.is_Add else [expr]
            for i, term in enumerate(terms, 1):
                if term.has(x):
                    coeff = term.as_coefficients_dict()[x**term.as_coeff_exponent(x)[1]]
                    power = term.as_coeff_exponent(x)[1]
                    
                    if power == -1:
                        steps.append(f"📝 الحد {i}: {coeff}/x → التكامل: {coeff}ln|x| (قاعدة: ∫1/x dx = ln|x|)")
                    else:
                        new_power = power + 1
                        new_coeff = coeff / new_power
                        steps.append(f"📝 الحد {i}: {coeff}x^{power} → التكامل: {new_coeff}x^{new_power} (قاعدة: ∫x^n dx = x^(n+1)/(n+1))")
        
        elif expr.has(sin) or expr.has(cos) or expr.has(tan):
            steps.append("🌊 تحتوي على دوال مثلثية")
            if expr.has(sin):
                steps.append("📐 قاعدة: ∫sin(x) dx = -cos(x)")
            if expr.has(cos):
                steps.append("📐 قاعدة: ∫cos(x) dx = sin(x)")
        
        elif expr.has(exp):
            steps.append("⚡ تحتوي على دوال أسية")
            steps.append("📊 قاعدة: ∫e^x dx = e^x")
        
        # إضافة التذكير بثابت التكامل
        steps.append("📌 لا تنسى إضافة ثابت التكامل C في التكامل غير المحدود")
        steps.append(f"✅ النتيجة النهائية: {integral} + C")
        
        return steps
    
    def _format_derivative_explanation(self, original: str, result, steps: List[str]) -> str:
        """تنسيق شرح المشتق"""
        explanation = f"""
🧮 **شرح مفصل لحساب المشتق**

📋 **المطلوب:** إيجاد مشتق الدالة f(x) = {original}

🔧 **الخطوات:**
"""
        
        for i, step in enumerate(steps, 1):
            explanation += f"{i}. {step}\n"
        
        explanation += f"""
🎯 **النتيجة النهائية:**
f'(x) = {result}

💡 **نصائح للمراجعة:**
- تأكد من تطبيق القواعد الصحيحة
- راجع كل خطوة للتأكد من الحسابات
- تدرب على أمثلة مشابهة
"""
        
        return explanation
    
    def _format_integral_explanation(self, original: str, result, steps: List[str]) -> str:
        """تنسيق شرح التكامل"""
        explanation = f"""
🧮 **شرح مفصل لحساب التكامل**

📋 **المطلوب:** إيجاد تكامل الدالة ∫{original} dx

🔧 **الخطوات:**
"""
        
        for i, step in enumerate(steps, 1):
            explanation += f"{i}. {step}\n"
        
        explanation += f"""
🎯 **النتيجة النهائية:**
∫{original} dx = {result} + C

💡 **نصائح للمراجعة:**
- تأكد من إضافة ثابت التكامل C
- تحقق من النتيجة بحساب المشتق
- راجع القواعد الأساسية للتكامل
"""
        
        return explanation
    
    def extract_math_from_arabic_text(self, text: str) -> str:
        """استخراج المعادلة الرياضية من النص العربي"""
        import re
        
        # نماذج المعادلات الرياضية
        math_patterns = [
            r'[x-z]\^?[0-9]*[\+\-\*/]*[0-9]*[x-z]*[\+\-\*/]*[0-9]*',  # x^2+3x+1
            r'[0-9]*[x-z][\^\+\-\*/0-9]*[x-z]*[\+\-\*/]*[0-9]*',       # 2x^2+x+5
            r'd/dx\([^)]+\)',                                            # d/dx(...)
            r'∫[^dx]+dx',                                               # ∫f(x)dx
            r'[\+\-]?[0-9]*[x-z]?[\^\+\-\*/0-9x-z\(\)\s]+',            # معادلات عامة
        ]
        
        # البحث عن المعادلات
        for pattern in math_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return max(matches, key=len).strip()
        
        # البحث عن أرقام ومتغيرات
        simple_math = re.findall(r'[0-9x\^\+\-\*/\(\)\s]+', text)
        if simple_math:
            return max(simple_math, key=len).strip()
        
        return text.strip()
    
    def detect_arabic_math_operation(self, text: str) -> str:
        """كشف نوع العملية من النص العربي"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['مشتق', 'اشتقاق', 'مشق']):
            return 'derivative'
        elif any(word in text_lower for word in ['تكامل', 'تكميل']):
            return 'integral'
        elif any(word in text_lower for word in ['حل', 'حال', 'معادلة']):
            return 'solve'
        elif any(word in text_lower for word in ['تبسيط', 'بسط']):
            return 'simplify'
        elif any(word in text_lower for word in ['تحليل']):
            return 'factor'
        elif any(word in text_lower for word in ['توسيع', 'فك']):
            return 'expand'
        elif any(word in text_lower for word in ['رسم', 'ارسم', 'مخطط', 'جراف']):
            return 'plot'
        elif any(word in text_lower for word in ['نهاية', 'حد']):
            return 'limit'
        else:
            return 'evaluate'
    
    def solve_math_problem(self, query: str) -> Dict[str, Any]:
        """حل المسائل الرياضية العامة مع دعم العربية"""
        try:
            # استخراج المعادلة من النص
            math_expression = self.extract_math_from_arabic_text(query)
            
            # كشف نوع العملية
            if is_arabic(query):
                operation = self.detect_arabic_math_operation(query)
            else:
                operation = self.detect_operation(math_expression)
            
            # تطبيع التعبير الرياضي
            normalized = self.normalize_math_expression(math_expression)
            
            # تطبيق العملية المطلوبة
            if operation == 'derivative':
                result = self.solve_derivative(normalized)
                if result.get('success'):
                    result['original_question'] = query
                return result
            elif operation == 'integral':
                result = self.solve_integral(normalized)
                if result.get('success'):
                    result['original_question'] = query
                return result
            elif operation == 'solve':
                return self.solve_equation(normalized)
            elif operation == 'plot':
                return self.plot_function(normalized)
            elif operation == 'matrix':
                return self.solve_matrix(normalized)
            elif operation in ['simplify', 'factor', 'expand']:
                return self.evaluate_expression(normalized, operation)
            else:
                # تقييم عام
                result = self.evaluate_expression(normalized)
                if result.get('success'):
                    result['original_question'] = query
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في حل المسألة الرياضية: {str(e)}'
            }
    
    def evaluate_expression(self, expr_str: str, operation: str = 'evaluate') -> Dict[str, Any]:
        """تقييم التعبيرات الرياضية"""
        try:
            expr = sympify(expr_str)
            
            if operation == 'simplify':
                result = simplify(expr)
                op_name = 'التبسيط'
            elif operation == 'factor':
                result = factor(expr)
                op_name = 'التحليل'
            elif operation == 'expand':
                result = expand(expr)
                op_name = 'التوسيع'
            else:
                # حساب القيمة العددية
                if hasattr(expr, 'evalf'):
                    numeric_result = expr.evalf()
                    # تنظيف الأرقام العشرية الطويلة
                    if numeric_result.is_real and numeric_result.is_finite:
                        # تحويل لـ float ثم إزالة الأصفار الزائدة
                        float_val = float(numeric_result)
                        if float_val == int(float_val):
                            result = int(float_val)
                        else:
                            result = round(float_val, 10)
                            result = f"{result:g}"  # إزالة الأصفار الزائدة
                    else:
                        result = str(numeric_result)
                else:
                    result = expr
                op_name = 'التقييم'
            
            return {
                'success': True,
                'operation': op_name,
                'original': str(expr),
                'result': str(result),
                'latex': latex(result) if hasattr(result, '_latex') else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في {operation}: {str(e)}'
            }

# إنشاء مثيل عام
math_engine = MathEngine()