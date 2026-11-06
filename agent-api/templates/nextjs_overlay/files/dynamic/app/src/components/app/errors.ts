import { app } from "./app";

type TApiErrorLike = { status?: number; code?: string; message?: string; details?: unknown };

/** The message to show for a failed operation: the contract's message for its code (`x-bga.errors`), else the
 *  server's. */
export function errorMessage(operationId: string | undefined, error: unknown): string {
  const e = (error ?? {}) as TApiErrorLike;
  const known = operationId ? app.errors[operationId]?.find((item) => item.code === e.code) : undefined;
  return e.message || known?.message || "Something went wrong";
}

/** Server errors by form field: request validation (`details: [{loc, msg}]`), a conflict that names its fields
 *  (`details: {fields: [...]}`, a unique field's 409), and the contract's errors that name their fields (a rule's
 *  conflict on `start`, say). Errors without a field go to a toast. */
export function fieldErrors(operationId: string | undefined, error: unknown, fields: string[]): Record<string, string> {
  const e = (error ?? {}) as TApiErrorLike;
  const out: Record<string, string> = {};
  if (Array.isArray(e.details)) {
    for (const item of e.details as { loc?: unknown[]; msg?: string; field?: string; message?: string }[]) {
      const name = item.field ?? [...(item.loc ?? [])].reverse().find((part) => typeof part === "string" && fields.includes(part));
      if (typeof name === "string" && fields.includes(name)) out[name] = item.msg ?? item.message ?? "Not valid";
    }
  }
  const named = e.details && typeof e.details === "object" && !Array.isArray(e.details) ? (e.details as { fields?: unknown }).fields : undefined;
  for (const name of Array.isArray(named) ? named : []) {
    if (typeof name === "string" && fields.includes(name) && !out[name]) out[name] = e.message || "Already taken";
  }
  const known = operationId ? app.errors[operationId]?.find((item) => item.code === e.code) : undefined;
  for (const name of known?.fields ?? []) {
    if (fields.includes(name) && !out[name]) out[name] = e.message || known?.message || "Not valid";
  }
  return out;
}
