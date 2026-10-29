"use client";

import Link from "next/link";
import { Section } from "@/components/layout/Section";
import { Separator } from "@/components/ui/separator";
import type { TBinding, TColumn, TRecord, TStates } from "@/components/renderer/site";
import { recordHref, useSectionRecords } from "@/components/renderer/use-section-records";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import type { TDataSectionContent } from "./types";

type ListProps = TDataSectionContent & {
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** Records as a list: the first field as the line (linked to the record's page), the others below it. */
export function List({ title, description, items, columns = [], binding, states }: ListProps) {
  const { records, isLoading, error } = useSectionRecords(items, binding);
  const [primary, ...rest] = columns;
  return (
    <Section title={title} description={description}>
      <QueryState isLoading={isLoading} error={error} isEmpty={records.length === 0} emptyText={states?.empty} errorText={states?.error}>
        <ul className="flex flex-col">
          {records.map((record, index) => {
            const href = recordHref(binding?.link, record);
            const line = primary ? formatValue(record[primary.key], primary.format) : "";
            return (
              <li key={String(record.id ?? index)} className="flex flex-col gap-1 pb-3">
                {index > 0 && <Separator className="mb-3" />}
                {href ? (
                  <Link href={href} className="font-medium hover:underline">
                    {line}
                  </Link>
                ) : (
                  <span className="font-medium">{line}</span>
                )}
                {rest.map((column) => (
                  <span key={column.key} className="text-sm text-muted-foreground">
                    {formatValue(record[column.key], column.format)}
                  </span>
                ))}
              </li>
            );
          })}
        </ul>
      </QueryState>
    </Section>
  );
}
