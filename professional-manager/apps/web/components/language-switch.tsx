"use client";

import { useEffect, useState } from "react";
import type { Locale } from "@/lib/i18n";

export function LanguageSwitch() {
  const [locale, setLocale] = useState<Locale>("ar");

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
  }, [locale]);

  return (
    <button className="language" type="button" aria-label="تغيير اللغة إلى الإنجليزية" onClick={() => setLocale(locale === "ar" ? "en" : "ar")}>
      <span aria-hidden="true">文</span> {locale === "ar" ? "English" : "العربية"}
    </button>
  );
}

