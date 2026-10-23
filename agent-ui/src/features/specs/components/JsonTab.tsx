"use client";

import { ChevronDown, Download, Eraser, FileJson, Upload, WandSparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Stack } from "@/components/layout/Stack";
import { downloadText, pickFile, prettyJson } from "@/lib/files";
import { useSpecDraftStore } from "@/store/spec-draft-store";
import { fetchExampleText } from "../api/specs-api";
import type { TEditorHandle } from "../hooks/use-json-editor";
import { useExampleIndex, useSpecSchema } from "../hooks/use-spec-queries";
import type { TEditorIssue } from "../hooks/use-spec-validation";
import { JsonEditor } from "./JsonEditor";

type JsonTabProps = {
  editor: TEditorHandle;
  issues: TEditorIssue[];
  parsed: unknown;
};

export function JsonTab({ editor, issues, parsed }: JsonTabProps) {
  const specText = useSpecDraftStore((state) => state.specText);
  const setSpecText = useSpecDraftStore((state) => state.setSpecText);
  const { data: schema } = useSpecSchema();
  const { data: examples } = useExampleIndex();

  const loadExample = async (path: string) => {
    try {
      setSpecText(await fetchExampleText(path));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not load the example");
    }
  };

  const upload = async () => {
    const file = await pickFile("application/json,.json");
    if (file) setSpecText(await file.text());
  };

  return (
    <Stack gap="sm">
      <Stack direction="row" gap="xs" wrap>
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
            <FileJson /> Load example <ChevronDown />
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {(examples?.specs ?? []).map((example) => (
              <DropdownMenuItem key={example.path} onClick={() => loadExample(example.path)}>
                {example.name}
              </DropdownMenuItem>
            ))}
            {!examples?.specs?.length && <DropdownMenuItem disabled>No examples found</DropdownMenuItem>}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant="outline" size="sm" onClick={upload}>
          <Upload /> Upload .json
        </Button>
        <Button variant="outline" size="sm" disabled={parsed === undefined} onClick={() => setSpecText(prettyJson(parsed))}>
          <WandSparkles /> Format
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!specText.trim()}
          onClick={() => downloadText("backend-spec.json", specText)}
        >
          <Download /> Download
        </Button>
        <Button variant="ghost" size="sm" disabled={!specText} onClick={() => setSpecText("")}>
          <Eraser /> Clear
        </Button>
      </Stack>
      <div className="overflow-hidden rounded-lg border">
        <JsonEditor
          path="backend-spec.json"
          value={specText}
          onChange={setSpecText}
          issues={issues}
          schema={schema}
          onMount={editor.onMount}
        />
      </div>
    </Stack>
  );
}
