"use client";

import { useMemo, type ReactNode } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/sections/Form";
import { useOperationMutation } from "../bindings";
import { site, type TFormDef, type TFormFieldDef, type TTreeNode } from "../site";
import { useRecord } from "./tree-data";

type TFormProps = { node: TTreeNode; pageId: string; children?: ReactNode } & Record<string, unknown>;

const TYPES: Record<string, string> = { number: "number", boolean: "boolean", string: "string" };

function guessFields(collection: string | undefined): TFormFieldDef[] {
  const sample = site.collections[collection ?? ""]?.[0] ?? {};
  return Object.entries(sample)
    .filter(([name, value]) => name !== "id" && !/At$/.test(name) && (typeof value !== "string" || !value.startsWith("asset:")))
    .map(([name, value]) => ({ name, type: TYPES[typeof value] ?? "string", label: name.replace(/([a-z])([A-Z])/g, "$1 $2") }));
}

/**
 * A form that creates (`mode: "create"`) or edits (`mode: "edit"`, inside a CollectionDetail) a record of the
 * collection: `fields` as written, or the collection's own fields. On a dynamic app it submits to the bound
 * operation; on a static site it is a client-only form.
 */
export function RecordForm({ node, pageId, children: _children, ...props }: TFormProps) {
  const record = useRecord();
  const binding = node.binding;
  const definition = useMemo<TFormDef>(() => {
    const written = Array.isArray(props.fields) ? (props.fields as Partial<TFormFieldDef>[]) : null;
    const fields: TFormFieldDef[] = written
      ? written.map((f) => ({ name: String(f.name), type: f.type ?? "string", label: f.label ?? String(f.name), required: f.required }))
      : guessFields(binding?.collection);
    const edit = props.mode === "edit" && record;
    return {
      operationId: binding?.operationId ?? null,
      params: edit ? { id: String(record.id ?? "") } : {},
      fields: edit ? fields.map((f) => ({ ...f, value: record[f.name] })) : fields,
      submitLabel: typeof props.submitLabel === "string" ? props.submitLabel : edit ? "Save" : "Add",
      onSuccess: { toast: typeof props.successMessage === "string" ? props.successMessage : "Saved" },
    };
  }, [props.fields, props.mode, props.submitLabel, props.successMessage, binding, record]);
  return (
    <div className={typeof props.className === "string" ? props.className : undefined}>
      <Form
        formId={`${pageId}-${binding?.collection ?? "record"}-${props.mode === "edit" ? "edit" : "new"}`}
        form={definition}
        title={typeof props.title === "string" ? props.title : undefined}
        description={typeof props.description === "string" ? props.description : undefined}
      />
    </div>
  );
}

/** A button on the current record: `delete`, or `set` a field to a value (status changes). */
export function RecordAction({ node, pageId: _pageId, children, ...props }: TFormProps) {
  const record = useRecord();
  const binding = node.binding;
  const mutation = useOperationMutation(binding?.operationId);
  const action = props.action === "set" ? "set" : "delete";
  const label = typeof props.label === "string" ? props.label : children ?? (action === "delete" ? "Delete" : "Update");
  const onClick = () => {
    if (!record) return;
    if (props.confirm !== false && action === "delete" && !window.confirm(String(props.confirm ?? "Delete this record?"))) return;
    if (!binding?.operationId) {
      toast("This action needs the app's backend");
      return;
    }
    const body = action === "set" && typeof props.field === "string" ? { [props.field]: props.value } : {};
    mutation.mutate(
      { params: { id: String(record.id ?? "") }, body },
      { onSuccess: () => toast(typeof props.successMessage === "string" ? props.successMessage : "Done") },
    );
  };
  return (
    <Button
      variant={(props.variant as "default" | "destructive" | "outline" | "secondary" | "ghost" | "link") ?? (action === "delete" ? "destructive" : "default")}
      size="sm"
      className={typeof props.className === "string" ? props.className : undefined}
      onClick={onClick}
      disabled={!record || mutation.isPending}
    >
      {label}
    </Button>
  );
}
