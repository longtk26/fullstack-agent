"use client";

import Link from "next/link";
import { Section } from "@/components/layout/Section";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { TBinding, TColumn, TRecord, TSectionAction, TSectionControls, TStates } from "@/components/renderer/site";
import { recordHref, useSectionRecords } from "@/components/renderer/use-section-records";
import { ActionButtons } from "./ActionButtons";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import { SectionControls } from "./SectionControls";
import type { TDataSectionContent } from "./types";

type DataTableProps = TDataSectionContent & {
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
  actions?: TSectionAction[];
  controls?: TSectionControls;
};

/** Records as a table, one column per field; the first column links to the record's page. */
export function DataTable({ title, description, items, columns = [], binding, states, actions = [], controls }: DataTableProps) {
  const { records, total, isLoading, error } = useSectionRecords(items, binding, controls);
  const hasActions = actions.length > 0;

  return (
    <Section title={title} description={description}>
      <SectionControls controls={controls} columns={columns} total={total} recordsCount={records.length} />
      <QueryState isLoading={isLoading} error={error} isEmpty={records.length === 0} emptyText={states?.empty} emptyImage={states?.emptyImage} errorText={states?.error}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key}>{column.label}</TableHead>
              ))}
              {hasActions && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((record, row) => {
              const href = recordHref(binding?.link, record);
              const recordId = String(record.id ?? row);
              return (
                <TableRow key={recordId} data-bga-record={recordId}>
                  {columns.map((column, index) => {
                    const text = formatValue(record[column.key], column.format);
                    return (
                      <TableCell key={column.key}>
                        {column.format === "badge" ? (
                          <Badge variant="secondary" className="h-6 text-sm">{text}</Badge>
                        ) : index === 0 && href ? (
                          <Link href={href} className="font-medium hover:underline">
                            {text}
                          </Link>
                        ) : (
                          text
                        )}
                      </TableCell>
                    );
                  })}
                  {hasActions && (
                    <TableCell className="text-right">
                      <ActionButtons actions={actions} record={record} className="inline-flex justify-end gap-1.5" />
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </QueryState>
    </Section>
  );
}
