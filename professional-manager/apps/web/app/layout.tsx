import type { Metadata } from "next";
import "./globals.css";
import "./workspace.css";
import "./dialogs.css";
import "./master-data.css";
import "./membership-repair.css";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "المدير المحترف | الجداول الذكية",
  description: "منصة عربية احترافية لبناء وإدارة الجداول المدرسية الذكية",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ar" dir="rtl"><body><AppShell>{children}</AppShell></body></html>;
}
