"use client";

import { useEffect, useMemo } from "react";
import { Braces, FileInput, MessageSquareText, Rocket } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Stack } from "@/components/layout/Stack";
import { FrontendImportTab } from "@/features/specs/components/FrontendImportTab";
import { IssueList } from "@/features/specs/components/IssueList";
import { JsonTab } from "@/features/specs/components/JsonTab";
import { RequirementTab } from "@/features/specs/components/RequirementTab";
import { SpecSummaryPanel } from "@/features/specs/components/SpecSummaryPanel";
import { useJsonEditor } from "@/features/specs/hooks/use-json-editor";
import { useSpecValidation } from "@/features/specs/hooks/use-spec-validation";
import { summarizeSpec } from "@/features/specs/lib/spec-summary";
import type { TSpecTab } from "@/features/specs/types";
import { useSpecDraftStore } from "@/store/spec-draft-store";
import { useNewGeneration } from "../hooks/use-new-generation";
import { GenerationOptionsForm } from "./GenerationOptionsForm";

export function NewGenerationView() {
  const specText = useSpecDraftStore((state) => state.specText);
  const activeTab = useSpecDraftStore((state) => state.activeTab);
  const setActiveTab = useSpecDraftStore((state) => state.setActiveTab);
  const clearDraft = useSpecDraftStore((state) => state.clearDraft);
  const editor = useJsonEditor();
  const validation = useSpecValidation(specText);
  const summary = useMemo(() => summarizeSpec(validation.parsed), [validation.parsed]);
  const submit = useNewGeneration(validation.parsed, validation.isSubmittable, clearDraft);

  useEffect(() => {
    useSpecDraftStore.persist.rehydrate();
  }, []);

  const selectIssue: typeof editor.jumpTo = (issue) => {
    setActiveTab("json");
    requestAnimationFrame(() => editor.jumpTo(issue));
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as TSpecTab)}>
        <TabsList>
          <TabsTrigger value="requirement">
            <MessageSquareText /> Requirement
          </TabsTrigger>
          <TabsTrigger value="import">
            <FileInput /> Import frontend JSON
          </TabsTrigger>
          <TabsTrigger value="json">
            <Braces /> JSON
          </TabsTrigger>
        </TabsList>
        <TabsContent value="requirement" className="pt-2">
          <RequirementTab />
        </TabsContent>
        <TabsContent value="import" className="pt-2" keepMounted>
          <FrontendImportTab />
        </TabsContent>
        <TabsContent value="json" className="pt-2" keepMounted>
          <JsonTab editor={editor} issues={validation.issues} parsed={validation.parsed} />
        </TabsContent>
      </Tabs>

      <aside className="lg:sticky lg:top-4 lg:self-start">
        <Stack gap="md">
          <Card size="sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Validation
                {validation.isChecking && <Spinner />}
                {validation.errorCount > 0 && <Badge variant="destructive">{validation.errorCount} errors</Badge>}
                {validation.warningCount > 0 && <Badge variant="outline">{validation.warningCount} warnings</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <IssueList
                issues={validation.issues}
                isChecking={validation.isChecking}
                isEmpty={validation.isEmpty}
                onSelect={selectIssue}
              />
              {validation.requestError && (
                <p className="mt-2 text-sm text-destructive">{validation.requestError.message}</p>
              )}
            </CardContent>
          </Card>

          <Card size="sm">
            <CardHeader>
              <CardTitle>{summary.projectName ?? "Summary"}</CardTitle>
              <CardDescription>What the current JSON describes.</CardDescription>
            </CardHeader>
            <CardContent>
              <SpecSummaryPanel summary={summary} />
            </CardContent>
          </Card>

          <Card size="sm">
            <form onSubmit={submit.handleSubmit} noValidate>
              <CardHeader>
                <CardTitle>Options</CardTitle>
                {!submit.enginesReportedByWorker && (
                  <CardDescription>The worker is not reporting; engine availability may be stale.</CardDescription>
                )}
              </CardHeader>
              <CardContent className="py-4">
                <GenerationOptionsForm form={submit.form} engines={submit.engines} />
              </CardContent>
              <CardFooter>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={!validation.isSubmittable || submit.isSubmitting}
                >
                  {submit.isSubmitting ? <Spinner /> : <Rocket />}
                  Generate backend
                </Button>
              </CardFooter>
            </form>
          </Card>
        </Stack>
      </aside>
    </div>
  );
}
