"use client";

import { useState } from "react";
import { FileText, FileUp, Sparkles, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { Stack } from "@/components/layout/Stack";
import type { TGenerationMode } from "@/features/generations/types";
import { useNow } from "@/hooks/use-now";
import { cn } from "@/lib/utils";
import { useRequirementTab } from "../hooks/use-requirement-tab";
import { REQUIREMENT_MAX_BYTES, REQUIREMENT_MIN_CHARS } from "../lib/requirement-file";
import { DraftResult } from "./DraftResult";

const COPY: Record<TGenerationMode, { intro: string; placeholder: string; action: string }> = {
  backend: {
    intro: "Describe the backend: the data it keeps and what clients do with it. The draft is a BackendSpec.",
    placeholder: "A task tracker: projects have many tasks; tasks have a title, status (todo, doing, done) and due date.",
    action: "Draft BackendSpec",
  },
  static: {
    intro: "Describe the site: its pages, what each one shows, and any brand colours or fonts. The draft is a FrontendSpec.",
    placeholder: "A website for a design studio: home with our services and quotes, a work page, about and contact.",
    action: "Draft FrontendSpec",
  },
  dynamic: {
    intro: "Describe the app: its pages, the data behind them and the forms. The draft is a FrontendSpec and its BackendSpec.",
    placeholder: "A small shop: product catalogue, product detail with an add-to-cart form, a cart and a contact page.",
    action: "Draft both specs",
  },
};

const PROGRESS: Record<string, string> = {
  PENDING: "Waiting for a worker…",
  drafting: "Drafting…",
  validating: "Validating…",
};

type RequirementTabProps = {
  mode: TGenerationMode;
  engine: string | null;
};

export function RequirementTab({ mode, engine }: RequirementTabProps) {
  const tab = useRequirementTab({ mode, engine });
  const [isDragging, setIsDragging] = useState(false);
  const now = useNow(tab.isRunning);
  const copy = COPY[mode];
  const draft = tab.draft;
  const startedAt = draft?.startedAt ?? draft?.createdAt;
  const elapsed = startedAt ? Math.max(0, Math.round((now - Date.parse(startedAt)) / 1000)) : 0;
  const progress = draft ? PROGRESS[draft.progress ?? draft.status] ?? `${draft.progress ?? draft.status}…` : "Starting…";

  return (
    <Stack gap="md">
      <p className="text-sm text-muted-foreground">{copy.intro}</p>

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          tab.loadFile(event.dataTransfer.files[0] ?? null);
        }}
        className={cn("rounded-lg transition-colors", isDragging && "ring-2 ring-primary")}
      >
        <Textarea
          rows={14}
          value={tab.text}
          onChange={(event) => tab.setText(event.target.value)}
          placeholder={`${copy.placeholder}\n\nType here, or drop a .md / .txt file.`}
          className="font-mono text-xs"
          aria-label="Requirement"
        />
      </div>

      <Stack direction="row" justify="between" align="center" wrap className="gap-y-2">
        <Stack direction="row" gap="xs" wrap align="center">
          <Button variant="outline" size="sm" onClick={tab.upload}>
            <FileUp /> Upload .md / .txt
          </Button>
          {tab.examples.map((example) => (
            <Button key={example.path} variant="outline" size="sm" onClick={() => tab.loadExample(example)}>
              <Sparkles /> {example.name}
            </Button>
          ))}
        </Stack>
        <span className={cn("text-xs text-muted-foreground", tab.tooLarge && "text-destructive")}>
          {(tab.bytes / 1024).toFixed(1)} / {REQUIREMENT_MAX_BYTES / 1024} KB
        </span>
      </Stack>

      {tab.fileName && (
        <span className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
          <FileText className="size-3.5" /> {tab.fileName}
          <Button variant="ghost" size="icon-xs" onClick={tab.clearFile} aria-label="Forget the file name">
            <X />
          </Button>
        </span>
      )}

      <Stack direction="row" gap="sm" align="center" wrap>
        <Button onClick={tab.startDraft} disabled={!tab.canDraft}>
          {tab.isStarting || tab.isRunning ? <Spinner /> : <Sparkles />} {copy.action}
        </Button>
        {tab.tooShort && tab.text.length > 0 && (
          <span className="text-xs text-muted-foreground">At least {REQUIREMENT_MIN_CHARS} characters.</span>
        )}
        {engine && <span className="text-xs text-muted-foreground">Engine: {engine} (from Options)</span>}
      </Stack>

      {tab.isRunning && (
        <Card size="sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Spinner /> {progress}
            </CardTitle>
            <CardDescription>
              {elapsed} s · the draft runs on the worker; you can leave this page and come back.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
      {tab.draftError && (
        <Alert variant="destructive">
          <AlertTitle>Could not load the draft</AlertTitle>
          <AlertDescription>
            {tab.draftError.message}{" "}
            <Button size="sm" variant="link" onClick={tab.discardDraft}>
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}
      {draft && tab.isFinished && draft.mode !== mode && (
        <Alert>
          <AlertTitle>The last draft is for {draft.mode} mode</AlertTitle>
          <AlertDescription>Switch back to that mode to open it, or draft again for this one.</AlertDescription>
        </Alert>
      )}
      {draft && tab.isFinished && draft.mode === mode && (
        <DraftResult
          draft={draft}
          needsAcknowledgement={tab.needsAcknowledgement}
          acknowledged={tab.acknowledged}
          onAcknowledge={tab.setAcknowledged}
          onOpen={tab.openInEditor}
          onDiscard={tab.discardDraft}
        />
      )}
    </Stack>
  );
}
