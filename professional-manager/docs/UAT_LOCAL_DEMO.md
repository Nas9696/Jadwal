# UAT المحلي

المتطلب: Windows وDocker Desktop يعملان.

```powershell
cd D:\myapp\jadwal\professional-manager
.\scripts\demo.ps1
```

الرابط: `http://localhost:3000` — لا يوجد تسجيل دخول في Demo الحالي.

```powershell
.\scripts\demo.ps1 -Reset # يعيد بيانات المستأجر التجريبي فقط ثم يشغّل النظام
.\scripts\demo.ps1 -Stop  # يوقف الخدمات ويحفظ قاعدة Demo
```

ترتيب التجربة: المدرسة واليوم الدراسي ← الصفوف والفصول ← المعلمون ← المواد والإسناد ← التوفر والقيود ← إنشاء الجدول (الفحص ثم 3 بدائل ثم الشبكة والمحرر) ← الغياب والبدلاء ← التقارير.
