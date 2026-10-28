import { Ban, CircleCheck, CircleX, TriangleAlert } from "lucide-react";
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { TDetailTab, TGenerationDetail, TGenerationEvent } from "../../types";

type TerminalBannerProps = {
  detail: TGenerationDetail;
  events: TGenerationEvent[];
  onOpenTab: (tab: TDetailTab) => void;
};

export function TerminalBanner({ detail, events, onOpenTab }: TerminalBannerProps) {
  const isStaticOrDynamic = detail.mode === "static" || detail.mode === "dynamic";

  if (detail.status === "COMPLETED") {
    return (
      <Alert>
        <CircleCheck className="text-success" />
        <AlertTitle>{detail.mode === "static" ? "Site generated" : detail.mode === "dynamic" ? "Web app generated" : "Backend generated"}</AlertTitle>
        <AlertDescription>
          {detail.mode === "static"
            ? "The site built and passed its checks and smoke tests."
            : detail.mode === "dynamic"
              ? "Both frontend and backend passed validation and live contract verification."
              : `Validation passed after ${detail.repairAttempts} repair attempt${detail.repairAttempts === 1 ? "" : "s"}.`}
        </AlertDescription>
        <AlertAction className="flex gap-2">
          {isStaticOrDynamic && (
            <Button size="sm" onClick={() => onOpenTab("app")}>
              App
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => onOpenTab("results")}>
            Results
          </Button>
          {detail.mode !== "static" && (
            <Button size="sm" variant="outline" onClick={() => onOpenTab("api")}>
              API
            </Button>
          )}
        </AlertAction>
      </Alert>
    );
  }
  if (detail.status === "COMPLETED_WITH_WARNINGS") {
    const backendDone = detail.lanes.backend === "COMPLETED";
    const keptEvt = events.findLast((e) => e.type === "integration.kept_mocks");
    const mockReason =
      (typeof keptEvt?.payload.reason === "string" ? keptEvt.payload.reason : null) ??
      (detail.lanes.integration === "SKIPPED" ? detail.error : null);

    return (
      <Alert>
        <TriangleAlert className="text-warning" />
        <AlertTitle>
          {detail.lanes.frontend === "COMPLETED" && backendDone
            ? "Frontend and backend generated, with warnings"
            : detail.lanes.frontend === "COMPLETED" && detail.lanes.backend !== "COMPLETED"
              ? "Frontend generated, running on mock API"
              : backendDone
                ? "Backend generated, with warnings"
                : "Finished with warnings"}
        </AlertTitle>
        <AlertDescription>
          {mockReason ? (
            <span>
              The frontend is running on <strong>mock data</strong> because the backend was not ready:{" "}
              <em>{mockReason}</em>
            </span>
          ) : (
            detail.error ?? "Some lanes did not complete."
          )}
        </AlertDescription>
        <AlertAction className="flex gap-2">
          {isStaticOrDynamic && (
            <Button size="sm" onClick={() => onOpenTab("app")}>
              App
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => onOpenTab("results")}>
            Results
          </Button>
          {backendDone && (
            <Button size="sm" variant="outline" onClick={() => onOpenTab("api")}>
              API
            </Button>
          )}
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
        <AlertDescription>{detail.error ?? "No error summary was recorded."}</AlertDescription>
        {detail.artifacts.length > 0 && (
          <AlertAction>
            <Button size="sm" variant="outline" onClick={() => onOpenTab("results")}>
              Diagnostic report
            </Button>
          </AlertAction>
        )}
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
