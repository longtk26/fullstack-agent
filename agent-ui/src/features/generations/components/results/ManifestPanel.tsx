import { TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Stack } from "@/components/layout/Stack";
import type { TManifest } from "../../types";

type ManifestPanelProps = {
  manifest: TManifest;
};

const METHOD_TONE: Record<string, string> = {
  GET: "bg-info/15 text-info",
  POST: "bg-success/15 text-success",
  PATCH: "bg-warning/20 text-warning-foreground dark:text-warning",
  PUT: "bg-warning/20 text-warning-foreground dark:text-warning",
  DELETE: "bg-destructive/10 text-destructive",
};

export function ManifestPanel({ manifest }: ManifestPanelProps) {
  const bindings = new Map<string, string[]>();
  for (const binding of manifest.frontendBindings ?? []) {
    bindings.set(binding.operationId, [...(bindings.get(binding.operationId) ?? []), binding.component]);
  }
  return (
    <Stack gap="md">
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">{manifest.architecture}</Badge>
        <Badge variant="outline">template {manifest.templateRef?.slice(0, 8) ?? "—"}</Badge>
        {manifest.api && <Badge variant="outline">operations from {manifest.api.source}</Badge>}
        {manifest.modules.map((module) => (
          <Badge key={module.name} variant="secondary" className="font-mono">
            {module.path}
          </Badge>
        ))}
      </div>

      {(manifest.unresolved.length > 0 || manifest.contractProblems.length > 0) && (
        <div className="flex flex-col gap-1 rounded-lg border border-warning/40 bg-warning/10 p-3 text-xs">
          <p className="flex items-center gap-1.5 font-medium">
            <TriangleAlert className="size-3.5" /> Needs attention
          </p>
          {manifest.unresolved.map((item, index) => (
            <p key={`u${index}`}>
              <span className="font-mono">{item.ref ?? item.specPath}</span> — {item.message ?? item.reason}
            </p>
          ))}
          {manifest.contractProblems.map((problem, index) => (
            <p key={`c${index}`}>
              <span className="font-mono">{problem.operation}</span> — {problem.message}
            </p>
          ))}
        </div>
      )}

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Method</TableHead>
              <TableHead>Path</TableHead>
              <TableHead>operationId</TableHead>
              <TableHead>Auth</TableHead>
              <TableHead>Request → response</TableHead>
              <TableHead>Status codes</TableHead>
              {bindings.size > 0 && <TableHead>Frontend</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {manifest.operations.map((op) => (
              <TableRow key={op.operationId}>
                <TableCell>
                  <Badge variant="secondary" className={METHOD_TONE[op.method]}>
                    {op.method}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{op.path}</TableCell>
                <TableCell className="font-mono text-xs">{op.operationId}</TableCell>
                <TableCell className="text-xs">{op.policy ? `${op.auth} · ${op.policy}` : op.auth}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {op.requestSchema ?? "—"} → {op.responseSchema ?? "—"}
                </TableCell>
                <TableCell className="text-xs tabular-nums">{op.statusCodes.join(", ")}</TableCell>
                {bindings.size > 0 && (
                  <TableCell className="text-xs">{bindings.get(op.operationId)?.join(", ") ?? "—"}</TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Environment variable</TableHead>
              <TableHead>Required</TableHead>
              <TableHead>Description</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {manifest.env.map((variable) => (
              <TableRow key={variable.name}>
                <TableCell className="font-mono text-xs">
                  {variable.name}
                  {variable.secret && (
                    <Badge variant="outline" className="ml-2">
                      secret
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-xs">{variable.required ? "yes" : "no"}</TableCell>
                <TableCell className="whitespace-normal text-xs text-muted-foreground">
                  {variable.description ?? "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Stack>
  );
}
