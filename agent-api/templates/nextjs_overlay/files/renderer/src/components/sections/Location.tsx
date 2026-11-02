"use client";

import { useSyncExternalStore } from "react";
import { Clock, Mail, MapPin, Phone } from "lucide-react";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AssetImage, backdropImage } from "./AssetImage";
import type { TLocationContent } from "./types";

type LocationProps = TLocationContent;
type THours = NonNullable<LocationProps["hours"]>[number];

const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

/** The weekdays (0 = Sunday) a line like "Mon–Fri", "Sat, Sun" or "Daily" covers; empty when it cannot be read. */
export function coveredDays(days: string): number[] {
  const text = days.toLowerCase();
  if (/daily|every day|mon\w*\s*[–-]\s*sun/.test(text)) return [0, 1, 2, 3, 4, 5, 6];
  const out = new Set<number>();
  for (const part of text.split(/,|&|\band\b/)) {
    const [from, to] = part.split(/[–-]|\bto\b/).map((day) => DAYS.indexOf(day.trim().slice(0, 3)));
    if (from === undefined || from < 0) continue;
    if (to === undefined || to < 0) {
      out.add(from);
      continue;
    }
    for (let day = from; ; day = (day + 1) % 7) {
      out.add(day);
      if (day === to) break;
    }
  }
  return [...out];
}

const noop = () => () => {};

/** Today's weekday in the visitor's browser; -1 while rendering on the server (the static export). */
function useToday(): number {
  return useSyncExternalStore(noop, () => new Date().getDay(), () => -1);
}

function HoursTable({ hours }: { hours: THours[] }) {
  const today = useToday();
  return (
    <table className="w-full max-w-sm text-left">
      <caption className="sr-only">Opening hours</caption>
      <tbody>
        {hours.map((line) => {
          const isToday = today >= 0 && coveredDays(line.days).includes(today);
          const time = line.opens && line.closes ? `${line.opens}–${line.closes}` : (line.opens ?? line.note ?? "");
          return (
            <tr key={line.days} className={cn("border-b border-border last:border-0", isToday && "font-semibold")}>
              <th scope="row" className="py-2 pr-6 font-normal">
                {line.days}
                {isToday && <span className="ml-2 text-sm text-primary">Today</span>}
              </th>
              <td className="py-2 tabular-nums">
                {time}
                {line.note && line.opens && <span className="text-muted-foreground"> · {line.note}</span>}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Details(props: LocationProps) {
  const { address, hours = [], phone, email, mapLink } = props;
  return (
    <div className="flex flex-col gap-6">
      <p className="flex gap-3 text-lg">
        <MapPin className="mt-1 size-5 shrink-0 text-primary" aria-hidden />
        <span>
          {address}
          {mapLink && (
            <a href={mapLink} className="mt-1 block text-sm text-primary underline-offset-4 hover:underline" rel="noreferrer" target="_blank">
              Open in maps
            </a>
          )}
        </span>
      </p>
      {hours.length > 0 && (
        <div className="flex gap-3">
          <Clock className="mt-2.5 size-5 shrink-0 text-primary" aria-hidden />
          <HoursTable hours={hours} />
        </div>
      )}
      {(phone || email) && (
        <div className="flex flex-col gap-2">
          {phone && (
            <a href={`tel:${phone.replaceAll(" ", "")}`} className="flex items-center gap-3 hover:text-primary">
              <Phone className="size-5 text-primary" aria-hidden /> {phone}
            </a>
          )}
          {email && (
            <a href={`mailto:${email}`} className="flex items-center gap-3 hover:text-primary">
              <Mail className="size-5 text-primary" aria-hidden /> {email}
            </a>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Where to find a place and when it is open (Story 20.8): `split` (details beside an image from 1024 px), `card`
 * (the details on one card) and `band` (address, hours and contact in columns). Today's opening hours are marked in
 * the visitor's browser; the map is a link, never an embedded frame (no third-party requests).
 */
export function Location(props: LocationProps) {
  const { title = "Visit us", image, form = "split", background, backgroundImage } = props;
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      {form === "card" && (
        <Card className="max-w-xl">
          <CardContent>
            <Details {...props} />
          </CardContent>
        </Card>
      )}
      {form === "band" && (
        <div className="grid gap-8 md:grid-cols-[2fr_3fr]">
          {image && <AssetImage asset={image} className="aspect-[4/3]" />}
          <Details {...props} />
        </div>
      )}
      {form === "split" && (
        <div className={cn("grid gap-10", image && "lg:grid-cols-2 lg:items-center")}>
          <Details {...props} />
          {image && <AssetImage asset={image} />}
        </div>
      )}
    </Section>
  );
}
