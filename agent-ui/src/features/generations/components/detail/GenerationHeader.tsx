"use client";

import Link from "next/link";
import { ArrowLeft, Coins, ExternalLink, Radio, RotateCcw, Timer } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Stack } from "@/components/layout/Stack";
import { useNow } from "@/hooks/use-now";
import { cn } from "@/lib/utils";
import type { TStreamState } from "../../hooks/use-generation-stream";
import { elapsedMs, formatDuration, formatStep, isTerminal } from "../../lib/status";
import type { TGenerationDetail } from "../../types";
import { StatusBadge } from "../StatusBadge";
import { CancelGenerationButton } from "./CancelGenerationButton";

const STREAM_LABEL: Record<TStreamState, string> = {
  connecting: "Connecting to the live stream…",
  open: "Live",
  reconnecting: "Reconnecting…",
  closed: "Stream closed (job finished)",
};

const numberFormat = new Intl.NumberFormat();

type GenerationHeaderProps = {
  detail: TGenerationDetail;
  streamState: TStreamState;
};

export function GenerationHeader({ detail, streamState }: GenerationHeaderProps) {
  const terminal = isTerminal(detail.status);
  const now = useNow(!terminal && detail.startedAt !== null);
  const elapsed = elapsedMs(detail.startedAt, detail.finishedAt, now);
  const tokens = detail.usage.inputTokens + detail.usage.outputTokens;

  return (
    <Stack gap="sm">
      <Link
        href="/generations"
        className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Generations
      </Link>
      <Stack direction="row" justify="between" align="start" wrap className="gap-y-3">
        <Stack gap="xs">
          <Stack direction="row" gap="sm" align="center" wrap>
            <h1 className="text-2xl font-semibold tracking-tight">{detail.projectName ?? "Untitled project"}</h1>
            <StatusBadge status={detail.status} />
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Radio
                  className={cn(
                    "size-4",
                    streamState === "open" ? "animate-pulse text-success" : "text-muted-foreground",
                    streamState === "reconnecting" && "text-warning",
                  )}
                  aria-label={STREAM_LABEL[streamState]}
                />
              </TooltipTrigger>
              <TooltipContent>{STREAM_LABEL[streamState]}</TooltipContent>
            </Tooltip>
          </Stack>
          <Stack direction="row" gap="md" align="center" wrap className="text-sm text-muted-foreground">
            <span className="font-mono text-xs">{detail.generationId}</span>
            {!terminal && <span>Step: {formatStep(detail.currentStep)}</span>}
            <span>Engine: {detail.engine}</span>
            <span className="flex items-center gap-1 tabular-nums">
              <Timer className="size-3.5" /> {elapsed === null ? "not started" : formatDuration(elapsed)}
            </span>
            <span className="flex items-center gap-1 tabular-nums">
              <Coins className="size-3.5" /> {numberFormat.format(tokens)} tokens · ${detail.usage.costUsd.toFixed(4)}
            </span>
            {detail.resumeCount > 0 && (
              <Badge variant="outline">
                <RotateCcw /> resumed ×{detail.resumeCount}
              </Badge>
            )}
          </Stack>
        </Stack>
        <Stack direction="row" gap="xs">
          {detail.trace.langsmithUrl ? (
            <Button
              variant="outline"
              size="sm"
              render={<a href={detail.trace.langsmithUrl} target="_blank" rel="noreferrer" />}
              nativeButton={false}
            >
              <ExternalLink /> LangSmith
            </Button>
          ) : (
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button variant="outline" size="sm" disabled>
                  <ExternalLink /> LangSmith
                </Button>
              </TooltipTrigger>
              <TooltipContent>Tracing is not configured (set LANGSMITH_API_KEY)</TooltipContent>
            </Tooltip>
          )}
          <CancelGenerationButton
            generationId={detail.generationId}
            disabled={terminal}
            cancelRequested={detail.cancelRequested && !terminal}
          />
        </Stack>
      </Stack>
    </Stack>
  );
}
