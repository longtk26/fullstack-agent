"use client";

import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePreviewLogs } from "../../hooks/use-preview-logs";

type PreviewLogsSheetProps = {
  generationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: "medium" });

export function PreviewLogsSheet({ generationId, open, onOpenChange }: PreviewLogsSheetProps) {
  const { logs, requests } = usePreviewLogs(generationId, open);
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-3xl">
        <SheetHeader>
          <SheetTitle>Preview container</SheetTitle>
          <SheetDescription>Refreshed every 3 seconds. Secrets are redacted.</SheetDescription>
        </SheetHeader>
        <Tabs defaultValue="requests" className="min-h-0 flex-1 px-4 pb-4">
          <TabsList>
            <TabsTrigger value="requests">Requests</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
          </TabsList>
          <TabsContent value="requests" className="min-h-0 overflow-auto">
            {requests.error ? (
              <p className="p-2 text-sm text-muted-foreground">{requests.error.message}</p>
            ) : requests.items.length === 0 ? (
              <p className="p-2 text-sm text-muted-foreground">No requests yet. Try an endpoint in the explorer.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Request</TableHead>
                    <TableHead>operationId</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">ms</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.items.map((item) => (
                    <TableRow key={`${item.ts}-${item.path}`}>
                      <TableCell className="text-xs tabular-nums">{timeFormat.format(new Date(item.ts))}</TableCell>
                      <TableCell className="max-w-72 truncate font-mono text-xs">
                        {item.method} {item.path}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{item.operationId ?? "—"}</TableCell>
                      <TableCell>
                        <Badge variant={item.status >= 400 ? "destructive" : "secondary"}>{item.status}</Badge>
                      </TableCell>
                      <TableCell className="text-right text-xs tabular-nums">{item.durationMs ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>
          <TabsContent value="logs" className="min-h-0 overflow-auto">
            {logs.error ? (
              <p className="p-2 text-sm text-muted-foreground">{logs.error.message}</p>
            ) : (
              <pre className="rounded-md bg-muted/60 p-3 text-xs leading-relaxed whitespace-pre-wrap">
                {(logs.data?.lines ?? []).join("\n") || "No output yet."}
              </pre>
            )}
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
