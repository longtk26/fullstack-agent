"use client";

import { FileText } from "lucide-react";
import { useState } from "react";
import { photoCredit } from "@/components/app/app";
import { PhotoCredit } from "@/components/app/PhotoCredit";
import type { TFileValue } from "@/components/app/plugin-types";

/** A file or image field in a list or a record (Story 22.7): through its signed read URL (`<field>Url`). An image
 *  that does not load (a seeded outside link that went away) shows the empty value, not a broken image. */
export const FileValue: TFileValue = ({ entity, field, record, compact }) => {
  const spec = entity?.fields?.[field];
  const url = spec?.urlField ? record[spec.urlField] : undefined;
  const [failed, setFailed] = useState(false);
  if (typeof url !== "string" || !url || (failed && spec?.type === "image")) {
    return <span className="text-muted-foreground">—</span>;
  }
  if (spec?.type === "image") {
    const credit = photoCredit(url);
    if (credit) {
      return (
        <span className={compact ? "relative inline-block h-10 w-14" : "relative inline-block aspect-video max-h-56 w-full max-w-sm"}>
          {/* eslint-disable-next-line @next/next/no-img-element -- a seeded stock photo, hotlinked as its service asks */}
          <img
            src={url}
            alt=""
            title={compact ? `Photo by ${credit.name} on Unsplash` : undefined}
            className="size-full rounded-lg border object-cover"
            loading="lazy"
            onError={() => setFailed(true)}
          />
          {!compact && <PhotoCredit credit={credit} />}
        </span>
      );
    }
    return (
      // eslint-disable-next-line @next/next/no-img-element -- a signed URL from the API, not a static asset
      <img
        src={url}
        alt=""
        className={compact ? "h-10 w-14 rounded-md border object-cover" : "aspect-video max-h-56 w-full max-w-sm rounded-lg border object-cover"}
        loading="lazy"
        onError={() => setFailed(true)}
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
