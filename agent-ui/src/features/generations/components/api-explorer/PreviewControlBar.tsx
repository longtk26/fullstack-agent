"use client";

import { useState } from "react";
import { Copy, ExternalLink, Logs, Play, RefreshCw, RotateCcw, Square } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useNow } from "@/hooks/use-now";
import { formatDuration } from "../../lib/status";
import type { TPreview, TPreviewAction, TPreviewStatus } from "../../types";

const STATUS_TONE: Record<TPreviewStatus, string> = {
  STARTING: "bg-info/15 text-info",
  RUNNING: "bg-success/15 text-success",
  STOPPED: "bg-muted text-muted-foreground",
  FAILED: "bg-destructive/10 text-destructive",
};

type PreviewControlBarProps = {
  preview: TPreview | null;
  pending: TPreviewAction | null | undefined;
  onAction: (action: TPreviewAction) => void;
  onOpenLogs: () => void;
};

export function PreviewControlBar({ preview, pending, onAction, onOpenLogs }: PreviewControlBarProps) {
  const status = preview?.status;
  const running = status === "RUNNING";
  const busy = Boolean(pending && pending !== "touch") || status === "STARTING";
  const now = useNow(running, 30_000);
  const expiresIn = running && preview?.expiresAt ? Date.parse(preview.expiresAt) - now : null;

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium">Preview</span>
        <Badge variant="secondary" className={status ? STATUS_TONE[status] : undefined}>
          {status === "STARTING" && <Spinner />}
          {status?.toLowerCase() ?? "not started"}
        </Badge>
        {running && preview?.url && (
          <span className="flex items-center gap-1 font-mono text-xs">
            {preview.url}
            <Button
              variant="ghost"
              size="icon-xs"
              aria-label="Copy URL"
              onClick={() => navigator.clipboard.writeText(preview.url ?? "").then(() => toast.success("URL copied"))}
            >
              <Copy />
            </Button>
            <a
              href={preview.docsUrl ?? preview.url}
              target="_blank"
              rel="noreferrer"
              aria-label="Open Swagger UI"
              className={buttonVariants({ variant: "ghost", size: "icon-xs" })}
            >
              <ExternalLink />
            </a>
          </span>
        )}
        {expiresIn !== null && (
          <span className="text-xs text-muted-foreground">
            stops after {formatDuration(Math.max(0, expiresIn))} idle
          </span>
        )}
        <div className="ml-auto flex flex-wrap gap-2">
          {running || status === "STARTING" ? (
            <>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => onAction("restart")}>
                <RefreshCw /> Restart
              </Button>
              <ResetDatabaseButton disabled={busy} onConfirm={() => onAction("reset-db")} />
              <Button size="sm" variant="outline" disabled={busy && !running} onClick={() => onAction("stop")}>
                <Square /> Stop
              </Button>
            </>
          ) : (
            <Button size="sm" disabled={busy} onClick={() => onAction("start")}>
              {busy ? <Spinner /> : <Play />} Start preview
            </Button>
          )}
          <Button size="sm" variant="ghost" disabled={!preview} onClick={onOpenLogs}>
            <Logs /> Logs
          </Button>
        </div>
      </div>
      {status === "FAILED" && preview?.error && (
        <p className="rounded-md bg-destructive/10 px-2 py-1 text-xs text-destructive">{preview.error}</p>
      )}
      {status === "STOPPED" && preview?.error && (
        <p className="text-xs text-muted-foreground">Stopped: {preview.error}</p>
      )}
    </div>
  );
}

function ResetDatabaseButton({ disabled, onConfirm }: { disabled: boolean; onConfirm: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger render={<Button size="sm" variant="outline" disabled={disabled} />}>
        <RotateCcw /> Reset DB
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Reset the preview database?</AlertDialogTitle>
          <AlertDialogDescription>
            Every row created in this preview is deleted. Migrations and seed data are applied again.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() => {
              setOpen(false);
              onConfirm();
            }}
          >
            Reset
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
