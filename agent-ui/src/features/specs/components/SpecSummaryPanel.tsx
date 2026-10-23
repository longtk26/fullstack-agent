import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Stack } from "@/components/layout/Stack";
import type { TSpecSummary } from "../lib/spec-summary";

type SpecSummaryPanelProps = {
  summary: TSpecSummary;
};

export function SpecSummaryPanel({ summary }: SpecSummaryPanelProps) {
  if (summary.entities.length === 0 && summary.operations.length === 0) {
    return <p className="text-sm text-muted-foreground">Entities and operations appear here once the JSON parses.</p>;
  }
  return (
    <Stack gap="md">
      <Stack gap="xs">
        <h3 className="text-sm font-medium">Entities ({summary.entities.length})</h3>
        <Stack direction="row" gap="xs" wrap>
          {summary.entities.map((entity) => (
            <Badge key={entity.name} variant="outline">
              {entity.name} · {entity.fieldCount} fields
              {entity.relationshipCount > 0 && ` · ${entity.relationshipCount} rel`}
            </Badge>
          ))}
        </Stack>
      </Stack>
      <Stack gap="xs">
        <h3 className="text-sm font-medium">Operations ({summary.operations.length})</h3>
        <div className="max-h-72 overflow-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Method</TableHead>
                <TableHead>Path</TableHead>
                <TableHead>operationId</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summary.operations.map((operation, index) => (
                <TableRow key={`${operation.operationId}-${index}`}>
                  <TableCell className="font-mono text-xs">{operation.method}</TableCell>
                  <TableCell className="font-mono text-xs">{operation.path}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{operation.operationId}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Stack>
    </Stack>
  );
}
