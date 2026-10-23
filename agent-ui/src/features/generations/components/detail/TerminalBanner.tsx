import { Ban, CircleCheck, CircleX } from "lucide-react";
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { TDetailTab, TGenerationDetail, TGenerationEvent } from "../../types";

type TerminalBannerProps = {
  detail: TGenerationDetail;
  events: TGenerationEvent[];
  onOpenTab: (tab: TDetailTab) => void;
};

export function TerminalBanner({ detail, events, onOpenTab }: TerminalBannerProps) {
  if (detail.status === "COMPLETED") {
    return (
      <Alert>
        <CircleCheck className="text-success" />
        <AlertTitle>Backend generated</AlertTitle>
        <AlertDescription>
          Validation passed after {detail.repairAttempts} repair attempt{detail.repairAttempts === 1 ? "" : "s"}.
        </AlertDescription>
        <AlertAction className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => onOpenTab("results")}>
            Results
          </Button>
          <Button size="sm" onClick={() => onOpenTab("api")}>
            API
          </Button>
        </AlertAction>
      </Alert>
    );
  }
  if (detail.status === "FAILED") {
    const final = events.findLast((event) => event.type === "status.changed" && event.status === "FAILED");
    const code = typeof final?.payload.errorCode === "string" ? final.payload.errorCode : null;
    return (
      <Alert variant="destructive">
        <CircleX />
        <AlertTitle>Generation failed{code ? ` · ${code}` : ""}</AlertTitle>
        <AlertDescription>
          <p>{detail.error ?? "No error summary was recorded."}</p>
          <p className="text-xs">The diagnostic report download arrives with the artifacts epic (Story 7.2).</p>
        </AlertDescription>
      </Alert>
    );
  }
  if (detail.status === "CANCELLED") {
    return (
      <Alert>
        <Ban />
        <AlertTitle>Generation cancelled</AlertTitle>
        <AlertDescription>The job stopped before finishing.</AlertDescription>
      </Alert>
    );
  }
  return null;
}
