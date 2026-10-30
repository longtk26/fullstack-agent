"use client";

import Link from "next/link";
import { Section } from "@/components/layout/Section";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { TBinding, TColumn, TRecord, TStates } from "@/components/renderer/site";
import { recordHref, useSectionRecords } from "@/components/renderer/use-section-records";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import type { TDataSectionContent } from "./types";

type DataTableProps = TDataSectionContent & {
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** Records as a table, one column per field; the first column links to the record's page. */
export function DataTable({ title, description, items, columns = [], binding, states }: DataTableProps) {
  const { records, isLoading, error } = useSectionRecords(items, binding);
  return (
    <Section title={title} description={description}>
      <QueryState isLoading={isLoading} error={error} isEmpty={records.length === 0} emptyText={states?.empty} emptyImage={states?.emptyImage} errorText={states?.error}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key}>{column.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((record, row) => {
              const href = recordHref(binding?.link, record);
              return (
                <TableRow key={String(record.id ?? row)}>
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
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </QueryState>
    </Section>
  );
}
