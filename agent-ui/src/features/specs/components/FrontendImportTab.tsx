"use client";

import { useState } from "react";
import { FileUp, Sparkles } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Stack } from "@/components/layout/Stack";
import { cn } from "@/lib/utils";
import { useFrontendImportTab } from "../hooks/use-frontend-import-tab";
import { ImportResult } from "./ImportResult";

export function FrontendImportTab() {
  const tab = useFrontendImportTab();
  const [isDragging, setIsDragging] = useState(false);

  return (
    <Stack gap="md">
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
        className={cn(
          "flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-8 text-center transition-colors",
          isDragging && "border-primary bg-muted",
        )}
      >
        <FileUp className="size-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Drop a Frontend-Agent site JSON here. It is converted into an example BackendSpec with seed data.
        </p>
        <Stack direction="row" gap="xs" wrap justify="center">
          <Button variant="outline" size="sm" onClick={tab.upload}>
            Upload site JSON
          </Button>
          <Button variant="outline" size="sm" onClick={tab.loadSample} disabled={!tab.hasSample}>
            <Sparkles /> Load sample
          </Button>
        </Stack>
        {tab.sourceName && <span className="font-mono text-xs text-muted-foreground">{tab.sourceName}</span>}
      </div>

      <Label className="flex items-center gap-2 font-normal">
        <Switch checked={tab.includeAdminCrud} onCheckedChange={tab.toggleAdminCrud} />
        Include admin CRUD (create / update / delete for every entity)
      </Label>

      {tab.conversion.isPending && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Converting…
        </p>
      )}
      {tab.conversion.isError && (
        <Alert variant="destructive">
          <AlertTitle>Import failed</AlertTitle>
          <AlertDescription>{tab.conversion.error.message}</AlertDescription>
        </Alert>
      )}
      {tab.result && !tab.conversion.isPending && (
        <ImportResult
          result={tab.result}
          needsAcknowledgement={tab.needsAcknowledgement}
          acknowledged={tab.acknowledged}
          onAcknowledge={tab.setAcknowledged}
          onEdit={tab.editInJsonTab}
        />
      )}
    </Stack>
  );
}
