import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "المدير المحترف | الجداول الذكية",
  description: "منصة عربية احترافية لبناء وإدارة الجداول المدرسية الذكية",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ar" dir="rtl"><body>{children}</body></html>;
}

