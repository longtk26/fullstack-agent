"use client";

import { Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useSpanOutput } from "../../hooks/use-span-output";
import type { TSpanStream, TTraceSpan } from "../../types";

type SpanOutputProps = {
  generationId: string;
  span: TTraceSpan;
};

function lineClass(line: string): string | undefined {
  if (line.startsWith("+++") || line.startsWith("---")) return "text-muted-foreground";
  if (line.startsWith("+")) return "text-success";
  if (line.startsWith("-")) return "text-destructive";
  if (line.startsWith("@@")) return "text-info";
  return undefined;
}

/** Tail of a span's output: CLI stdout/stderr, a check's output, or a repair patch with diff highlighting. */
export function SpanOutput({ generationId, span }: SpanOutputProps) {
  const view = useSpanOutput(generationId, span);
  if (!view.hasOutput) return null;
  const data = view.output.data;
  const patch = data?.stream === "patch";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {view.hasStreams ? (
          <Tabs value={view.stream} onValueChange={(value) => view.setStream(value as TSpanStream)}>
            <TabsList>
              <TabsTrigger value="stdout">stdout</TabsTrigger>
              <TabsTrigger value="stderr">stderr</TabsTrigger>
            </TabsList>
          </Tabs>
        ) : (
          <h3 className="text-sm font-medium">{patch ? "Patch" : "Output"}</h3>
        )}
        <div className="flex items-center gap-1">
          {view.canLoadMore && (
            <Button variant="ghost" size="sm" onClick={view.loadMore}>
              Load more
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            disabled={!data}
            onClick={async () => {
              await view.copy();
              toast.success("Copied");
            }}
          >
            <Copy /> Copy
          </Button>
        </div>
      </div>
      {view.output.isLoading && <Skeleton className="h-48 w-full" />}
      {view.output.isError && <p className="text-sm text-muted-foreground">{view.output.error.message}</p>}
      {data && (
        <pre className="max-h-[420px] overflow-auto rounded-md bg-muted/60 p-2 text-xs leading-relaxed">
          {data.truncated && <span className="block text-muted-foreground">… earlier output omitted</span>}
          {data.text
            ? data.text.split("\n").map((line, index) => (
                <span key={index} className={cn("block whitespace-pre", patch && lineClass(line))}>
                  {line || " "}
                </span>
              ))
            : "(empty)"}
        </pre>
      )}
    </div>
  );
}
