"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, AppWindow, Database, Play, ShieldAlert, Sparkles } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fetchFrontendSpec } from "@/features/specs/api/specs-api";
import { usePreview } from "../../hooks/use-preview";
import type { TDetailTab, TGenerationDetail } from "../../types";
import { AppDataPanel } from "./AppDataPanel";
import { AppNetworkPanel } from "./AppNetworkPanel";
import { AppToolbar, type TAppPageOption, type TDeviceSize } from "./AppToolbar";

type AppTabProps = {
  detail: TGenerationDetail;
  onOpenTab: (tab: TDetailTab) => void;
};

const DEVICE_WIDTH: Record<TDeviceSize, string> = {
  desktop: "w-full",
  tablet: "w-[820px] max-w-full",
  mobile: "w-[390px] max-w-full",
};

export function AppTab({ detail, onOpenTab }: AppTabProps) {
  const id = detail.generationId;
  const isDynamic = detail.mode === "dynamic";
  const { preview, run, pending, recheck, isRechecking, useMocks, isUsingMocks } = usePreview(
    id,
    detail.frontendPreview,
    "frontend",
  );

  const [currentRoute, setCurrentRoute] = useState("/");
  const [deviceSize, setDeviceSize] = useState<TDeviceSize>("desktop");
  const [sidePanelTab, setSidePanelTab] = useState<"network" | "data">("network");
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Fetch FrontendSpec to populate Page Jumper
  const frontendSpec = useQuery({
    queryKey: ["frontend-spec", detail.frontendSpecId],
    queryFn: () => fetchFrontendSpec(detail.frontendSpecId!),
    enabled: Boolean(detail.frontendSpecId),
  });

  const pages: TAppPageOption[] = useMemo(() => {
    const rawPages =
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (frontendSpec.data?.normalized as any)?.pages ??
      (() => {
        try {
          return frontendSpec.data?.raw ? JSON.parse(frontendSpec.data.raw).pages : null;
        } catch {
          return null;
        }
      })();

    if (Array.isArray(rawPages) && rawPages.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return rawPages.map((p: any) => ({
        title: p.title || p.name || p.route || "Page",
        route: p.route || "/",
      }));
    }

    return [{ title: "Home", route: "/" }];
  }, [frontendSpec.data]);

  const previewBaseUrl = preview?.url?.replace(/\/$/, "");
  const iframeSrc = previewBaseUrl ? `${previewBaseUrl}${currentRoute}` : "";

  const handleNavigate = (route: string) => {
    setCurrentRoute(route);
    if (iframeRef.current && previewBaseUrl) {
      iframeRef.current.src = `${previewBaseUrl}${route}`;
    }
  };

  const handleBack = () => {
    try {
      iframeRef.current?.contentWindow?.history.back();
    } catch {
      // Cross-origin fallback
    }
  };

  const handleForward = () => {
    try {
      iframeRef.current?.contentWindow?.history.forward();
    } catch {
      // Cross-origin fallback
    }
  };

  const handleReload = () => {
    try {
      iframeRef.current?.contentWindow?.location.reload();
    } catch {
      if (iframeRef.current && iframeSrc) {
        iframeRef.current.src = iframeSrc;
      }
    }
  };

  // Keep iframe in sync if preview URL changes
  useEffect(() => {
    if (iframeRef.current && iframeSrc) {
      iframeRef.current.src = iframeSrc;
    }
  }, [iframeSrc]);

  const isRunning = preview?.status === "RUNNING";
  const isMock = preview?.mockApi ?? true;

  // Extract mock reason if running on mocks in dynamic mode
  const mockReason = isDynamic && isMock ? detail.error ?? "Backend preview was not ready when integration checked." : null;

  return (
    <div className="flex flex-col gap-4">
      {/* Backend not ready / running on mocks warning banner */}
      {isDynamic && isRunning && isMock && (
        <Alert variant="default" className="border-warning/40 bg-warning/10 text-foreground">
          <ShieldAlert className="size-4 text-warning" />
          <AlertTitle className="text-warning font-semibold">Backend not ready — running on mocks</AlertTitle>
          <AlertDescription className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span>{mockReason}</span>
            <Button
              size="xs"
              variant="outline"
              className="bg-card text-xs"
              onClick={recheck}
              disabled={isRechecking}
            >
              Re-check backend now
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Main Toolbar */}
      <AppToolbar
        currentRoute={currentRoute}
        onNavigate={handleNavigate}
        onBack={handleBack}
        onForward={handleForward}
        onReload={handleReload}
        pages={pages}
        deviceSize={deviceSize}
        onDeviceSizeChange={setDeviceSize}
        preview={preview}
        onPreviewAction={run}
        pendingAction={pending}
        backendUrl={detail.preview?.url ?? null}
        isDynamic={isDynamic}
        onRecheck={recheck}
        isRechecking={isRechecking}
        onUseMocks={useMocks}
        isUsingMocks={isUsingMocks}
      />

      {/* Content Area */}
      <div
        className={
          isDynamic
            ? "grid grid-cols-1 lg:grid-cols-[1fr_360px] xl:grid-cols-[1fr_420px] gap-4"
            : "w-full"
        }
      >
        {/* Preview Frame */}
        <div className="flex flex-col items-center justify-start min-h-[720px] bg-muted/20 border rounded-lg p-4 overflow-x-auto">
          {isRunning && iframeSrc ? (
            <div
              className={`flex flex-col transition-all duration-300 mx-auto ${DEVICE_WIDTH[deviceSize]}`}
              style={{
                height: deviceSize === "mobile" ? "780px" : deviceSize === "tablet" ? "880px" : "800px",
              }}
            >
              <div
                className={`flex-1 overflow-hidden bg-background shadow-lg border border-border ${
                  deviceSize !== "desktop" ? "rounded-2xl ring-8 ring-muted/60" : "rounded-lg"
                }`}
              >
                <iframe
                  ref={iframeRef}
                  src={iframeSrc}
                  title="Application preview"
                  className="size-full border-0 bg-background"
                  sandbox="allow-scripts allow-forms allow-same-origin"
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center my-auto p-8 text-center max-w-md">
              <div className="size-14 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                <AppWindow className="size-7 text-primary" />
              </div>
              <h3 className="text-base font-semibold">
                {preview?.status === "STARTING" ? "Frontend preview starting…" : "Preview not running"}
              </h3>
              <p className="mt-1.5 text-xs text-muted-foreground">
                {preview?.status === "STARTING"
                  ? "The container is bootstrapping. It will be available momentarily."
                  : "Start the container to preview, navigate, and test the generated web application."}
              </p>
              {preview?.status !== "STARTING" && (
                <Button size="sm" className="mt-4 gap-1.5" onClick={() => run("start")}>
                  <Play className="size-3.5" /> Start Preview
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Dynamic Mode Side Panels (Network / Data) */}
        {isDynamic && (
          <div className="flex flex-col h-[800px]">
            <Tabs
              value={sidePanelTab}
              onValueChange={(val) => setSidePanelTab(val as "network" | "data")}
              className="flex flex-col h-full"
            >
              <TabsList className="w-full grid grid-cols-2">
                <TabsTrigger value="network" className="text-xs gap-1.5">
                  <Activity className="size-3.5" /> Network
                </TabsTrigger>
                <TabsTrigger value="data" className="text-xs gap-1.5">
                  <Database className="size-3.5" /> Data
                </TabsTrigger>
              </TabsList>

              <TabsContent value="network" className="flex-1 mt-2 min-h-0">
                <AppNetworkPanel
                  generationId={id}
                  onOpenApiTab={() => onOpenTab("api")}
                />
              </TabsContent>

              <TabsContent value="data" className="flex-1 mt-2 min-h-0">
                <AppDataPanel detail={detail} />
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>

      {/* Static site hint */}
      {!isDynamic && (
        <div className="rounded-lg border bg-card/60 p-3 text-xs text-muted-foreground flex items-center gap-2">
          <Sparkles className="size-4 text-primary shrink-0" />
          <span>
            <strong>Static site:</strong> No backend container is required. Content, components, and pages are bundled directly in the frontend build.
          </span>
        </div>
      )}
    </div>
  );
}
