"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LanguageSwitch } from "./language-switch";
import { setupApi, type School } from "@/lib/setup-api";

const nav = [
  ["/", "الرئيسية"], ["/setup", "إعداد المدرسة"], ["/academic-structure", "الهيكل الدراسي"],
  ["/teachers", "المعلمون"], ["/subjects-resources", "المواد والموارد"], ["/assignments", "الإسناد"], ["/timetables", "الجداول الذكية"],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter();
  const [schools, setSchools] = useState<School[]>([]);
  const [schoolId, setSchoolId] = useState("");
  useEffect(() => { setupApi.schools().then((rows) => { setSchools(rows); const saved = localStorage.getItem("pm-school"); const selected = rows.find((x) => x.id === saved)?.id ?? rows[0]?.id ?? ""; setSchoolId(selected); if (selected) { localStorage.setItem("pm-school", selected); window.dispatchEvent(new CustomEvent("pm-school-change", { detail: selected })); } }).catch(() => setSchools([])); }, []);
  function changeSchool(id: string) { setSchoolId(id); localStorage.setItem("pm-school", id); window.dispatchEvent(new CustomEvent("pm-school-change", { detail: id })); router.refresh(); }
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">م</div><div><strong>المدير المحترف</strong><span>الجداول الذكية</span></div></div>
      <nav aria-label="التنقل الرئيسي">{nav.map(([href, label], index) => <Link className={pathname === href ? "active" : ""} href={href} key={href}><span aria-hidden="true">{["⌂","⚙","▦","♙","◇","↔","✦"][index]}</span>{label}{index > 4 && <small>قريبًا</small>}</Link>)}</nav>
      <div className="profile"><div className="avatar">مد</div><div><strong>مدير المدرسة</strong><span>صلاحية الإدارة</span></div></div>
    </aside>
    <main><header><label className="school-picker"><span>المدرسة الحالية</span><select aria-label="اختيار المدرسة" value={schoolId} onChange={(e) => changeSchool(e.target.value)}>{schools.length ? schools.map((s) => <option key={s.id} value={s.id}>{s.name_ar}</option>) : <option>لا توجد مدارس</option>}</select></label><div className="header-actions"><LanguageSwitch /></div></header>{children}</main>
  </div>;
}
