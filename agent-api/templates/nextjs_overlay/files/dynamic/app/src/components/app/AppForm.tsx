"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { compactValues } from "@/lib/form-utils";
import { app, pageHref, resolveParams, type TAppSection, type TFormField, type TRouteParams } from "./app";
import { useOperationMutation, useOperationQuery } from "./bindings";
import { errorMessage, fieldErrors } from "./errors";
import { formSchemas } from "./form-schemas";

type TValues = Record<string, unknown>;

function enumLabel(value: string): string {
  const words = value.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function FieldInput({ field, id, value, onChange, invalid }: {
  field: TFormField;
  id: string;
  value: unknown;
  onChange: (value: unknown) => void;
  invalid: boolean;
}) {
  const common = { id, "aria-invalid": invalid || undefined, required: field.required };
  switch (field.type) {
    case "text":
      return <Textarea {...common} rows={4} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "boolean":
      return <Switch id={id} checked={Boolean(value)} onCheckedChange={(checked) => onChange(checked)} />;
    case "enum":
      return (
        <Select
          items={Object.fromEntries((field.values ?? []).map((option) => [option, enumLabel(option)]))}
          value={(value as string) ?? null}
          onValueChange={(next) => onChange(next ?? undefined)}
        >
          <SelectTrigger id={id} className="w-full" aria-invalid={invalid || undefined}>
            <SelectValue placeholder="Choose…" />
          </SelectTrigger>
          <SelectContent>
            {(field.values ?? []).map((option) => (
              <SelectItem key={option} value={option}>
                {enumLabel(option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    case "integer":
    case "number":
    case "decimal":
      return (
        <Input
          {...common}
          type="number"
          inputMode={field.type === "integer" ? "numeric" : "decimal"}
          step={field.type === "integer" ? 1 : "any"}
          min={field.min}
          max={field.max}
          value={value === undefined || value === null ? "" : String(value)}
          onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
        />
      );
    case "date":
      return <Input {...common} type="date" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || undefined)} />;
    case "datetime":
      return (
        <Input
          {...common}
          type="datetime-local"
          value={typeof value === "string" ? value.slice(0, 16) : ""}
          onChange={(e) => onChange(e.target.value ? new Date(e.target.value).toISOString() : undefined)}
        />
      );
    default:
      return (
        <Input
          {...common}
          type={field.type === "email" ? "email" : field.type === "url" ? "url" : field.type === "password" ? "password" : "text"}
          maxLength={field.maxLength}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
  }
}

type AppFormBodyProps = {
  formId: string;
  /** The operation's path parameters, resolved (a dialog on a record's page passes the record's). */
  params?: Record<string, unknown>;
  onDone?: (result: unknown) => void;
  onCancel?: () => void;
};

/** A form on its operation's request (Story 22.3 writes the fields; Story 22.5 brings the full form kit): the
 *  generated Zod schema validates, hidden fields take their route values, an edit form loads its record, and server
 *  errors show on their field (else a toast). */
export function AppFormBody({ formId, params, onDone, onCancel }: AppFormBodyProps) {
  const form = app.forms[formId];
  const route = (useParams() ?? {}) as TRouteParams;
  const schema = formSchemas[formId];
  const fixed = useMemo(
    () =>
      resolveParams(
        Object.fromEntries((form?.fields ?? []).filter((f) => f.value !== undefined).map((f) => [f.name, f.value])),
        route,
      ),
    [form, route],
  );
  const defaults = useMemo(() => ({ ...(schema?.defaults ?? {}), ...fixed }), [schema, fixed]);
  const methods = useForm<TValues>({
    resolver: schema ? zodResolver(schema.schema as never) : undefined,
    defaultValues: defaults,
  });
  const load = useOperationQuery(form?.load?.operationId, resolveParams(form?.load?.params, route));
  const mutation = useOperationMutation(form?.operationId);

  useEffect(() => {
    if (load.data && typeof load.data === "object") {
      // An empty optional field arrives as `null`; the form (and its schema) treat it as not given.
      const loaded = Object.entries(load.data as TValues).filter(([, value]) => value !== null);
      methods.reset({ ...defaults, ...Object.fromEntries(loaded) });
    }
  }, [load.data, defaults, methods]);

  if (!form) return null;
  if (form.load && load.isLoading) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        {form.fields.slice(0, 4).map((field) => (
          <Skeleton key={field.name} className="h-14 w-full" />
        ))}
      </div>
    );
  }
  const visible = form.fields.filter((field) => !field.hidden);
  const names = form.fields.map((field) => field.name);

  function onSubmit(values: TValues) {
    const patch = Boolean(form.load);
    const dirty = methods.formState.dirtyFields as Record<string, unknown>;
    const body = patch
      ? Object.fromEntries(Object.entries(values).filter(([name]) => dirty[name] && names.includes(name)))
      : compactValues(Object.fromEntries(Object.entries(values).filter(([name]) => names.includes(name))));
    mutation.mutate(
      { params: params ?? resolveParams(form.params, route), body },
      {
        onSuccess: (result) => {
          if (form.onSuccess?.toast) toast.success(form.onSuccess.toast);
          onDone?.(result);
        },
        onError: (error) => {
          const byField = fieldErrors(form.operationId, error, names);
          for (const [name, message] of Object.entries(byField)) methods.setError(name, { message });
          if (Object.keys(byField).length === 0) toast.error(errorMessage(form.operationId, error));
        },
      },
    );
  }

  return (
    <form onSubmit={methods.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
      <FieldGroup>
        {visible.map((field) => {
          const id = `${formId}-${field.name}`;
          return (
            <Controller
              key={field.name}
              control={methods.control}
              name={field.name}
              render={({ field: control, fieldState }) => (
                <Field orientation={field.type === "boolean" ? "horizontal" : "vertical"} data-invalid={fieldState.invalid || undefined}>
                  <FieldLabel htmlFor={id}>
                    {field.label ?? field.name}
                    {field.required && <span className="text-destructive" aria-hidden> *</span>}
                  </FieldLabel>
                  <FieldInput field={field} id={id} value={control.value} onChange={control.onChange} invalid={fieldState.invalid} />
                  {fieldState.error?.message ? (
                    <FieldError>{fieldState.error.message}</FieldError>
                  ) : (
                    field.placeholder && <FieldDescription>{field.placeholder}</FieldDescription>
                  )}
                </Field>
              )}
            />
          );
        })}
      </FieldGroup>
      <div className="flex items-center justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={mutation.isPending}>
          {form.submitLabel ?? "Save"}
        </Button>
      </div>
    </form>
  );
}

/** A form page: the page title, the form in a card, back to where it came from on cancel; on success to the record's
 *  page (the new record's id fills the route) or the page the planner named. */
export function AppForm({ section, title }: { section: TAppSection; title: string }) {
  const router = useRouter();
  const route = (useParams() ?? {}) as TRouteParams;
  const formId = section.form ?? "";
  const form = app.forms[formId];
  if (!form) return null;
  const target = form.onSuccess?.navigate;
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <Card>
        <CardContent>
          <AppFormBody
            formId={formId}
            onCancel={() => router.back()}
            onDone={(result) => {
              if (!target) return;
              // The target's parameters come from the current route when it has them (a task added on its project's
              // page goes back to that project), else from the new record (a new deck opens its own page).
              const pattern = app.routes[target] ?? target;
              const needed = [...pattern.matchAll(/\[([A-Za-z0-9_]+)\]/g)].map((match) => match[1]);
              const fromRoute = needed.every((name) => route[name] !== undefined);
              const id = (result as { id?: unknown } | null)?.id;
              router.push(pageHref(target, fromRoute || id === undefined ? {} : { id }, route));
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
