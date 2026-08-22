# المدير المحترف | Professional Manager

أساس المنصة العربية لإدارة المدرسة. ينفذ PM-001 مساحة عمل مستقلة تحت `professional-manager/` مع إبقاء أدوات المستودع القديمة كما هي.

## ما يتضمنه الأساس

- `apps/web`: Next.js وTypeScript، واجهة عربية RTL افتراضية، مبدّل لغة أولي، حالات تحميل/خطأ، واتصال بـ API health.
- `apps/api`: FastAPI وPydantic v2 وSQLAlchemy 2، API بإصدار `/api/v1`، إعدادات بيئة وعزل أولي للمستأجر عبر `X-Tenant-ID`.
- `scheduler`: عقود typed مستقلة للحل والإصلاح والتشخيص والبدائل. حدّ CP-SAT موجود، لكن نموذج OR-Tools غير منفذ في PM-001 ولا يرجع نتائج وهمية.
- PostgreSQL وAlembic ومهاجرة تأسيسية وبيانات عرض عربية آمنة لإعادة التشغيل.
- اختبارات API وعزل مستأجر، اختبارات عقود Scheduler، واختبار RTL للواجهة.

## التشغيل السريع عبر Docker

```bash
cp .env.example .env
docker compose up --build
```

على PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

ثم افتح:

- Web: http://localhost:3000
- API docs: http://localhost:8000/api/v1/docs
- API health: http://localhost:8000/api/v1/health

تطبق خدمة API المهاجرات وتضيف demo تلقائيًا. معرّف مستأجر العرض هو `00000000-0000-4000-8000-000000000001` ويستخدم في طلبات البيانات عبر `X-Tenant-ID`.

## التشغيل المحلي دون Docker

يتطلب Node.js 22+، Python 3.12 أو 3.13، وPostgreSQL 16+.

```powershell
npm install
npm run dev

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r apps/api/requirements-dev.txt
$env:PYTHONPATH="apps/api;scheduler"
alembic -c apps/api/alembic.ini upgrade head
uvicorn app.main:app --app-dir apps/api --reload
```

## التحقق والجودة

```powershell
npm run lint
npm run typecheck
npm run test:web
python -m ruff check apps/api scheduler
python -m mypy apps/api/app scheduler/pm_scheduler
python -m pytest
```

## مخطط البيانات في PM-001

المهاجرة الأولى تنشئ: tenant، user، tenant_membership، school_complex، school، academic_year، term، teacher، teacher_school_membership، subject، stage، grade، section، resource (غرفة/معمل/مورد)، week_pattern، period_template، teaching_assignment، teaching_assignment_teacher، rule، timetable_project، timetable_project_school. كل سجل متغير في النطاق يحمل `tenant_id`، وتتحقق استعلامات API منه على الخادم. عضوية المستخدم تفصل الهوية العالمية عن دوره وصلاحياته داخل كل مستأجر.

المعلم هو هوية canonical على مستوى المستأجر، وتربطه عضويات relational بأي عدد من المدارس دون تكرار الشخص. مشروع الجدول يملك نطاق مدارس relational ويمكن أن يغطي مدرسة واحدة أو مجمعًا أو مجموعة مدارس، وتحمل كل علاقة مدرسة داخل المشروع `term_id` صالحًا لتلك المدرسة.

كل `PeriodTemplate` مرتبط صراحة بمدرسة و`WeekPattern` من المدرسة نفسها، ويحمل نمط الأسبوع `cycle_week_index` محليًا للمدرسة. قبل المحرك تُحسب دورة المشروع العالمية بـ LCM لأطوال دورات المدارس (بحد 12 أسبوعًا افتراضيًا)، ثم تتوسع الفترات المحلية إلى `project_cycle_week_index`. تعارض المعلم يعتمد فقط على الأسبوع العالمي و`weekday_index` الموحد وتداخل `[starts_at_minute, ends_at_minute)`، وليس على الفهرس المحلي أو اسم اليوم أو رقم الحصة أو نمط الحضور.

مسارات الكتابة التأسيسية لعضوية المعلم ونطاق مشروع الجدول تتحقق من انتماء جميع المراجع للمستأجر النشط. هيدر `X-Tenant-ID` سياق تطوير فقط وليس مصادقة أو حدًا أمنيًا.

`teacher.specialty_reference` مرجع وصفي فقط، ولا يدخل كقيد إسناد. قواعد الجدولة مخزنة بنموذج عام (`severity`, `rule_type`, selectors, parameters) وليست أعمدة منطقية متفرقة.

## حدود PM-001 المقصودة

- المصادقة وRBAC الكاملان وقاعدة إعداد المدرسة CRUD ضمن المراحل اللاحقة؛ هيدر المستأجر الحالي أساس واختبار عزل، وليس بديلًا عن هوية موثقة.
- محرك CP-SAT الفعلي والـ preflight والوظائف غير المتزامنة ليست مدّعاة في هذه المهمة. العقود مهيأة لها فقط.
- مبدّل اللغة يثبت آلية الاتجاه واللغة؛ استكمال ترجمة كل النصوص يأتي مع نظام localization الأوسع.
- لا يوجد scraping أو تكامل غير رسمي مع نور أو مدرستي.
