import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type ValidationChecksProps = {
  validation: Record<string, string>;
};

const VARIANT: Record<string, "secondary" | "destructive" | "outline"> = {
  passed: "secondary",
  failed: "destructive",
};

export function ValidationChecks({ validation }: ValidationChecksProps) {
  const checks = Object.entries(validation);
  if (checks.length === 0) return <p className="text-sm text-muted-foreground">No validation has run yet.</p>;
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Check</TableHead>
            <TableHead>Latest result</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {checks.map(([check, status]) => (
            <TableRow key={check}>
              <TableCell className="font-mono text-xs">{check}</TableCell>
              <TableCell>
                <Badge variant={VARIANT[status] ?? "outline"}>{status.replaceAll("_", " ")}</Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
