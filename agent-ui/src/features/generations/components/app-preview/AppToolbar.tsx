"use client";

import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  Laptop,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Square,
  Tablet,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Stack } from "@/components/layout/Stack";
import type { TPreview, TPreviewAction } from "../../types";

export type TDeviceSize = "desktop" | "tablet" | "mobile";

export type TAppPageOption = {
  title: string;
  route: string;
};

type AppToolbarProps = {
  currentRoute: string;
  onNavigate: (route: string) => void;
  onBack: () => void;
  onForward: () => void;
  onReload: () => void;
  pages: TAppPageOption[];
  deviceSize: TDeviceSize;
  onDeviceSizeChange: (size: TDeviceSize) => void;
  preview: TPreview | null;
  onPreviewAction: (action: TPreviewAction) => void;
  pendingAction: TPreviewAction | null;
  backendUrl: string | null;
  isDynamic: boolean;
  onRecheck: () => void;
  isRechecking: boolean;
  onUseMocks: () => void;
  isUsingMocks: boolean;
};

export function AppToolbar({
  currentRoute,
  onNavigate,
  onBack,
  onForward,
  onReload,
  pages,
  deviceSize,
  onDeviceSizeChange,
  preview,
  onPreviewAction,
  pendingAction,
  backendUrl,
  isDynamic,
  onRecheck,
  isRechecking,
  onUseMocks,
  isUsingMocks,
}: AppToolbarProps) {
  const [addressInput, setAddressInput] = useState(currentRoute);
  const isRunning = preview?.status === "RUNNING";
  const isMock = preview?.mockApi ?? true;
  const fullUrl = preview?.url ? `${preview.url.replace(/\/$/, "")}${currentRoute}` : null;

  const handleAddressSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    let target = addressInput.trim();
    if (!target.startsWith("/")) target = `/${target}`;
    onNavigate(target);
  };

  const handlePageSelect = (value: string | null) => {
    if (!value) return;
    setAddressInput(value);
    onNavigate(value);
  };

  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-2.5 shadow-xs">
      <Stack direction="row" justify="between" align="center" wrap className="gap-2">
        {/* Navigation & Address Bar */}
        <div className="flex flex-1 items-center gap-1.5 min-w-[280px]">
          <div className="flex items-center gap-0.5">
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button size="sm" variant="ghost" className="size-8 p-0" onClick={onBack} disabled={!isRunning}>
                  <ArrowLeft className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Back</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button size="sm" variant="ghost" className="size-8 p-0" onClick={onForward} disabled={!isRunning}>
                  <ArrowRight className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Forward</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button size="sm" variant="ghost" className="size-8 p-0" onClick={onReload} disabled={!isRunning}>
                  <RotateCcw className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reload page</TooltipContent>
            </Tooltip>
          </div>

          {/* Page Jumper */}
          {pages.length > 0 && (
            <Select
              items={pages.map((p) => ({ value: p.route, label: `${p.title} (${p.route})` }))}
              value={pages.some((p) => p.route === currentRoute) ? currentRoute : null}
              onValueChange={handlePageSelect}
            >
              <SelectTrigger size="sm" className="w-44 text-xs shrink-0" aria-label="Jump to page">
                <SelectValue placeholder="Jump to page…" />
              </SelectTrigger>
              <SelectContent>
                {pages.map((page) => (
                  <SelectItem key={page.route} value={page.route}>
                    <span className="font-medium">{page.title}</span>{" "}
                    <span className="text-muted-foreground font-mono text-[11px]">{page.route}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Address input */}
          <form onSubmit={handleAddressSubmit} className="flex-1 min-w-[140px]">
            <Input
              value={addressInput}
              onChange={(e) => setAddressInput(e.target.value)}
              placeholder="/"
              className="h-8 font-mono text-xs"
              disabled={!isRunning}
            />
          </form>
        </div>

        {/* Device sizes & External link */}
        <Stack direction="row" gap="xs" align="center">
          <div className="flex items-center rounded-md border bg-muted/40 p-0.5">
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button
                  size="sm"
                  variant={deviceSize === "desktop" ? "secondary" : "ghost"}
                  className="size-7 p-0"
                  onClick={() => onDeviceSizeChange("desktop")}
                >
                  <Laptop className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Desktop (Responsive)</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button
                  size="sm"
                  variant={deviceSize === "tablet" ? "secondary" : "ghost"}
                  className="size-7 p-0"
                  onClick={() => onDeviceSizeChange("tablet")}
                >
                  <Tablet className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Tablet (820px)</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button
                  size="sm"
                  variant={deviceSize === "mobile" ? "secondary" : "ghost"}
                  className="size-7 p-0"
                  onClick={() => onDeviceSizeChange("mobile")}
                >
                  <Smartphone className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Mobile (390px)</TooltipContent>
            </Tooltip>
          </div>

          {fullUrl && (
            <Tooltip>
              <TooltipTrigger render={<span />}>
                <Button
                  size="sm"
                  variant="outline"
                  className="size-8 p-0"
                  render={<a href={fullUrl} target="_blank" rel="noreferrer" />}
                  nativeButton={false}
                >
                  <ExternalLink className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Open in a new tab</TooltipContent>
            </Tooltip>
          )}
        </Stack>
      </Stack>

      {/* Second row: Status, Integration Switch, Backend URL, Preview Lifecycle */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-2 text-xs">
        <Stack direction="row" gap="sm" align="center" wrap>
          {isDynamic && (
            <Badge
              variant={isMock ? "secondary" : "default"}
              className={
                isMock
                  ? "border-warning/30 bg-warning/15 text-warning font-medium"
                  : "bg-success text-success-foreground font-medium"
              }
            >
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

          {isDynamic && (
            <span className="text-muted-foreground flex items-center gap-1">
              Backend:{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">
                {!isMock && backendUrl ? backendUrl : "Local MSW mocks"}
              </code>
            </span>
          )}

          {isDynamic && isRunning && (
            <Stack direction="row" gap="xs" align="center">
              <Button
                size="xs"
                variant="outline"
                className="h-6 gap-1 px-2 text-[11px]"
                onClick={onRecheck}
                disabled={isRechecking || isUsingMocks}
              >
                {isRechecking ? <Spinner className="size-3" /> : <RefreshCw className="size-3" />}
                {isMock ? "Use live API" : "Re-check backend"}
              </Button>
              {!isMock && (
                <Button
                  size="xs"
                  variant="outline"
                  className="h-6 gap-1 px-2 text-[11px]"
                  onClick={onUseMocks}
                  disabled={isRechecking || isUsingMocks}
                >
                  {isUsingMocks ? <Spinner className="size-3" /> : <ShieldAlert className="size-3 text-warning" />}
                  Use mocks
                </Button>
              )}
            </Stack>
          )}
        </Stack>

        {/* Lifecycle controls */}
        <Stack direction="row" gap="xs" align="center">
          <span className="text-muted-foreground text-[11px]">
            Preview: <strong className="text-foreground font-medium">{(preview?.status ?? "STOPPED").toLowerCase()}</strong>
          </span>
          {!isRunning ? (
            <Button
              size="xs"
              className="h-6 gap-1 px-2 text-[11px]"
              onClick={() => onPreviewAction("start")}
              disabled={Boolean(pendingAction)}
            >
              {pendingAction === "start" ? <Spinner className="size-3" /> : <Play className="size-3" />} Start
            </Button>
          ) : (
            <>
              <Button
                size="xs"
                variant="ghost"
                className="h-6 gap-1 px-2 text-[11px]"
                onClick={() => onPreviewAction("restart")}
                disabled={Boolean(pendingAction)}
              >
                {pendingAction === "restart" ? <Spinner className="size-3" /> : <RefreshCw className="size-3" />} Restart
              </Button>
              <Button
                size="xs"
                variant="ghost"
                className="h-6 gap-1 px-2 text-[11px] text-destructive hover:text-destructive"
                onClick={() => onPreviewAction("stop")}
                disabled={Boolean(pendingAction)}
              >
                {pendingAction === "stop" ? <Spinner className="size-3" /> : <Square className="size-3" />} Stop
              </Button>
            </>
          )}
        </Stack>
      </div>
    </div>
  );
}
