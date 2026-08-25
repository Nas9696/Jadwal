import Link from "next/link";
type Health = { status: string; version: string };
export function Dashboard({ health }: { health: Health | null }) {
  return <div className="content">
    <section className="welcome"><div><p className="eyebrow">مساحة إدارة المدرسة</p><h1>مرحبًا بك في المدير المحترف</h1><p>ابدأ بضبط التقويم والهيكل الدراسي، وستبقى كل البيانات محفوظة للمدرسة المختارة.</p></div><Link className="primary" href="/setup">بدء إعداد المدرسة ←</Link></section>
    <div className={`connection-card ${health ? "online" : "offline"}`}><span>{health ? "✓" : "!"}</span><div><strong>{health ? "الخدمة متصلة وجاهزة" : "تعذر الاتصال بالخدمة"}</strong><p>{health ? `واجهة API الإصدار ${health.version}` : "شغّل خدمة API لبدء حفظ البيانات."}</p></div></div>
    <section className="dashboard-actions"><Link href="/setup"><span>01</span><div><h2>إعداد المدرسة</h2><p>الأعوام، الفصول، الشفتات، أنماط الأسابيع واليوم الدراسي.</p></div><b>ابدأ الآن</b></Link><Link href="/academic-structure"><span>02</span><div><h2>الهيكل الدراسي</h2><p>أنشئ مراحل وصفوفًا وشُعبًا بمسميات تناسب مدرستك.</p></div><b>إدارة الهيكل</b></Link></section>
    <section className="roadmap-card"><div><span className="eyebrow">مسار العمل</span><h2>أساس واضح قبل بناء الجدول</h2><p>ننهي إعداد المدرسة أولًا، ثم ننتقل في مراحل المراجعة القادمة إلى المعلمين والمواد والإسناد.</p></div><ol><li className="active">التقويم واليوم الدراسي</li><li>الهيكل الدراسي</li><li>المعلمون والمواد</li><li>الإسناد والجداول</li></ol></section>
  </div>;
}
