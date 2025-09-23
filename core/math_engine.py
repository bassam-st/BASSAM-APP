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
    ln, log, pi, lambdify
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
        
        # معالجة المسافات (إضافة + للضرب الضمني)
        expr = re.sub(r'(\d+)\s+([a-zA-Z])', r'\1*\2', expr)
        expr = re.sub(r'([a-zA-Z0-9\)])\s+([a-zA-Z])', r'\1 + \2', expr)
        
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
        """حساب المشتق"""
        try:
            expr = sympify(expr_str)
            derivative = diff(expr, x)
            
            return {
                'success': True,
                'operation': 'المشتق',
                'original': str(expr),
                'result': str(derivative),
                'latex': latex(derivative) if hasattr(derivative, '_latex') else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'خطأ في حساب المشتق: {str(e)}'
            }
    
    def solve_integral(self, expr_str: str) -> Dict[str, Any]:
        """حساب التكامل"""
        try:
            expr = sympify(expr_str)
            integral = integrate(expr, x)
            
            return {
                'success': True,
                'operation': 'التكامل',
                'original': str(expr),
                'result': str(integral),
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
            # تنظيف النص
            matrix_str = matrix_str.replace('matrix:', '').strip()
            
            # تحويل إلى مصفوفة SymPy
            matrix = Matrix(eval(matrix_str))
            
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
    
    def solve_math_problem(self, query: str) -> Dict[str, Any]:
        """حل المسائل الرياضية العامة"""
        try:
            # تطبيع النص
            normalized = self.normalize_math_expression(query)
            operation = self.detect_operation(query)
            
            if operation == 'derivative':
                return self.solve_derivative(normalized)
            elif operation == 'integral':
                return self.solve_integral(normalized)
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
                return self.evaluate_expression(normalized)
                
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