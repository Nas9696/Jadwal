import {
  AcademicCapIcon,
  AdjustmentsHorizontalIcon,
  ArrowLeftIcon,
  BellIcon,
  BookOpenIcon,
  BuildingLibraryIcon,
  CalendarDaysIcon,
  ChartBarSquareIcon,
  CheckCircleIcon,
  ClockIcon,
  HomeIcon,
  RectangleGroupIcon,
  SparklesIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";
import { LanguageSwitch } from "./language-switch";

type Health = { status: string; version: string };

const nav = [
  [HomeIcon, "نظرة عامة", true], [BuildingLibraryIcon, "البيانات المدرسية", false],
  [AcademicCapIcon, "المعلمون والمواد", false], [BookOpenIcon, "الإسناد التعليمي", false],
  [AdjustmentsHorizontalIcon, "العلاقات والضوابط", false], [CalendarDaysIcon, "الجداول", false],
  [UserGroupIcon, "المستخدمون والصلاحيات", false], [ChartBarSquareIcon, "التقارير", false],
] as const;

const stats = [
  [UserGroupIcon, "المعلمون", "48", "تم إدخال النصاب لـ 42 معلمًا", "blue"],
  [BookOpenIcon, "المواد", "24", "3 مواد تحتاج مراجعة", "violet"],
  [RectangleGroupIcon, "الشعب", "18", "4 مراحل تعليمية", "green"],
  [ClockIcon, "الحصص الأسبوعية", "612", "اكتمل إسناد 86%", "amber"],
] as const;

export function Dashboard({ health }: { health: Health | null }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><SparklesIcon /></div><div><strong>المدير المحترف</strong><span>الجداول الذكية</span></div></div>
        <nav aria-label="التنقل الرئيسي">
          {nav.map(([Icon, label, active]) => <a key={label} href="#" className={active ? "active" : ""} aria-current={active ? "page" : undefined}><Icon />{label}</a>)}
        </nav>
        <div className="sidebar-card"><SparklesIcon /><strong>مركز المساعدة</strong><p>دليل سريع لإعداد أول جدول مدرسي باحترافية.</p><button>استعراض الدليل</button></div>
        <div className="profile"><div className="avatar">خ ع</div><div><strong>خالد العتيبي</strong><span>مدير النظام</span></div><span className="more">•••</span></div>
      </aside>

      <main>
        <header><div className="school"><div className="school-icon"><BuildingLibraryIcon /></div><div><strong>مجمع الآفاق التعليمي</strong><span>العام الدراسي 1448 هـ · الفصل الأول</span></div></div><div className="header-actions"><span className={`api-status ${health?.status === "ok" ? "online" : "offline"}`} title={health ? `API v${health.version}` : "API غير متصل"}>{health ? "النظام متصل" : "وضع المعاينة"}</span><LanguageSwitch /><button className="icon-button" aria-label="الإشعارات"><BellIcon /><i /></button></div></header>

        <div className="content">
          <section className="welcome"><div><p className="eyebrow">لوحة إدارة المدرسة</p><h1>صباح الخير، أ. خالد <span>👋</span></h1><p>مدرستك جاهزة لبناء جدول متوازن وقابل للتفسير.</p></div><button className="primary"><span>متابعة تجهيز الجدول</span><ArrowLeftIcon /></button></section>

          <section className="stats" aria-label="إحصاءات المدرسة">
            {stats.map(([Icon, label, value, note, color]) => <article key={label}><div className={`stat-icon ${color}`}><Icon /></div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>)}
          </section>

          <div className="dashboard-grid">
            <section className="panel progress-panel"><div className="panel-heading"><div><h2>جاهزية البيانات</h2><p>أكمل الخطوات المتبقية قبل إنشاء الجدول</p></div><strong>72%</strong></div><div className="progress"><i /></div>
              <ul>
                <li className="done"><CheckCircleIcon /><div><strong>بيانات المدرسة والفترات</strong><span>تم إعداد أيام الدوام وأوقات الحصص</span></div><b>مكتمل</b></li>
                <li className="done"><CheckCircleIcon /><div><strong>المعلمون والمواد</strong><span>48 معلمًا · 24 مادة</span></div><b>مكتمل</b></li>
                <li><span className="step">3</span><div><strong>الإسناد التعليمي</strong><span>تبقى إسناد 86 حصة أسبوعية</span></div><button>متابعة</button></li>
                <li><span className="step">4</span><div><strong>العلاقات والضوابط</strong><span>حدد تفضيلات مدرستك والقيود الإلزامية</span></div><span>لم يبدأ</span></li>
              </ul>
            </section>

            <section className="panel activity"><div className="panel-heading"><div><h2>آخر النشاطات</h2><p>أحدث التغييرات في مساحة العمل</p></div><button className="text-button">عرض الكل</button></div>
              <ul><li><span className="activity-icon blue"><UserGroupIcon /></span><div><strong>تم استيراد بيانات المعلمين</strong><p>أضافت سارة القحطاني 12 معلمًا</p><time>منذ 18 دقيقة</time></div></li><li><span className="activity-icon violet"><AdjustmentsHorizontalIcon /></span><div><strong>تحديث ضابط دراسي</strong><p>لا تزيد حصص الرياضيات عن حصتين متتاليتين</p><time>منذ ساعة</time></div></li><li><span className="activity-icon green"><CheckCircleIcon /></span><div><strong>اكتمال إعداد الفترات</strong><p>تم اعتماد جدول أوقات الفترة الصباحية</p><time>أمس، 2:30 م</time></div></li></ul>
            </section>
          </div>

          <section className="tip"><div className="tip-icon"><SparklesIcon /></div><div><strong>نصيحة ذكية</strong><p>يمكنك إدخال القيود بلغة مدرسية بسيطة، مثل: «لا تضع للمعلم أكثر من ثلاث حصص متتالية». سنعرض أثرها قبل اعتمادها.</p></div><button>جرّب لاحقًا</button></section>
        </div>
      </main>
    </div>
  );
}

