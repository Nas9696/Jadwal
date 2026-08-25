"use client";

import { ChangeEvent, InputHTMLAttributes, useState } from "react";

const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
const easternDigits = "۰۱۲۳۴۵۶۷۸۹";

function toWestern(value: string) {
  return value.replace(/[٠-٩۰-۹]/g, (digit) => {
    const arabic = arabicDigits.indexOf(digit);
    return String(arabic >= 0 ? arabic : easternDigits.indexOf(digit));
  }).replace(/[^0-9.-]/g, "");
}

function toArabic(value: string) {
  return value.replace(/\d/g, (digit) => arabicDigits[Number(digit)]);
}

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "defaultValue"> & { value?: string | number; defaultValue?: string | number };

export function ArabicNumberInput({ name, value, defaultValue, onChange, ...props }: Props) {
  const controlled = value !== undefined;
  const [internal, setInternal] = useState(() => toWestern(String(defaultValue ?? "")));
  const western = controlled ? toWestern(String(value ?? "")) : internal;
  function change(event: ChangeEvent<HTMLInputElement>) {
    const next = toWestern(event.currentTarget.value);
    if (!controlled) setInternal(next);
    event.currentTarget.value = next;
    onChange?.(event);
  }
  return <><input {...props} type="text" inputMode="numeric" value={toArabic(western)} onChange={change}/>{name&&<input type="hidden" name={name} value={western}/>}</>;
}
