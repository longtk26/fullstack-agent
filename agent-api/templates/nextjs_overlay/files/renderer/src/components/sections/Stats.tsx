"use client";

import { useParams } from "next/navigation";
import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import { useOperationQuery } from "@/components/renderer/bindings";
import { resolveParams } from "@/components/renderer/use-section-records";
import { cn } from "@/lib/utils";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TStatItem, TStatsContent } from "./types";

type StatsProps = TStatsContent;

/** A stat's value: written in the content, or counted / read from an API operation (Story 19.6). */
function useStatValue(item: TStatItem): string | number {
  const route = (useParams() ?? {}) as Record<string, string | string[] | undefined>;
  const operationId = item.data?.operationId;
  const query = useOperationQuery(operationId, resolveParams({}, route));

  if (!operationId) return item.value ?? "";
  if (query.isLoading) return "…";
  const data = query.data;
  if (data === undefined) return item.value ?? "";
  if (item.data?.value === "count") {
    if (Array.isArray(data)) return data.length;
    if (typeof data === "number") return data;
    if (typeof data === "object" && data !== null) {
      const obj = data as { total?: number; count?: number; items?: unknown[] };
      return obj.total ?? obj.count ?? (Array.isArray(obj.items) ? obj.items.length : 0);
    }
    return item.value ?? "";
  }
  if (item.data?.value && typeof data === "object" && data !== null) {
    return ((data as Record<string, unknown>)[item.data.value] as string | number) ?? "—";
  }
  return item.value ?? "";
}

function StatCard({ item, cardStyle }: { item: TStatItem; cardStyle?: StatsProps["cardStyle"] }) {
  const value = useStatValue(item);
  return (
    <Card className={cardClass(cardStyle)}>
      <CardContent className="flex flex-col gap-1">
        <span className="font-heading text-2xl font-semibold">{value}</span>
        <span className="text-sm text-muted-foreground">{item.label}</span>
      </CardContent>
    </Card>
  );
}

/**
 * A number without a box: an accent rule, the number in the heading face and weight, its label under it. It keeps to
 * the section title's size step, so a page with a hero still has five type sizes at most (design checklist).
 */
function Figure({ item }: { item: TStatItem }) {
  const value = useStatValue(item);
  return (
    <div className="flex flex-col gap-2 border-l-2 border-primary pl-5">
      <span className="heading font-heading text-2xl tabular-nums">{value}</span>
      <span className="text-sm text-muted-foreground">{item.label}</span>
    </div>
  );
}

/** One line of value and label pairs, separated by hairlines (they wrap on small screens). */
function InlineStat({ item, first }: { item: TStatItem; first: boolean }) {
  const value = useStatValue(item);
  return (
    <div className={cn("flex items-baseline gap-2 py-2 sm:px-6", !first && "sm:border-l sm:border-border")}>
      <span className="font-heading text-2xl font-semibold tabular-nums">{value}</span>
      <span className="text-sm text-muted-foreground">{item.label}</span>
    </div>
  );
}

/**
 * Key numbers, in three forms (Stories 17.7, 20.2): `cards` (a grid of cards), `figures` (large numbers without
 * boxes) and `inline` (one line with dividers).
 */
export function Stats({ title, items = [], cardStyle, form = "cards", background, backgroundImage }: StatsProps) {
  const columns = items.length >= 4 ? 4 : items.length === 3 ? 3 : 2;
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      {form === "figures" && (
        <Grid columns={columns}>
          {items.map((item, index) => (
            <Figure key={`${item.label}-${index}`} item={item} />
          ))}
        </Grid>
      )}
      {form === "inline" && (
        <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-baseline sm:[&>*:first-child]:pl-0">
          {items.map((item, index) => (
            <InlineStat key={`${item.label}-${index}`} item={item} first={index === 0} />
          ))}
        </div>
      )}
      {form === "cards" && (
        <Grid columns={columns}>
          {items.map((item, index) => (
            <StatCard key={`${item.label}-${index}`} item={item} cardStyle={cardStyle} />
          ))}
        </Grid>
      )}
    </Section>
  );
}
