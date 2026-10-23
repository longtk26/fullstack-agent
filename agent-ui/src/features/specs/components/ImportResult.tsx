"use client";

import { ArrowRight, Download, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Stack } from "@/components/layout/Stack";
import { downloadText, prettyJson } from "@/lib/files";
import type { TFrontendImportResult } from "../types";
import { JsonEditor } from "./JsonEditor";
import { NotesPanel } from "./NotesPanel";

const PREVIEW_ROWS = 3;
const PREVIEW_COLUMNS = 4;

type ImportResultProps = {
  result: TFrontendImportResult;
  needsAcknowledgement: boolean;
  acknowledged: boolean;
  onAcknowledge: (value: boolean) => void;
  onEdit: () => void;
};

function previewValue(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 40 ? `${text.slice(0, 40)}…` : text;
}

export function ImportResult({ result, needsAcknowledgement, acknowledged, onAcknowledge, onEdit }: ImportResultProps) {
  const specText = prettyJson(result.backendSpec);
  const canEdit = !needsAcknowledgement || acknowledged;

  return (
    <Stack gap="md">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Generated example BackendSpec
            <Badge variant={result.validation.valid ? "secondary" : "destructive"}>
              {result.validation.valid ? "valid" : `${result.validation.errors.length} errors`}
            </Badge>
          </CardTitle>
          <CardDescription>Read-only preview. Edit it in the JSON tab before generating.</CardDescription>
          <CardAction>
            <Stack direction="row" gap="xs">
              <Button variant="outline" size="sm" onClick={() => downloadText("backend-spec.json", specText)}>
                <Download /> Download .json
              </Button>
              <Tooltip>
                <TooltipTrigger render={<span />}>
                  <Button variant="outline" size="sm" disabled>
                    <Sparkles /> Refine with AI
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Arrives with requirement drafting (Story 2.4)</TooltipContent>
              </Tooltip>
            </Stack>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border">
            <JsonEditor path="imported-spec.json" value={specText} readOnly height={320} />
          </div>
        </CardContent>
      </Card>

      <NotesPanel kind="unresolved" notes={result.unresolved} />
      <NotesPanel kind="assumptions" notes={result.assumptions} />

      <Card>
        <CardHeader>
          <CardTitle>Bindings ({result.bindings.length})</CardTitle>
          <CardDescription>Which UI element on which page drives which endpoint.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="max-h-72 overflow-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Page</TableHead>
                  <TableHead>Component</TableHead>
                  <TableHead>operationId</TableHead>
                  <TableHead>Params</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.bindings.map((binding, index) => (
                  <TableRow key={`${binding.componentPath ?? index}-${binding.operationId}`}>
                    <TableCell>{binding.page ?? "—"}</TableCell>
                    <TableCell title={binding.componentPath}>{binding.component ?? "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{binding.operationId ?? "—"}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {binding.params && Object.keys(binding.params).length ? previewValue(binding.params) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Seed data</CardTitle>
          <CardDescription>The site&apos;s records, loaded into the preview database.</CardDescription>
        </CardHeader>
        <CardContent>
          <Stack gap="md">
            {result.seed.map((block) => {
              const columns = Object.keys(block.records[0] ?? {}).slice(0, PREVIEW_COLUMNS);
              return (
                <Stack key={block.entity} gap="xs">
                  <h3 className="text-sm font-medium">
                    {block.entity} <span className="text-muted-foreground">({block.records.length} rows)</span>
                  </h3>
                  <div className="overflow-auto rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {columns.map((column) => (
                            <TableHead key={column}>{column}</TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {block.records.slice(0, PREVIEW_ROWS).map((record, index) => (
                          <TableRow key={index}>
                            {columns.map((column) => (
                              <TableCell key={column} className="max-w-56 truncate text-xs">
                                {previewValue(record[column])}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </Stack>
              );
            })}
            {result.seed.length === 0 && <p className="text-sm text-muted-foreground">No records in the site JSON.</p>}
          </Stack>
        </CardContent>
      </Card>

      <Stack direction="row" justify="between" align="center" wrap className="gap-y-3">
        {needsAcknowledgement ? (
          <Label className="flex items-center gap-2 font-normal">
            <Checkbox checked={acknowledged} onCheckedChange={(value) => onAcknowledge(value === true)} />
            I reviewed the assumptions and unresolved items
          </Label>
        ) : (
          <span />
        )}
        <Button onClick={onEdit} disabled={!canEdit}>
          Edit in JSON tab <ArrowRight />
        </Button>
      </Stack>
    </Stack>
  );
}
