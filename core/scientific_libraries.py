"""
مكتبة علمية شاملة لبسام الذكي
تحتوي على أدوات علمية متخصصة في الفيزياء والكيمياء والطب والهندسة
"""

import re
import math
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

@dataclass
class ScientificField:
    """تعريف مجال علمي"""
    name: str
    keywords: List[str]
    formulas: Dict[str, str]
    constants: Dict[str, float]
    units: List[str]

class ScientificLibraries:
    """مكتبة المعرفة العلمية الشاملة"""
    
    def __init__(self):
        self.fields = self._initialize_scientific_fields()
        self.chemistry_data = self._load_chemistry_data()
        self.physics_constants = self._load_physics_constants()
        self.medical_terminology = self._load_medical_terminology()
        self.engineering_formulas = self._load_engineering_formulas()
    
    def _initialize_scientific_fields(self) -> Dict[str, ScientificField]:
        """تهيئة المجالات العلمية"""
        return {
            'physics': ScientificField(
                name="الفيزياء",
                keywords=['فيزياء', 'قوة', 'طاقة', 'سرعة', 'تسارع', 'كتلة', 'ضغط', 'حرارة', 'كهرباء', 'مغناطيس', 'ضوء', 'صوت', 'إشعاع'],
                formulas={
                    'قانون_نيوتن_الثاني': 'F = ma',
                    'طاقة_حركية': 'KE = ½mv²',
                    'طاقة_وضع': 'PE = mgh',
                    'قانون_أوم': 'V = IR',
                    'قانون_الغازات': 'PV = nRT',
                    'معادلة_اينشتاين': 'E = mc²'
                },
                constants={
                    'سرعة_الضوء': 299792458,  # m/s
                    'ثابت_بلانك': 6.626e-34,  # J⋅s
                    'ثابت_الجاذبية': 6.674e-11,  # N⋅m²/kg²
                    'شحنة_الإلكترون': 1.602e-19,  # C
                    'كتلة_الإلكترون': 9.109e-31,  # kg
                    'ثابت_أفوجادرو': 6.022e23   # mol⁻¹
                },
                units=['متر', 'كيلوجرام', 'ثانية', 'أمبير', 'كلفن', 'مول', 'كانديلا', 'جول', 'واط', 'نيوتن']
            ),
            
            'chemistry': ScientificField(
                name="الكيمياء",
                keywords=['كيمياء', 'عنصر', 'مركب', 'تفاعل', 'محلول', 'تركيز', 'حمض', 'قاعدة', 'أكسدة', 'اختزال', 'تحليل', 'تركيب'],
                formulas={
                    'تركيز_مولاري': 'M = n/V',
                    'قانون_الغازات_المثالية': 'PV = nRT',
                    'معادلة_هندرسون': 'pH = pKa + log([A⁻]/[HA])',
                    'طاقة_التنشيط': 'k = Ae^(-Ea/RT)',
                    'قانون_فانت_هوف': 'π = iMRT'
                },
                constants={
                    'ثابت_الغازات': 8.314,      # J/(mol⋅K)
                    'عدد_أفوجادرو': 6.022e23,    # mol⁻¹
                    'ثابت_فاراداي': 96485,       # C/mol
                    'ثابت_ريدبرغ': 1.097e7      # m⁻¹
                },
                units=['مول', 'جرام', 'لتر', 'مليمول', 'مولار', 'عادي', 'بار', 'أتم']
            ),
            
            'medicine': ScientificField(
                name="الطب",
                keywords=['طب', 'مرض', 'دواء', 'علاج', 'تشخيص', 'أعراض', 'فيروس', 'بكتيريا', 'مناعة', 'وراثة', 'جينات', 'خلية'],
                formulas={
                    'مؤشر_كتلة_الجسم': 'BMI = weight(kg) / height(m)²',
                    'معدل_ترشيح_الكلى': 'GFR = (140-age) × weight / (72 × creatinine)',
                    'جرعة_الدواء': 'Dose = weight × mg/kg',
                    'ضغط_الدم_الوسطي': 'MAP = (2×DBP + SBP) / 3'
                },
                constants={
                    'معدل_نبضات_طبيعي': 70,     # beats/min
                    'ضغط_دم_طبيعي': 120,       # mmHg systolic
                    'حرارة_جسم_طبيعية': 37,     # °C
                    'تركيز_جلوكوز_طبيعي': 100  # mg/dL
                },
                units=['ملليجرام', 'ميكروجرام', 'وحدة دولية', 'ميليلتر', 'ملليمول']
            ),
            
            'engineering': ScientificField(
                name="الهندسة",
                keywords=['هندسة', 'مقاومة', 'إجهاد', 'انفعال', 'خرسانة', 'فولاذ', 'تصميم', 'إنشاءات', 'كهرباء', 'ميكانيكا'],
                formulas={
                    'قانون_هوك': 'σ = E × ε',
                    'عزم_الانحناء': 'M = σ × Z',
                    'قوة_القص': 'τ = V × Q / (I × t)',
                    'معامل_الأمان': 'SF = σ_ultimate / σ_working',
                    'ترقق_التيار': 'I = V / R'
                },
                constants={
                    'معامل_يونغ_فولاذ': 200e9,     # Pa
                    'معامل_يونغ_خرسانة': 30e9,    # Pa
                    'كثافة_فولاذ': 7850,          # kg/m³
                    'كثافة_خرسانة': 2400,         # kg/m³
                    'مقاومة_ضغط_خرسانة': 25e6    # Pa
                },
                units=['باسكال', 'ميجاباسكال', 'نيوتن', 'كيلونيوتن', 'متر مكعب', 'متر مربع']
            )
        }
    
    def _load_chemistry_data(self) -> Dict[str, Any]:
        """بيانات كيميائية أساسية"""
        return {
            'periodic_table': {
                'H': {'name': 'هيدروجين', 'atomic_number': 1, 'atomic_weight': 1.008},
                'He': {'name': 'هيليوم', 'atomic_number': 2, 'atomic_weight': 4.003},
                'Li': {'name': 'ليثيوم', 'atomic_number': 3, 'atomic_weight': 6.941},
                'C': {'name': 'كربون', 'atomic_number': 6, 'atomic_weight': 12.011},
                'N': {'name': 'نيتروجين', 'atomic_number': 7, 'atomic_weight': 14.007},
                'O': {'name': 'أكسجين', 'atomic_number': 8, 'atomic_weight': 15.999},
                'Na': {'name': 'صوديوم', 'atomic_number': 11, 'atomic_weight': 22.990},
                'Mg': {'name': 'مغنيسيوم', 'atomic_number': 12, 'atomic_weight': 24.305},
                'Al': {'name': 'ألومنيوم', 'atomic_number': 13, 'atomic_weight': 26.982},
                'Si': {'name': 'سيليكون', 'atomic_number': 14, 'atomic_weight': 28.086},
                'Cl': {'name': 'كلور', 'atomic_number': 17, 'atomic_weight': 35.453},
                'Ca': {'name': 'كالسيوم', 'atomic_number': 20, 'atomic_weight': 40.078},
                'Fe': {'name': 'حديد', 'atomic_number': 26, 'atomic_weight': 55.845},
                'Cu': {'name': 'نحاس', 'atomic_number': 29, 'atomic_weight': 63.546},
                'Ag': {'name': 'فضة', 'atomic_number': 47, 'atomic_weight': 107.868},
                'Au': {'name': 'ذهب', 'atomic_number': 79, 'atomic_weight': 196.967}
            },
            'common_compounds': {
                'H2O': {'name': 'ماء', 'molecular_weight': 18.015},
                'CO2': {'name': 'ثاني أكسيد الكربون', 'molecular_weight': 44.010},
                'NaCl': {'name': 'ملح الطعام', 'molecular_weight': 58.443},
                'CaCO3': {'name': 'كربونات الكالسيوم', 'molecular_weight': 100.087},
                'H2SO4': {'name': 'حمض الكبريتيك', 'molecular_weight': 98.079}
            }
        }
    
    def _load_physics_constants(self) -> Dict[str, Any]:
        """ثوابت فيزيائية مهمة"""
        return {
            'fundamental': {
                'c': {'value': 299792458, 'unit': 'm/s', 'name': 'سرعة الضوء'},
                'h': {'value': 6.626070e-34, 'unit': 'J⋅s', 'name': 'ثابت بلانك'},
                'G': {'value': 6.67430e-11, 'unit': 'N⋅m²/kg²', 'name': 'ثابت الجاذبية'},
                'e': {'value': 1.602176e-19, 'unit': 'C', 'name': 'شحنة الإلكترون'},
                'me': {'value': 9.109384e-31, 'unit': 'kg', 'name': 'كتلة الإلكترون'},
                'mp': {'value': 1.672622e-27, 'unit': 'kg', 'name': 'كتلة البروتون'}
            },
            'derived': {
                'k_e': {'value': 8.987551e9, 'unit': 'N⋅m²/C²', 'name': 'ثابت كولوم'},
                'μ_0': {'value': 4*math.pi*1e-7, 'unit': 'H/m', 'name': 'نفاذية الفراغ'},
                'ε_0': {'value': 8.854188e-12, 'unit': 'F/m', 'name': 'سماحية الفراغ'}
            }
        }
    
    def _load_medical_terminology(self) -> Dict[str, Any]:
        """مصطلحات طبية أساسية"""
        return {
            'vital_signs': {
                'heart_rate': {'normal_range': (60, 100), 'unit': 'bpm', 'name': 'معدل النبض'},
                'blood_pressure': {'normal_systolic': (90, 120), 'normal_diastolic': (60, 80), 'unit': 'mmHg', 'name': 'ضغط الدم'},
                'body_temperature': {'normal_range': (36.1, 37.2), 'unit': '°C', 'name': 'درجة الحرارة'},
                'respiratory_rate': {'normal_range': (12, 20), 'unit': 'breaths/min', 'name': 'معدل التنفس'}
            },
            'lab_values': {
                'glucose': {'normal_fasting': (70, 100), 'unit': 'mg/dL', 'name': 'الجلوكوز'},
                'cholesterol': {'normal_total': (0, 200), 'unit': 'mg/dL', 'name': 'الكوليسترول'},
                'hemoglobin': {'normal_male': (13.8, 17.2), 'normal_female': (12.1, 15.1), 'unit': 'g/dL', 'name': 'الهيموجلوبين'}
            }
        }
    
    def _load_engineering_formulas(self) -> Dict[str, Any]:
        """معادلات هندسية متقدمة"""
        return {
            'structural': {
                'beam_deflection': 'δ = (5wL⁴)/(384EI)',
                'column_buckling': 'P_cr = (π²EI)/(KL)²',
                'stress': 'σ = F/A',
                'strain': 'ε = ΔL/L'
            },
            'fluid_mechanics': {
                'reynolds_number': 'Re = ρVD/μ',
                'bernoulli_equation': 'P₁ + ½ρV₁² + ρgh₁ = P₂ + ½ρV₂² + ρgh₂',
                'darcy_weisbach': 'hf = f(L/D)(V²/2g)'
            },
            'thermodynamics': {
                'ideal_gas': 'PV = nRT',
                'heat_transfer': 'Q = mcΔT',
                'efficiency': 'η = W_out/Q_in'
            }
        }
    
    def detect_scientific_field(self, question: str) -> Optional[str]:
        """كشف المجال العلمي للسؤال"""
        question_lower = question.lower()
        
        field_scores = {}
        for field_name, field_data in self.fields.items():
            score = 0
            for keyword in field_data.keywords:
                if keyword in question_lower:
                    score += 1
            field_scores[field_name] = score
        
        if max(field_scores.values()) > 0:
            return max(field_scores, key=field_scores.get)
        
        return None
    
    def get_scientific_context(self, field: str, question: str) -> Dict[str, Any]:
        """الحصول على السياق العلمي للمجال"""
        if field not in self.fields:
            return {}
        
        field_data = self.fields[field]
        context = {
            'field_name': field_data.name,
            'relevant_formulas': [],
            'relevant_constants': [],
            'relevant_units': field_data.units
        }
        
        question_lower = question.lower()
        
        # البحث عن معادلات ذات صلة
        for formula_name, formula in field_data.formulas.items():
            if any(keyword in question_lower for keyword in formula_name.split('_')):
                context['relevant_formulas'].append({
                    'name': formula_name.replace('_', ' '),
                    'formula': formula
                })
        
        # البحث عن ثوابت ذات صلة
        for const_name, const_value in field_data.constants.items():
            if any(keyword in question_lower for keyword in const_name.split('_')):
                context['relevant_constants'].append({
                    'name': const_name.replace('_', ' '),
                    'value': const_value
                })
        
        return context
    
    def search_element(self, query: str) -> Optional[Dict[str, Any]]:
        """البحث عن عنصر كيميائي"""
        query_lower = query.lower()
        
        for symbol, data in self.chemistry_data['periodic_table'].items():
            if (symbol.lower() == query_lower or 
                data['name'] in query_lower or 
                str(data['atomic_number']) == query):
                return {
                    'symbol': symbol,
                    'name': data['name'],
                    'atomic_number': data['atomic_number'],
                    'atomic_weight': data['atomic_weight'],
                    'type': 'element'
                }
        
        return None
    
    def search_compound(self, query: str) -> Optional[Dict[str, Any]]:
        """البحث عن مركب كيميائي"""
        query_upper = query.upper()
        
        for formula, data in self.chemistry_data['common_compounds'].items():
            if (formula == query_upper or 
                data['name'] in query.lower()):
                return {
                    'formula': formula,
                    'name': data['name'],
                    'molecular_weight': data['molecular_weight'],
                    'type': 'compound'
                }
        
        return None
    
    def get_physics_constant(self, query: str) -> Optional[Dict[str, Any]]:
        """البحث عن ثابت فيزيائي"""
        query_lower = query.lower()
        
        all_constants = {**self.physics_constants['fundamental'], 
                        **self.physics_constants['derived']}
        
        for symbol, data in all_constants.items():
            if (symbol.lower() in query_lower or 
                any(word in query_lower for word in data['name'].split())):
                return {
                    'symbol': symbol,
                    'value': data['value'],
                    'unit': data['unit'],
                    'name': data['name']
                }
        
        return None
    
    def analyze_medical_values(self, value_type: str, value: float) -> Dict[str, Any]:
        """تحليل القيم الطبية"""
        if value_type not in self.medical_terminology['vital_signs'] and \
           value_type not in self.medical_terminology['lab_values']:
            return {'error': 'نوع القيمة غير معروف'}
        
        # فحص العلامات الحيوية
        if value_type in self.medical_terminology['vital_signs']:
            data = self.medical_terminology['vital_signs'][value_type]
            if 'normal_range' in data:
                min_val, max_val = data['normal_range']
                if min_val <= value <= max_val:
                    status = 'طبيعي'
                elif value < min_val:
                    status = 'أقل من الطبيعي'
                else:
                    status = 'أعلى من الطبيعي'
                
                return {
                    'value': value,
                    'unit': data['unit'],
                    'name': data['name'],
                    'status': status,
                    'normal_range': f"{min_val}-{max_val}",
                    'recommendation': self._get_medical_recommendation(value_type, status)
                }
        
        return {'error': 'لا يمكن تحليل هذه القيمة'}
    
    def _get_medical_recommendation(self, value_type: str, status: str) -> str:
        """الحصول على توصية طبية"""
        recommendations = {
            'heart_rate': {
                'أقل من الطبيعي': 'قد يحتاج لفحص طبي لاستبعاد بطء القلب',
                'أعلى من الطبيعي': 'قد يحتاج لفحص طبي لاستبعاد تسرع القلب',
                'طبيعي': 'المعدل طبيعي'
            },
            'blood_pressure': {
                'أقل من الطبيعي': 'قد يشير لانخفاض ضغط الدم',
                'أعلى من الطبيعي': 'قد يشير لارتفاع ضغط الدم - ينصح بمراجعة الطبيب',
                'طبيعي': 'الضغط طبيعي'
            }
        }
        
        return recommendations.get(value_type, {}).get(status, 'ينصح بمراجعة الطبيب للتقييم')
    
    def generate_scientific_explanation(self, field: str, topic: str) -> str:
        """توليد شرح علمي متخصص"""
        if field not in self.fields:
            return "المجال العلمي غير مدعوم"
        
        field_data = self.fields[field]
        
        explanation = f"""📚 **شرح علمي متخصص في {field_data.name}**

🔬 **الموضوع:** {topic}

"""
        
        # إضافة المعادلات ذات الصلة
        relevant_formulas = []
        for formula_name, formula in field_data.formulas.items():
            if any(word in topic.lower() for word in formula_name.split('_')):
                relevant_formulas.append(f"• {formula_name.replace('_', ' ')}: {formula}")
        
        if relevant_formulas:
            explanation += "📐 **المعادلات ذات الصلة:**\n"
            explanation += "\n".join(relevant_formulas) + "\n\n"
        
        # إضافة الثوابت ذات الصلة
        relevant_constants = []
        for const_name, const_value in field_data.constants.items():
            if any(word in topic.lower() for word in const_name.split('_')):
                relevant_constants.append(f"• {const_name.replace('_', ' ')}: {const_value}")
        
        if relevant_constants:
            explanation += "🔢 **الثوابت المهمة:**\n"
            explanation += "\n".join(relevant_constants) + "\n\n"
        
        # إضافة الوحدات
        explanation += f"📏 **الوحدات المستخدمة:** {', '.join(field_data.units[:5])}"
        
        return explanation

# إنشاء مثيل عام للاستخدام
scientific_libraries = ScientificLibraries()