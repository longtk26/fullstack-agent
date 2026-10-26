"use client";

import { PlugZap } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Stack } from "@/components/layout/Stack";
import { useApiTab } from "../../hooks/use-api-tab";
import type { TGenerationDetail } from "../../types";
import { ComingSoonPanel } from "../detail/ComingSoonPanel";
import { ApiExplorer } from "./ApiExplorer";
import { PreviewControlBar } from "./PreviewControlBar";
import { PreviewLogsSheet } from "./PreviewLogsSheet";

type ApiTabProps = {
  detail: TGenerationDetail;
};

export function ApiTab({ detail }: ApiTabProps) {
  const tab = useApiTab(detail);
  const running = tab.preview?.status === "RUNNING";

  if (!tab.hasOpenapi) {
    return (
      <ComingSoonPanel
        icon={PlugZap}
        title="No API description yet"
        description={
          detail.status === "COMPLETED"
            ? "This generation has no exported OpenAPI (it ran without the sandbox)."
            : "The OpenAPI explorer appears when the generation completes."
        }
      />
    );
  }
  return (
    <Stack gap="md">
      {tab.canPreview && (
        <PreviewControlBar
          preview={tab.preview}
          pending={tab.pending}
          onAction={tab.run}
          onOpenLogs={() => tab.setLogsOpen(true)}
        />
      )}
      {!running && (
        <p className="text-xs text-muted-foreground">
          Read-only: start the preview to send requests to the generated backend.
        </p>
      )}
      {tab.document ? (
        <ApiExplorer
          document={tab.document}
          serverUrl={running ? tab.preview?.url ?? null : null}
          onRequestSent={tab.touch}
        />
      ) : (
        <Skeleton className="h-[720px] w-full" />
      )}
      <PreviewLogsSheet generationId={detail.generationId} open={tab.logsOpen} onOpenChange={tab.setLogsOpen} />
    </Stack>
  );
}
