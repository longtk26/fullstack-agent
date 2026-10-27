"use client";

import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { Stack } from "@/components/layout/Stack";
import { KIND_STYLE } from "../../lib/span-style";
import { formatDuration } from "../../lib/status";
import type { TTraceSpan } from "../../types";
import { SpanOutput } from "./SpanOutput";

type SpanDrawerProps = {
  generationId: string;
  span: TTraceSpan | null;
  langsmithUrl: string | null;
  onClose: () => void;
};

const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: "medium" });

function formatValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 1);
  return String(value);
}

export function SpanDrawer({ generationId, span, langsmithUrl, onClose }: SpanDrawerProps) {
  return (
    <Sheet open={span !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
        {span && (
          <>
            <SheetHeader>
              <SheetTitle className="font-mono text-sm break-all">{span.name}</SheetTitle>
              <SheetDescription className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{KIND_STYLE[span.kind].label}</Badge>
                <Badge variant={span.error ? "destructive" : "secondary"}>{span.status}</Badge>
                <span>
                  {span.startedAt ? timeFormat.format(new Date(span.startedAt)) : "—"} ·{" "}
                  {span.durationMs != null ? formatDuration(span.durationMs) : span.endedAt ? "—" : "running"}
                </span>
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-4 pb-6">
              <Stack gap="md">
                {langsmithUrl && (
                  <div>
                    <Button
                      variant="outline"
                      size="sm"
                      render={<a href={langsmithUrl} target="_blank" rel="noreferrer" />}
                      nativeButton={false}
                    >
                      <ExternalLink /> Open in LangSmith
                    </Button>
                  </div>
                )}
                <div className="rounded-lg border">
                  <Table>
                    <TableBody>
                      {Object.entries(span.attrs).map(([key, value]) => (
                        <TableRow key={key}>
                          <TableCell className="w-40 align-top text-xs text-muted-foreground">{key}</TableCell>
                          <TableCell className="font-mono text-xs break-all whitespace-pre-wrap">
                            {formatValue(value)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <SpanOutput key={span.spanId} generationId={generationId} span={span} />
              </Stack>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
