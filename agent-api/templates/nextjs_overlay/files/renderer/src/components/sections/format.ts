export type TValueFormat = "text" | "date" | "datetime" | "badge" | "image";

const dateFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium" });
const dateTimeFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });

/** How a record field is shown in cards, lists, tables and detail views. */
export function formatValue(value: unknown, format: TValueFormat = "text"): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map((item) => formatValue(item)).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  if (format === "date") return dateFormat.format(new Date(`${String(value).slice(0, 10)}T00:00:00`));
  if (format === "datetime") return dateTimeFormat.format(new Date(String(value)));
  if (format === "badge") return String(value).replaceAll("_", " ").toLowerCase();
  return String(value);
}
