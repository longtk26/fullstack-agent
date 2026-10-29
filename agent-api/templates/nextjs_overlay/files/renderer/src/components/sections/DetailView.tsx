"use client";

import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { TBinding, TColumn, TStates } from "@/components/renderer/site";
import { useSectionRecords } from "@/components/renderer/use-section-records";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import type { TDataSectionContent } from "./types";

type DetailViewProps = TDataSectionContent & {
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** One record (a get operation): the first field as its title, the others as labelled values. */
export function DetailView({ title, description, columns = [], binding, states }: DetailViewProps) {
  const { record, isLoading, error } = useSectionRecords(undefined, binding);
  const [heading, ...rest] = columns;
  return (
    <Section title={title} description={description}>
      <QueryState isLoading={isLoading} error={error} isEmpty={!record} emptyText={states?.empty} errorText={states?.error}>
        {record && (
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">{heading ? formatValue(record[heading.key], heading.format) : ""}</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent>
              <dl className="grid gap-3 sm:grid-cols-[10rem_1fr]">
                {rest.map((column) => (
                  <div key={column.key} className="contents">
                    <dt className="text-sm text-muted-foreground">{column.label}</dt>
                    <dd>{formatValue(record[column.key], column.format)}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        )}
      </QueryState>
    </Section>
  );
}
