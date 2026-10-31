"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { siteConfig } from "@/config/site";
import { compactValues } from "@/lib/form-utils";
import { useOperationMutation, useOperationQuery } from "./bindings";
import { formSchemas } from "./form-schemas";
import type { TFormDef } from "./site";
import { resolveParams } from "./use-section-records";

type TValues = Record<string, unknown>;

/**
 * A FrontendSpec form: the generated Zod schema validates, hidden `$route.*` fields take the route's values, the
 * form's operation submits; on success its toast shows (or it navigates) and the form resets.
 * If `form.load` is specified, pre-fills with data from the GET operation, and for PATCH operations only submits
 * changed (dirty) fields.
 */
export function useSectionForm(formId: string, form: TFormDef) {
  const route = (useParams() ?? {}) as Record<string, string | string[] | undefined>;
  const router = useRouter();
  const schema = formSchemas[formId];
  const fixed = resolveParams(
    Object.fromEntries(form.fields.filter((field) => field.value !== undefined).map((field) => [field.name, field.value])),
    route,
  );
  const defaults = { ...(schema?.defaults ?? {}), ...fixed };
  const methods = useForm<TValues>({
    resolver: schema ? zodResolver(schema.schema as never) : undefined,
    defaultValues: defaults,
  });

  const loadQuery = useOperationQuery(
    form.load?.operationId,
    resolveParams(form.load?.params ?? {}, route),
  );

  useEffect(() => {
    if (loadQuery.data && typeof loadQuery.data === "object") {
      methods.reset({ ...defaults, ...(loadQuery.data as Record<string, unknown>) });
    }
  }, [loadQuery.data]);

  const mutation = useOperationMutation(form.operationId ?? undefined);

  function onSubmit(values: TValues) {
    const params = resolveParams(form.params, route);
    const isPatch = (mutation as { method?: string })?.method === "PATCH";
    let body: Record<string, unknown>;
    if (form.load && isPatch) {
      const dirty = methods.formState.dirtyFields;
      body = Object.fromEntries(Object.entries(values).filter(([k]) => Boolean(dirty[k])));
    } else {
      body = compactValues(values);
    }

    mutation.mutate(
      { params, body },
      {
        onSuccess: () => {
          if (form.onSuccess?.toast) toast.success(form.onSuccess.toast);
          methods.reset(defaults);
          const target = form.onSuccess?.navigate;
          if (target) router.push((siteConfig.pages as Record<string, string>)[target] ?? target);
        },
        onError: (error) => toast.error(error.message),
      },
    );
  }

  return { methods, onSubmit, pending: mutation.isPending, isLoading: Boolean(form.load && loadQuery.isLoading) };
}
