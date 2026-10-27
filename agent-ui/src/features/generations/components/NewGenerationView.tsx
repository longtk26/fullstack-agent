"use client";

import { useEffect, useMemo } from "react";
import { AppWindow, Braces, FileInput, Globe, MessageSquareText, Rocket } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Stack } from "@/components/layout/Stack";
import { ConsistencyIssueList } from "@/features/specs/components/ConsistencyIssueList";
import { FrontendImportTab } from "@/features/specs/components/FrontendImportTab";
import { JsonTab } from "@/features/specs/components/JsonTab";
import { RequirementTab } from "@/features/specs/components/RequirementTab";
import { SpecSummaryPanel } from "@/features/specs/components/SpecSummaryPanel";
import { useExamplePairOffer } from "@/features/specs/hooks/use-example-pair-offer";
import { useJsonEditor } from "@/features/specs/hooks/use-json-editor";
import { useSpecPairCheck } from "@/features/specs/hooks/use-spec-pair-check";
import { useSpecValidation } from "@/features/specs/hooks/use-spec-validation";
import type { TEditorIssue } from "@/features/specs/hooks/use-spec-validation";
import { summarizeSpec } from "@/features/specs/lib/spec-summary";
import type { TSpecKind, TSpecTab } from "@/features/specs/types";
import { useSpecDraftStore } from "@/store/spec-draft-store";
import { useGenerationMode } from "../hooks/use-generation-mode";
import { useNewGeneration } from "../hooks/use-new-generation";
import type { TGenerationMode } from "../types";
import { GenerationOptionsForm } from "./GenerationOptionsForm";
import { ModeCards } from "./ModeCards";
import { SpecValidationCard } from "./SpecValidationCard";

const MODE_TABS: Record<TGenerationMode, TSpecTab[]> = {
  backend: ["requirement", "import", "json"],
  static: ["frontend"],
  dynamic: ["frontend", "json"],
};

const SUBMIT_LABELS: Record<TGenerationMode, string> = {
  backend: "Generate backend",
  static: "Generate site",
  dynamic: "Generate app",
};

const EMPTY_TEXT: Record<TSpecKind, string> = {
  backend: "Paste, load or import a BackendSpec to validate it.",
  frontend: "Paste, load or upload a FrontendSpec to validate it.",
};

