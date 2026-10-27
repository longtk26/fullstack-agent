"use client";

import { Controller, get, type FieldValues, type Path, type UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toNumber } from "@/lib/form-utils";

export type TFormFieldDef = {
  name: string;
  label: string;
  type: "string" | "text" | "email" | "integer" | "number" | "date" | "enum";
  values?: readonly string[];
};

type FormProps<TValues extends FieldValues> = {
  form: UseFormReturn<TValues>;
  fields: TFormFieldDef[];
  submitLabel: string;
  pending?: boolean;
  title?: string;
  onSubmit: (values: TValues) => void;
};

const INPUT_TYPES = { string: "text", email: "email", integer: "number", number: "number", date: "date" } as const;

/** A FrontendSpec form rendered from field definitions; validation comes from the form's Zod schema. */
export function Form<TValues extends FieldValues>({ form, fields, submitLabel, pending, title, onSubmit }: FormProps<TValues>) {
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="flex max-w-lg flex-col gap-4" noValidate>
      {title && <h2 className="text-lg font-semibold">{title}</h2>}
      {fields.map((field) => {
        const name = field.name as Path<TValues>;
        const id = `field-${field.name}`;
        const message = (get(form.formState.errors, field.name) as { message?: string } | undefined)?.message;
        return (
          <Field key={field.name} data-invalid={Boolean(message)}>
            <FieldLabel htmlFor={id}>{field.label}</FieldLabel>
            {field.type === "text" ? (
              <Textarea id={id} aria-invalid={Boolean(message)} {...form.register(name)} />
            ) : field.type === "enum" ? (
              <Controller
                control={form.control}
                name={name}
                render={({ field: control }) => (
                  <Select value={control.value ?? null} onValueChange={control.onChange}>
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
            ) : (
              <Input
                id={id}
                type={INPUT_TYPES[field.type]}
                aria-invalid={Boolean(message)}
                {...form.register(name, field.type === "integer" || field.type === "number" ? { setValueAs: toNumber } : {})}
              />
            )}
            {message && <FieldError>{message}</FieldError>}
          </Field>
        );
      })}
      <div>
        <Button type="submit" disabled={pending}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
