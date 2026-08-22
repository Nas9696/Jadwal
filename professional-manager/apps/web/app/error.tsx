"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="error-state"><h1>تعذر تحميل لوحة الإدارة</h1><p>تحقق من الاتصال ثم أعد المحاولة.</p><button onClick={reset}>إعادة المحاولة</button></main>;
}

