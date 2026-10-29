import { Section } from "@/components/layout/Section";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fieldLabel, formatValue, recordFields, recordKey, type TRecord } from "./records";
import type { TDataSectionContent } from "./types";

type DataTableProps = TDataSectionContent & {
  items?: TRecord[];
  fields?: string[];
};

/** Records of a content collection as a table, one column per field. */
export function DataTable({ title, description, items = [], fields }: DataTableProps) {
  const columns = recordFields(items, fields);
  return (
    <Section title={title} description={description}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((field) => (
              <TableHead key={field}>{fieldLabel(field)}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((record, index) => (
            <TableRow key={recordKey(record, index)}>
              {columns.map((field) => (
                <TableCell key={field}>{formatValue(record[field])}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Section>
  );
}