export function NewGenerationView() {
  const { mode, setMode } = useGenerationMode();
  const specText = useSpecDraftStore((state) => state.specText);
  const setSpecText = useSpecDraftStore((state) => state.setSpecText);
  const frontendSpecText = useSpecDraftStore((state) => state.frontendSpecText);
  const setFrontendSpecText = useSpecDraftStore((state) => state.setFrontendSpecText);
  const activeTab = useSpecDraftStore((state) => state.activeTab);
  const setActiveTab = useSpecDraftStore((state) => state.setActiveTab);
  const clearDraft = useSpecDraftStore((state) => state.clearDraft);

  const editors = { backend: useJsonEditor(), frontend: useJsonEditor() };
  const backend = useSpecValidation("backend", specText);
  const frontend = useSpecValidation("frontend", frontendSpecText, mode === "backend" ? undefined : mode);
  const pair = useSpecPairCheck(
    mode === "dynamic",
    { ...frontend, text: frontendSpecText },
    { ...backend, text: specText },
  );
  const summary = useMemo(() => summarizeSpec(backend.parsed), [backend.parsed]);
  const offerPair = useExamplePairOffer(setSpecText);

  const canSubmit = {
    backend: backend.isSubmittable,
    static: frontend.isSubmittable,
    dynamic: frontend.isSubmittable && backend.isSubmittable && pair.isSubmittable,
  }[mode];
  const submit = useNewGeneration({
    mode,
    backendSpec: backend.parsed,
    frontendSpec: frontend.parsed,
    canSubmit,
    onCreated: clearDraft,
  });

  useEffect(() => {
    useSpecDraftStore.persist.rehydrate();
  }, []);

  const tabs = MODE_TABS[mode];
  const tab = tabs.includes(activeTab) ? activeTab : tabs[0];

  const jumpTo = (kind: TSpecKind, issue: TEditorIssue) => {
    setActiveTab(kind === "frontend" ? "frontend" : "json");
    requestAnimationFrame(() => editors[kind].jumpTo(issue));
  };
  const jumpToPointer = (kind: TSpecKind, pointer: string) =>
    jumpTo(kind, { code: "", path: pointer, message: "", hint: null, severity: "error" });

  return (
    <Stack gap="lg">
      <ModeCards mode={mode} onChange={setMode} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <Tabs value={tab} onValueChange={(value) => setActiveTab(value as TSpecTab)}>
          <TabsList>
            {tabs.includes("requirement") && (
              <TabsTrigger value="requirement">
                <MessageSquareText /> Requirement
              </TabsTrigger>
            )}
            {tabs.includes("import") && (
              <TabsTrigger value="import">
                <FileInput /> Import frontend JSON
              </TabsTrigger>
            )}
            {tabs.includes("frontend") && (
              <TabsTrigger value="frontend">
                {mode === "static" ? <Globe /> : <AppWindow />} FrontendSpec
              </TabsTrigger>
            )}
            {tabs.includes("json") && (
              <TabsTrigger value="json">
                <Braces /> {mode === "dynamic" ? "BackendSpec" : "JSON"}
              </TabsTrigger>
            )}
          </TabsList>
          {tabs.includes("requirement") && (
            <TabsContent value="requirement" className="pt-2">
              <RequirementTab />
            </TabsContent>
          )}
          {tabs.includes("import") && (
            <TabsContent value="import" className="pt-2" keepMounted>
              <FrontendImportTab />
            </TabsContent>
          )}
          {tabs.includes("frontend") && (
            <TabsContent value="frontend" className="pt-2" keepMounted>
              <JsonTab
                kind="frontend"
                text={frontendSpecText}
                onTextChange={setFrontendSpecText}
                editor={editors.frontend}
                issues={frontend.issues}
                parsed={frontend.parsed}
                onExampleLoaded={mode === "dynamic" ? offerPair : undefined}
              />
            </TabsContent>
          )}
          {tabs.includes("json") && (
            <TabsContent value="json" className="pt-2" keepMounted>
              <JsonTab
                kind="backend"
                text={specText}
                onTextChange={setSpecText}
                editor={editors.backend}
                issues={backend.issues}
                parsed={backend.parsed}
              />
            </TabsContent>
          )}
        </Tabs>

        <aside className="lg:sticky lg:top-4 lg:self-start">
          <Stack gap="md">
            {mode !== "backend" && (
              <SpecValidationCard
                title={mode === "dynamic" ? "FrontendSpec" : "Validation"}
                validation={frontend}
                emptyText={EMPTY_TEXT.frontend}
                onSelect={(issue) => jumpTo("frontend", issue)}
              />
            )}
            {mode !== "static" && (
              <SpecValidationCard
                title={mode === "dynamic" ? "BackendSpec" : "Validation"}
                validation={backend}
                emptyText={EMPTY_TEXT.backend}
                onSelect={(issue) => jumpTo("backend", issue)}
              />
            )}
            {mode === "dynamic" && (
              <Card size="sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    Consistency
                    {pair.isChecking && <Spinner />}
                    {pair.errorCount > 0 && <Badge variant="destructive">{pair.errorCount} errors</Badge>}
                  </CardTitle>
                  <CardDescription>Does the FrontendSpec only use what the BackendSpec&apos;s API provides?</CardDescription>
                </CardHeader>
                <CardContent>
                  <ConsistencyIssueList
                    issues={pair.issues}
                    isReady={pair.isReady}
                    isChecking={pair.isChecking}
                    onSelect={jumpToPointer}
                  />
                  {pair.requestError && <p className="mt-2 text-sm text-destructive">{pair.requestError.message}</p>}
                </CardContent>
              </Card>
            )}

            {mode !== "static" && (
              <Card size="sm">
                <CardHeader>
                  <CardTitle>{summary.projectName ?? "Summary"}</CardTitle>
                  <CardDescription>What the current BackendSpec describes.</CardDescription>
                </CardHeader>
                <CardContent>
                  <SpecSummaryPanel summary={summary} />
                </CardContent>
              </Card>
            )}

            <Card size="sm">
              <form onSubmit={submit.handleSubmit} noValidate>
                <CardHeader>
                  <CardTitle>Options</CardTitle>
                  {!submit.enginesReportedByWorker && (
                    <CardDescription>The worker is not reporting; engine availability may be stale.</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="py-4">
                  <GenerationOptionsForm form={submit.form} engines={submit.engines} mode={mode} />
                </CardContent>
                <CardFooter>
                  <Button type="submit" className="w-full" disabled={!canSubmit || submit.isSubmitting}>
                    {submit.isSubmitting ? <Spinner /> : <Rocket />}
                    {SUBMIT_LABELS[mode]}
                  </Button>
                </CardFooter>
              </form>
            </Card>
          </Stack>
        </aside>
      </div>
    </Stack>
  );
}
