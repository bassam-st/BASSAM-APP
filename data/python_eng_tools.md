# أدوات بايثون هندسية
## 1) مشتقات وتكامل (لخدمة المسائل)
```python
import sympy as sp
x = sp.symbols('x')
expr = 3*sp.sin(x) + 2*sp.cos(x)
print("d/dx:", sp.diff(expr, x))
print("∫ dx:", sp.integrate(expr, x))
