"use client";

import { Activity, FileCode2, PlugZap, Waypoints } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Stack } from "@/components/layout/Stack";
import { useGenerationDetail } from "../../hooks/use-generation-detail";
import { ApiTab } from "../api-explorer/ApiTab";
import { ResultsTab } from "../results/ResultsTab";
import { ComingSoonPanel } from "./ComingSoonPanel";
import { EventLog } from "./EventLog";
import { GenerationHeader } from "./GenerationHeader";
import { StepDrawer } from "./StepDrawer";
import type { TDetailTab } from "../../types";
import { TerminalBanner } from "./TerminalBanner";
import { WorkflowDiagram } from "./WorkflowDiagram";

type GenerationDetailViewProps = {
  id: string;
};

export function GenerationDetailView({ id }: GenerationDetailViewProps) {
  const view = useGenerationDetail(id);
  const detail = view.detail.data;

  if (view.detail.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load this generation</AlertTitle>
        <AlertDescription>{view.detail.error.message}</AlertDescription>
      </Alert>
    );
  }
  if (!detail) return <GenerationDetailSkeleton />;

  return (
    <Stack gap="lg">
      <GenerationHeader detail={detail} streamState={view.streamState} />
      <TerminalBanner detail={detail} events={view.events} onOpenTab={view.setTab} />
      <Tabs value={view.tab} onValueChange={(value) => view.setTab(value as TDetailTab)}>
        <TabsList>
          <TabsTrigger value="steps">
            <Activity /> Steps
          </TabsTrigger>
          <TabsTrigger value="trace">
            <Waypoints /> Trace
          </TabsTrigger>
          <TabsTrigger value="results">
            <FileCode2 /> Results
          </TabsTrigger>
          <TabsTrigger value="api">
            <PlugZap /> API
          </TabsTrigger>
        </TabsList>
        <TabsContent value="steps" className="pt-2">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <Stack gap="sm">
              <h2 className="text-sm font-medium">Workflow</h2>
              <WorkflowDiagram
                graph={view.graph}
                progress={view.progress}
                selectedNode={view.selectedNode}
                onSelectNode={view.setSelectedNode}
                repairAttempts={view.repairAttempts}
                maxRepairAttempts={view.maxRepairAttempts}
              />
            </Stack>
            <EventLog events={view.events} />
          </div>
        </TabsContent>
        <TabsContent value="trace" className="pt-2">
          <ComingSoonPanel
            icon={Waypoints}
            title="Trace viewer"
            description="A span waterfall of every node and engine call arrives with tracing (Epic 8, Story 9.4)."
          />
        </TabsContent>
        <TabsContent value="results" className="pt-2">
          <ResultsTab detail={detail} />
        </TabsContent>
        <TabsContent value="api" className="pt-2">
          <ApiTab detail={detail} />
        </TabsContent>
      </Tabs>
      <StepDrawer
        node={view.selectedNode}
        steps={detail.steps}
        events={view.events}
        onClose={() => view.setSelectedNode(null)}
      />
    </Stack>
  );
}

export function GenerationDetailSkeleton() {
  return (
    <Stack gap="lg">
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-[720px] w-full" />
    </Stack>
  );
}
