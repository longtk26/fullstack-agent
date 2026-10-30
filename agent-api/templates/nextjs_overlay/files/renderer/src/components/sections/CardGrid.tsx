"use client";

import Link from "next/link";
import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { TBinding, TColumn, TRecord, TStates } from "@/components/renderer/site";
import { recordHref, useSectionRecords } from "@/components/renderer/use-section-records";
import { AssetImage } from "./AssetImage";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import { cardClass } from "./styles";
import type { TCardGridContent } from "./types";

type CardGridProps = TCardGridContent & {
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** Records as cards: image fields first, the first other field as the title; linked to the record's page. */
export function CardGrid({ title, description, cardStyle, items, columns = [], binding, states }: CardGridProps) {
  const { records, isLoading, error } = useSectionRecords(items, binding);
  const images = columns.filter((column) => column.format === "image");
  const [heading, ...rest] = columns.filter((column) => column.format !== "image");
  return (
    <Section title={title} description={description}>
      <QueryState isLoading={isLoading} error={error} isEmpty={records.length === 0} emptyText={states?.empty} emptyImage={states?.emptyImage} errorText={states?.error}>
        <Grid columns={3}>
          {records.map((record, index) => {
            const href = recordHref(binding?.link, record);
            const card = (
              <Card
                className={cn(
                  cardClass(cardStyle),
                  "h-full",
                  href && "transition-transform duration-200 hover:-translate-y-0.5 motion-reduce:transition-none motion-reduce:hover:translate-y-0",
                )}
              >
                {images.map((column) => (
                  <AssetImage key={column.key} asset={String(record[column.key] ?? "")} />
                ))}
                <CardHeader>{heading && <CardTitle>{formatValue(record[heading.key], heading.format)}</CardTitle>}</CardHeader>
                {rest.length > 0 && (
                  <CardContent className="flex flex-col gap-1 text-sm text-muted-foreground">
                    {rest.map((column) => (
                      <span key={column.key}>{formatValue(record[column.key], column.format)}</span>
                    ))}
                  </CardContent>
                )}
              </Card>
            );
            const key = String(record.id ?? index);
            return href ? (
              <Link key={key} href={href}>
                {card}
              </Link>
            ) : (
              <div key={key}>{card}</div>
            );
          })}
        </Grid>
      </QueryState>
    </Section>
  );
}
