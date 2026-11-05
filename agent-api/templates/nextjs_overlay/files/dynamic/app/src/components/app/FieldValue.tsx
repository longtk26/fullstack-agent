import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { pageHref, type TAppEntity, type TRecord } from "./app";

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });
const dateTimeFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const numberFormat = new Intl.NumberFormat();

function enumLabel(value: string): string {
  const words = value.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function asDate(value: unknown): Date | null {
  if (typeof value !== "string" && typeof value !== "number") return null;
  // A date-only value is a calendar day: read it as local, not as UTC midnight.
  const date = typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

type FieldValueProps = {
  entity: TAppEntity | undefined;
  field: string;
  record: TRecord;
  /** Links a parent to its page (off inside a link, such as a card). */
  link?: boolean;
};

/** One field of a record, shown by its type: parents by name (linked to their page), dates in the user's format,
 *  enums as badges, numbers grouped; empty values as a dash. */
export function FieldValue({ entity, field, record, link = true }: FieldValueProps) {
  const reference = entity?.references?.[field];
  if (reference) {
    const summary = record[reference.summary] as { id?: unknown; label?: unknown } | null | undefined;
    const id = summary?.id ?? record[field];
    if (id === undefined || id === null) return <span className="text-muted-foreground">—</span>;
    const label = summary?.label ? String(summary.label) : String(id);
    if (!link || !reference.href) return <span>{label}</span>;
    return (
      <Link href={pageHref(reference.href, { id })} className="font-medium underline-offset-4 hover:underline">
        {label}
      </Link>
    );
  }
  const value = record[field];
  if (value === undefined || value === null || value === "") return <span className="text-muted-foreground">—</span>;
  const type = entity?.fields?.[field]?.type ?? "string";
  switch (type) {
    case "boolean":
      return <span>{value ? "Yes" : "No"}</span>;
    case "enum":
      return <Badge variant="secondary">{enumLabel(String(value))}</Badge>;
    case "date": {
      const date = asDate(value);
      return <time dateTime={String(value)}>{date ? dateFormat.format(date) : String(value)}</time>;
    }
    case "datetime": {
      const date = asDate(value);
      return <time dateTime={String(value)}>{date ? dateTimeFormat.format(date) : String(value)}</time>;
    }
    case "integer":
    case "number":
      return <span className="tabular-nums">{typeof value === "number" ? numberFormat.format(value) : String(value)}</span>;
    case "list":
      return <span>{Array.isArray(value) ? value.length : String(value)}</span>;
    case "object":
      return <span className="text-muted-foreground">…</span>;
    case "text":
      return <span className="line-clamp-3 whitespace-pre-line">{String(value)}</span>;
    default:
      return <span>{String(value)}</span>;
  }
}
