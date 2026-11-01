"use client";

import { useCallback, useEffect, useMemo } from "react";
import { useWatch } from "react-hook-form";
import { AppWindow, Braces, FileCode, FileInput, Globe, MessageSquareText, Rocket } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Stack } from "@/components/layout/Stack";
import { AssetsPanel } from "@/features/specs/components/AssetsPanel";
import { ConsistencyIssueList } from "@/features/specs/components/ConsistencyIssueList";
import { DesignPanel } from "@/features/specs/components/DesignPanel";
import { FrontendImportTab } from "@/features/specs/components/FrontendImportTab";
import { FrontendSpecSummaryPanel } from "@/features/specs/components/FrontendSpecSummaryPanel";
import { JsonEditor } from "@/features/specs/components/JsonEditor";
import { JsonTab } from "@/features/specs/components/JsonTab";
import { RequirementTab } from "@/features/specs/components/RequirementTab";
import { SpecSummaryPanel } from "@/features/specs/components/SpecSummaryPanel";
import { useExamplePairOffer } from "@/features/specs/hooks/use-example-pair-offer";
import { useJsonEditor } from "@/features/specs/hooks/use-json-editor";
import { useSpecPairCheck } from "@/features/specs/hooks/use-spec-pair-check";
import { useSpecDraft } from "@/features/specs/hooks/use-spec-queries";
import { useSpecValidation } from "@/features/specs/hooks/use-spec-validation";
import type { TEditorIssue } from "@/features/specs/hooks/use-spec-validation";
import { summarizeFrontendSpec } from "@/features/specs/lib/frontend-spec-summary";
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
  static: ["requirement", "frontend"],
  dynamic: ["requirement", "frontend", "json", "contract"],
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
  const appliedDraft = useSpecDraftStore((state) => state.appliedDraft);

  const editors = { backend: useJsonEditor(), frontend: useJsonEditor() };
  const backend = useSpecValidation("backend", specText);
  const frontend = useSpecValidation("frontend", frontendSpecText, mode === "backend" ? undefined : mode);
  const pair = useSpecPairCheck(
    mode === "dynamic",
    { ...frontend, text: frontendSpecText },
    { ...backend, text: specText },
  );
  const summary = useMemo(() => summarizeSpec(backend.parsed), [backend.parsed]);
  const frontendSummary = useMemo(() => summarizeFrontendSpec(frontend.parsed), [frontend.parsed]);
  const offerPair = useExamplePairOffer(setSpecText);
  // The design directions of the draft the editors were filled from (Story 12.6), static and dynamic only.
  const appliedDraftQuery = useSpecDraft(mode !== "backend" && appliedDraft?.mode === mode ? appliedDraft.id : null);
  const design = appliedDraftQuery.data?.design ?? null;

  const hasManagePages = useMemo(
    () => frontendSummary.pages.some((p) => p.route.startsWith("/manage") || p.id.startsWith("manage-")),
    [frontendSummary.pages],
  );

  const handleDropManageArea = useCallback(() => {
    try {
      const parsed = JSON.parse(frontendSpecText);
      if (typeof parsed !== "object" || parsed === null) return;
      const pages = Array.isArray(parsed.pages)
        ? parsed.pages.filter(
            (p: { id?: string; route?: string }) =>
              !p.route?.startsWith("/manage") && !p.id?.startsWith("manage-"),
          )
        : parsed.pages;
      const forms = Array.isArray(parsed.forms)
        ? parsed.forms.filter(
            (f: { id?: string }) =>
              !f.id?.startsWith("manage-") && !f.id?.startsWith("manage_"),
          )
        : parsed.forms;
      const content = Array.isArray(parsed.content)
        ? parsed.content.filter((c: { collection?: string }) => c.collection !== "manageEntities")
        : parsed.content;
      let layout = parsed.layout;
      if (layout?.header?.navigation && Array.isArray(layout.header.navigation)) {
        layout = {
          ...layout,
          header: {
            ...layout.header,
            navigation: layout.header.navigation.filter(
              (n: { page?: string; href?: string }) =>
                n.page !== "manage-index" &&
                !n.page?.startsWith("manage-") &&
                !n.href?.startsWith("/manage"),
            ),
          },
        };
      }
      const updated = { ...parsed, pages, forms, content, layout };
      setFrontendSpecText(JSON.stringify(updated, null, 2));
    } catch {
      // ignore
    }
  }, [frontendSpecText, setFrontendSpecText]);

  const canSubmit = {
    backend: backend.isSubmittable,
    static: frontend.isSubmittable,
    dynamic: frontend.isSubmittable && backend.isSubmittable && pair.isSubmittable,
  }[mode];
  const submit = useNewGeneration({
    mode,
    backendSpec: backend.parsed,
    frontendSpec: frontend.parsed,
    // The requirement draft the editors were filled from, so the generation keeps its requirement (2.4, 12.4).
    draftId: appliedDraft?.mode === mode ? appliedDraft.id : null,
    canSubmit,
    onCreated: clearDraft,
  });
  const engine = useWatch({ control: submit.form.control, name: "engine" });

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
            {tabs.includes("contract") && (
              <TabsTrigger value="contract">
                <FileCode /> Contract
              </TabsTrigger>
            )}
          </TabsList>
          {tabs.includes("requirement") && (
            <TabsContent value="requirement" className="pt-2" keepMounted>
              <RequirementTab
                mode={mode}
                engine={engine ?? null}
                onGenerateDirect={submit.generateFromRequirement}
                isGenerating={submit.isSubmitting}
              />
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
          {tabs.includes("contract") && (
            <TabsContent value="contract" className="pt-2">
              {pair.contract ? (
                <Stack gap="xs">
                  <p className="text-sm text-muted-foreground">
                    The API contract (OpenAPI 3.1) both lanes are generated from. Read-only: change the BackendSpec.
                  </p>
                  <JsonEditor path="contract.json" value={JSON.stringify(pair.contract, null, 2)} readOnly />
                </Stack>
              ) : (
                <p className="text-sm text-muted-foreground">
                  The contract appears once the FrontendSpec and BackendSpec are both valid.
                </p>
              )}
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

            {mode !== "backend" && design && design.directions.length > 0 && (
              <Card size="sm">
                <CardHeader>
                  <CardTitle>Design</CardTitle>
                  <CardDescription>
                    Directions for this draft: colours, fonts and the home page&apos;s order, from design data.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DesignPanel design={design} specText={frontendSpecText} onApply={setFrontendSpecText} />
                </CardContent>
              </Card>
            )}

            {mode !== "backend" && (
              <Card size="sm">
                <CardHeader>
                  <CardTitle>Images</CardTitle>
                  <CardDescription>Your logo and photos for the site; drawn images come from the spec.</CardDescription>
                </CardHeader>
                <CardContent>
                  <AssetsPanel specText={frontendSpecText} onApply={setFrontendSpecText} />
                </CardContent>
              </Card>
            )}

            {mode !== "backend" && (
              <Card size="sm">
                <CardHeader>
                  <CardTitle>{frontendSummary.projectName ?? "Site"}</CardTitle>
                  <CardDescription>What the current FrontendSpec builds.</CardDescription>
                </CardHeader>
                <CardContent>
                  <FrontendSpecSummaryPanel
                    summary={frontendSummary}
                    showOperations={mode === "dynamic"}
                    onDropManageArea={hasManagePages ? handleDropManageArea : undefined}
                    issues={frontend.issues}
                  />
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
