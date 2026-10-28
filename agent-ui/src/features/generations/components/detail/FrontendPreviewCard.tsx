"use client";

import { useState } from "react";
import { AppWindow, Check, Copy, ExternalLink, Play, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Stack } from "@/components/layout/Stack";
import { usePreview } from "../../hooks/use-preview";
import type { TGenerationDetail } from "../../types";

type FrontendPreviewCardProps = {
  detail: TGenerationDetail;
  className?: string;
  onOpenAppTab?: () => void;
};

export function FrontendPreviewCard({ detail, className, onOpenAppTab }: FrontendPreviewCardProps) {
  const id = detail.generationId;
  const isDynamic = detail.mode === "dynamic";
  const { preview, run, pending, recheck, isRechecking, useMocks, isUsingMocks } = usePreview(
    id,
    detail.frontendPreview,
    "frontend",
  );
  const [copied, setCopied] = useState(false);

  const status = preview?.status ?? "STOPPED";
  const isRunning = status === "RUNNING";
  const url = preview?.url;
  const isMock = preview?.mockApi ?? (detail.frontendPreview?.mockApi ?? true);
  const backendUrl = detail.preview?.url;

  const copyUrl = () => {
    if (!url) return;
    void navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      toast.success("Preview URL copied");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <Stack direction="row" justify="between" align="start" wrap className="gap-2">
          <div>
            <Stack direction="row" gap="xs" align="center">
              <AppWindow className="size-5 text-primary" />
              <CardTitle className="text-base font-semibold">Frontend Preview</CardTitle>
              {isDynamic && (
                <Badge variant={isMock ? "secondary" : "default"} className={isMock ? "bg-warning/20 text-warning border-warning/30" : "bg-success text-success-foreground"}>
                  {isMock ? (
                    <span className="flex items-center gap-1">
                      <ShieldAlert className="size-3" /> Mock API
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <ShieldCheck className="size-3" /> Live API
                    </span>
                  )}
                </Badge>
              )}
            </Stack>
            <CardDescription className="mt-1">
              {isDynamic ? (
                <span>
                  Backend in use:{" "}
                  <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                    {!isMock && backendUrl ? backendUrl : "Local MSW mocks (MOCK_TEST_API=true)"}
                  </code>
                </span>
              ) : (
                "Static site running with bundled content and components"
              )}
            </CardDescription>
          </div>

          <Stack direction="row" gap="xs" align="center" wrap>
            {isDynamic && isRunning && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={recheck}
                  disabled={isRechecking || isUsingMocks}
                >
                  {isRechecking ? <Spinner /> : <RefreshCw className="size-3.5" />}
                  Re-check backend
                </Button>
                {!isMock && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={useMocks}
                    disabled={isRechecking || isUsingMocks}
                  >
                    {isUsingMocks ? <Spinner /> : <ShieldAlert className="size-3.5 text-warning" />}
                    Use mocks
                  </Button>
                )}
              </>
            )}
            {isRunning && url && (
              <>
                <Tooltip>
                  <TooltipTrigger render={<span />}>
                    <Button size="sm" variant="ghost" onClick={copyUrl}>
                      {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Copy URL</TooltipContent>
                </Tooltip>
                <Button
                  size="sm"
                  variant="outline"
                  render={<a href={url} target="_blank" rel="noreferrer" />}
                  nativeButton={false}
                >
                  <ExternalLink className="size-3.5" /> Open in tab
                </Button>
                {onOpenAppTab && (
                  <Button size="sm" onClick={onOpenAppTab}>
                    <AppWindow className="size-3.5" /> Open app tab
                  </Button>
                )}
              </>
            )}
            {!isRunning && (
              <Button
                size="sm"
                onClick={() => run("start")}
                disabled={Boolean(pending)}
              >
                {pending === "start" ? <Spinner /> : <Play className="size-3.5" />} Start preview
              </Button>
            )}
            {isRunning && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => run("restart")}
                disabled={Boolean(pending)}
              >
                {pending === "restart" ? <Spinner /> : <RefreshCw className="size-3.5" />} Restart
              </Button>
            )}
          </Stack>
        </Stack>
      </CardHeader>
      <CardContent>
        {isRunning && url ? (
          <div className="relative aspect-video w-full overflow-hidden rounded-md border bg-background shadow-xs">
            <iframe
              src={url}
              title="Frontend preview"
              className="size-full border-0"
              sandbox="allow-scripts allow-forms allow-same-origin"
            />
          </div>
        ) : (
          <div className="flex h-56 flex-col items-center justify-center rounded-md border border-dashed bg-muted/20 p-6 text-center">
            <AppWindow className="size-10 text-muted-foreground/60" />
            <h3 className="mt-2 text-sm font-medium">
              {status === "STARTING" ? "Frontend preview starting…" : "Frontend preview not running"}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground max-w-sm">
              {status === "STARTING"
                ? "Launching the frontend preview container. It will be ready in a few seconds."
                : "Start the container to preview and test the generated frontend."}
            </p>
            {status !== "STARTING" && (
              <Button size="sm" className="mt-4" onClick={() => run("start")} disabled={Boolean(pending)}>
                {pending === "start" ? <Spinner /> : <Play className="size-3.5" />} Start preview
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
