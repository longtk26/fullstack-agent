import { FileText } from "lucide-react";
import type { TFileValue } from "@/components/app/plugin-types";

/** A file or image field in a list or a record (Story 22.7): through its signed read URL (`<field>Url`). */
export const FileValue: TFileValue = ({ entity, field, record, compact }) => {
  const spec = entity?.fields?.[field];
  const url = spec?.urlField ? record[spec.urlField] : undefined;
  if (typeof url !== "string" || !url) return <span className="text-muted-foreground">—</span>;
  if (spec?.type === "image") {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- a signed URL from the API, not a static asset
      <img
        src={url}
        alt=""
        className={compact ? "h-10 w-14 rounded-md border object-cover" : "aspect-video max-h-56 w-full max-w-sm rounded-lg border object-cover"}
        loading="lazy"
      />
    );
  }
  const name = String(record[field] ?? "").split("/").pop() || "Download";
  return (
    <a href={url} className="inline-flex items-center gap-1.5 font-medium underline-offset-4 hover:underline" download>
      <FileText aria-hidden className="size-4" />
      <span className="truncate">{name}</span>
    </a>
  );
};
