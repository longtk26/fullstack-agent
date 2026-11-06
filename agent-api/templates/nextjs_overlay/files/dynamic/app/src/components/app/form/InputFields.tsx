"use client";

import { EyeIcon, EyeOffIcon } from "lucide-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput, InputGroupText } from "@/components/ui/input-group";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { dateLocale } from "../date-locale";
import type { TFieldProps } from "./types";

/** A currency's symbol in the app's locale (`EUR` → `€`). */
function currencySymbol(currency: string): string {
  try {
    const parts = new Intl.NumberFormat(dateLocale.code, { style: "currency", currency }).formatToParts(0);
    return parts.find((part) => part.type === "currency")?.value ?? currency;
  } catch {
    return currency;
  }
}

/** `integer`, `number`, `decimal` (Story 22.5): the contract's limits, a step by type, the currency as a prefix and
 *  a unit as a suffix. */
export function NumberField({ field, id, value, onChange, onBlur, invalid }: TFieldProps) {
  const input = (
    <InputGroupInput
      id={id}
      type="number"
      inputMode={field.type === "integer" ? "numeric" : "decimal"}
      step={field.type === "integer" ? 1 : field.type === "decimal" ? 0.01 : "any"}
      min={field.min}
      max={field.max}
      required={field.required}
      placeholder={field.placeholder}
      aria-invalid={invalid || undefined}
      value={value === undefined || value === null ? "" : String(value)}
      onBlur={onBlur}
      onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
    />
  );
  return (
    <InputGroup>
      {field.currency && (
        <InputGroupAddon>
          <InputGroupText>{currencySymbol(field.currency)}</InputGroupText>
        </InputGroupAddon>
      )}
      {input}
      {field.unit && (
        <InputGroupAddon align="inline-end">
          <InputGroupText>{field.unit}</InputGroupText>
        </InputGroupAddon>
      )}
    </InputGroup>
  );
}

/** `text`: a text area, with a character count when the contract has a `maxLength`. */
export function TextAreaField({ field, id, value, onChange, onBlur, invalid }: TFieldProps) {
  const text = typeof value === "string" ? value : "";
  return (
    <div className="flex flex-col gap-1">
      <Textarea
        id={id}
        rows={4}
        required={field.required}
        maxLength={field.maxLength}
        placeholder={field.placeholder}
        aria-invalid={invalid || undefined}
        aria-describedby={field.maxLength ? `${id}-count` : undefined}
        value={text}
        onBlur={onBlur}
        onChange={(e) => onChange(e.target.value)}
      />
      {field.maxLength && (
        <span id={`${id}-count`} className="self-end text-xs text-muted-foreground tabular-nums" aria-live="polite">
          {text.length} / {field.maxLength}
        </span>
      )}
    </div>
  );
}

/** `password`: a masked input with show / hide. */
function PasswordField({ field, id, value, onChange, onBlur, invalid }: TFieldProps) {
  const [shown, setShown] = useState(false);
  return (
    <InputGroup>
      <InputGroupInput
        id={id}
        type={shown ? "text" : "password"}
        autoComplete="new-password"
        required={field.required}
        maxLength={field.maxLength}
        aria-invalid={invalid || undefined}
        value={typeof value === "string" ? value : ""}
        onBlur={onBlur}
        onChange={(e) => onChange(e.target.value)}
      />
      <InputGroupAddon align="inline-end">
        <InputGroupButton size="xs" aria-label={shown ? "Hide password" : "Show password"} onClick={() => setShown(!shown)}>
          {shown ? <EyeOffIcon aria-hidden /> : <EyeIcon aria-hidden />}
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>
  );
}

const TYPED: Record<string, { type: string; inputMode?: "email" | "url" | "tel"; autoComplete?: string }> = {
  email: { type: "email", inputMode: "email", autoComplete: "email" },
  url: { type: "url", inputMode: "url", autoComplete: "url" },
  tel: { type: "tel", inputMode: "tel", autoComplete: "tel" },
};

/** `string`, `email`, `url`, `tel`, `password`: typed inputs. */
export function TextField(props: TFieldProps) {
  const { field, id, value, onChange, onBlur, invalid } = props;
  if (field.type === "password") return <PasswordField {...props} />;
  const typed = TYPED[field.type] ?? { type: "text" };
  return (
    <Input
      id={id}
      {...typed}
      required={field.required}
      maxLength={field.maxLength}
      placeholder={field.placeholder}
      aria-invalid={invalid || undefined}
      value={typeof value === "string" ? value : ""}
      onBlur={onBlur}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

/** `boolean`: a switch (the form lays it out in a horizontal field, label beside it). */
export function BooleanField({ id, value, onChange, invalid }: TFieldProps) {
  return <Switch id={id} checked={Boolean(value)} aria-invalid={invalid || undefined} onCheckedChange={(checked) => onChange(checked)} />;
}
