export type TRecord = Record<string, unknown>;

/** The fields a record view shows: the section's `data.fields`, else every field of the first record. */
export function recordFields(items: TRecord[], fields?: string[]): string[] {
  return fields?.length ? fields : Object.keys(items[0] ?? {});
}

export function isImage(value: unknown): value is string {
  return typeof value === "string" && (value.startsWith("asset:") || value.startsWith("https://"));
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(formatValue).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function fieldLabel(field: string): string {
  const words = field.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function recordKey(record: TRecord, index: number): string {
  const id = record.id ?? record.slug ?? record.title ?? record.name;
  return typeof id === "string" || typeof id === "number" ? String(id) : String(index);
}
