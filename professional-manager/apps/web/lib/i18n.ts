export type Locale = "ar" | "en";

export const messages = {
  ar: {
    product: "المدير المحترف",
    module: "الجداول الذكية",
    overview: "نظرة عامة",
    data: "البيانات المدرسية",
    assignments: "الإسناد التعليمي",
    rules: "العلاقات والضوابط",
    timetables: "الجداول",
    greeting: "صباح الخير، أ. خالد",
    subtitle: "مدرستك جاهزة لبناء جدول متوازن وقابل للتفسير.",
    setup: "اكتمال تجهيز البيانات",
    launch: "متابعة تجهيز الجدول",
  },
  en: {
    product: "Professional Manager",
    module: "Smart Timetables",
    overview: "Overview",
    data: "School data",
    assignments: "Teaching assignments",
    rules: "Rules & relationships",
    timetables: "Timetables",
    greeting: "Good morning, Khalid",
    subtitle: "Your school is ready for an explainable, balanced timetable.",
    setup: "Data setup progress",
    launch: "Continue timetable setup",
  },
} as const;

