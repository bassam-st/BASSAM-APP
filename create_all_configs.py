#!/usr/bin/env python3
"""
إنشاء جميع ملفات الإعداد للنشر المجاني - بسام الذكي
"""

import os
from deploy.free_deployment import free_deployment

def create_deployment_configs():
    """إنشاء جميع ملفات الإعداد"""
    
    print("🔧 إنشاء ملفات الإعداد للنشر المجاني...")
    
    # إنشاء مجلد deploy إذا لم يكن موجوداً
    os.makedirs('deploy', exist_ok=True)
    
    # إنشاء الملفات
    files = free_deployment.create_deployment_files()
    
    created_files = []
    for filename, content in files.items():
        # تحديد المسار
        if filename.startswith('.'):
            filepath = filename  # ملفات الجذر
        elif filename.endswith('.yaml') or filename.endswith('.json'):
            filepath = filename  # ملفات الإعداد
        else:
            filepath = f"deploy/{filename}"
        
        # كتابة الملف
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        created_files.append(filepath)
        print(f"✅ {filepath}")
    
    # إنشاء دليل النشر
    with open('DEPLOYMENT_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(free_deployment.get_deployment_guide())
    
    created_files.append('DEPLOYMENT_GUIDE.md')
    print(f"✅ DEPLOYMENT_GUIDE.md")
    
    print(f"\n🎉 تم إنشاء {len(created_files)} ملف إعداد بنجاح!")
    print("\n📋 الملفات المُنشأة:")
    for file in created_files:
        print(f"   📄 {file}")
    
    print(f"\n🚀 التطبيق جاهز للنشر على جميع المنصات المجانية!")

if __name__ == "__main__":
    create_deployment_configs()