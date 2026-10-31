"use client";

import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { TBinding, TColumn, TSectionAction, TStates } from "@/components/renderer/site";
import { useSectionRecords } from "@/components/renderer/use-section-records";
import { ActionButtons } from "./ActionButtons";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import type { TDataSectionContent } from "./types";

type DetailViewProps = TDataSectionContent & {
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
  actions?: TSectionAction[];
};

/** One record (a get operation): the first field as its title, the others as labelled values. */
export function DetailView({ title, description, columns = [], binding, states, actions = [] }: DetailViewProps) {
  const { record, isLoading, error } = useSectionRecords(undefined, binding);
  const [heading, ...rest] = columns;
  const hasActions = actions.length > 0;

  return (
    <Section title={title} description={description}>
      <QueryState isLoading={isLoading} error={error} isEmpty={!record} emptyText={states?.empty} emptyImage={states?.emptyImage} errorText={states?.error}>
        {record && (
          <Card data-bga-record={String(record.id ?? "")}>
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <CardTitle className="text-2xl">{heading ? formatValue(record[heading.key], heading.format) : ""}</CardTitle>
              {hasActions && <ActionButtons actions={actions} record={record} />}
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
