"use client";

import Link from "next/link";
import { Section } from "@/components/layout/Section";
import { Separator } from "@/components/ui/separator";
import type { TBinding, TColumn, TRecord, TSectionAction, TSectionControls, TStates } from "@/components/renderer/site";
import { recordHref, useSectionRecords } from "@/components/renderer/use-section-records";
import { ActionButtons } from "./ActionButtons";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import { SectionControls } from "./SectionControls";
import type { TDataSectionContent } from "./types";

type ListProps = TDataSectionContent & {
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
  actions?: TSectionAction[];
  controls?: TSectionControls;
};

/** Records as a list: the first field as the line (linked to the record's page), the others below it. */
export function List({ title, description, items, columns = [], binding, states, actions = [], controls }: ListProps) {
  const { records, total, isLoading, error } = useSectionRecords(items, binding, controls);
  const [primary, ...rest] = columns;
  const hasActions = actions.length > 0;

  return (
    <Section title={title} description={description}>
      <SectionControls controls={controls} columns={columns} total={total} recordsCount={records.length} />
      <QueryState isLoading={isLoading} error={error} isEmpty={records.length === 0} emptyText={states?.empty} emptyImage={states?.emptyImage} errorText={states?.error}>
        <ul className="flex flex-col">
          {records.map((record, index) => {
            const href = recordHref(binding?.link, record);
            const line = primary ? formatValue(record[primary.key], primary.format) : "";
            const recordId = String(record.id ?? index);
            return (
              <li key={recordId} data-bga-record={recordId} className="flex flex-col gap-1 pb-3">
                {index > 0 && <Separator className="mb-3" />}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    {href ? (
                      <Link href={href} className="font-medium hover:underline">
                        {line}
                      </Link>
                    ) : (
                      <span className="font-medium">{line}</span>
                    )}
                  </div>
                  {hasActions && <ActionButtons actions={actions} record={record} />}
                </div>
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
