import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatValue, type TValueFormat } from "./format";

export type TColumn = { key: string; label: string; format?: TValueFormat };

type DataTableProps = {
  columns: TColumn[];
  rows: Record<string, unknown>[];
  rowKey: string;
  rowHref?: (row: Record<string, unknown>) => string;
};

/** Records as a table; the first column links to the record when `rowHref` is given. */
export function DataTable({ columns, rows, rowKey, rowHref }: DataTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column.key}>{column.label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={String(row[rowKey])}>
            {columns.map((column, index) => {
              const text = formatValue(row[column.key], column.format);
              return (
                <TableCell key={column.key}>
                  {column.format === "badge" ? (
                    <Badge variant="secondary">{text}</Badge>
                  ) : index === 0 && rowHref ? (
                    <Link href={rowHref(row)} className="font-medium hover:underline">
                      {text}
                    </Link>
                  ) : (
                    text
                  )}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
