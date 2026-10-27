export type TValueFormat = "text" | "date" | "datetime" | "badge";

const dateFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium" });
const dateTimeFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });

/** How a record field is shown in tables, cards and detail views. */
export function formatValue(value: unknown, format: TValueFormat = "text"): string {
  if (value === null || value === undefined || value === "") return "—";
  if (format === "date") return dateFormat.format(new Date(`${String(value)}T00:00:00`));
  if (format === "datetime") return dateTimeFormat.format(new Date(String(value)));
  if (format === "badge") return String(value).replaceAll("_", " ").toLowerCase();
  return String(value);
}
