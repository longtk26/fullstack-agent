"use client";

import { Controller, get } from "react-hook-form";
import { Section } from "@/components/layout/Section";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { TFormDef } from "@/components/renderer/site";
import { useSectionForm } from "@/components/renderer/use-section-form";
import { toNumber } from "@/lib/form-utils";
import type { TFormContent } from "./types";

type FormProps = TFormContent & {
  formId?: string;
  form?: TFormDef;
};

const INPUT_TYPES: Record<string, string> = {
  string: "text",
  email: "email",
  url: "url",
  tel: "tel",
  password: "password",
  integer: "number",
  number: "number",
  decimal: "number",
  date: "date",
};
const NUMBERS = new Set(["integer", "number", "decimal"]);

/** A FrontendSpec form from its field definitions; validation from the generated Zod schema. */
export function Form({ title, description, formId = "", form }: FormProps) {
  const { methods, onSubmit, pending, isLoading } = useSectionForm(formId, form ?? { params: {}, fields: [], submitLabel: "Submit", onSuccess: {} });

  if (isLoading) {
    return (
      <Section title={title} description={description}>
        <div className="flex max-w-lg flex-col gap-4 py-8">
          <p className="text-sm text-muted-foreground">Loading…</p>
        </div>
      </Section>
    );
  }

  return (
    <Section title={title} description={description}>
      <form onSubmit={methods.handleSubmit(onSubmit)} className="flex max-w-lg flex-col gap-4" noValidate>
        {(form?.fields ?? [])
          .filter((field) => !field.hidden)
          .map((field) => {
            const id = `${formId}-${field.name}`;
            const message = (get(methods.formState.errors, field.name) as { message?: string } | undefined)?.message;
            return (
              <Field key={field.name} data-invalid={Boolean(message)}>
                <FieldLabel htmlFor={id}>{field.label}</FieldLabel>
                {field.type === "text" ? (
                  <Textarea id={id} placeholder={field.placeholder} aria-invalid={Boolean(message)} {...methods.register(field.name)} />
                ) : field.type === "enum" ? (
                  <Controller
                    control={methods.control}
                    name={field.name}
                    render={({ field: control }) => (
                      <Select value={(control.value as string | undefined) ?? null} onValueChange={control.onChange}>
                        <SelectTrigger id={id} className="w-full">
                          <SelectValue placeholder="Choose…" />
                        </SelectTrigger>
                        <SelectContent>
                          {(field.values ?? []).map((value) => (
                            <SelectItem key={value} value={value}>
                              {value.replaceAll("_", " ").toLowerCase()}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                ) : field.type === "boolean" ? (
                  <Controller
                    control={methods.control}
                    name={field.name}
                    render={({ field: control }) => (
                      <Checkbox id={id} checked={Boolean(control.value)} onCheckedChange={(checked) => control.onChange(checked === true)} />
                    )}
                  />
                ) : (
                  <Input
                    id={id}
                    type={INPUT_TYPES[field.type] ?? "text"}
                    step={field.type === "decimal" ? "any" : undefined}
                    placeholder={field.placeholder}
                    aria-invalid={Boolean(message)}
                    {...methods.register(field.name, NUMBERS.has(field.type) ? { setValueAs: toNumber } : {})}
                  />
                )}
                {message && <FieldError>{message}</FieldError>}
              </Field>
            );
          })}
        <div>
          <Button type="submit" disabled={pending}>
            {form?.submitLabel ?? "Submit"}
          </Button>
        </div>
      </form>
    </Section>
  );
}
