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
import { fetchExampleText } from "../api/specs-api";
import type { TEditorHandle } from "../hooks/use-json-editor";
import { useExampleIndex, useSpecSchema } from "../hooks/use-spec-queries";
import type { TEditorIssue } from "../hooks/use-spec-validation";
import { SPEC_KINDS } from "../lib/spec-kinds";
import type { TSpecKind } from "../types";
import { JsonEditor } from "./JsonEditor";

type JsonTabProps = {
  kind: TSpecKind;
  text: string;
  onTextChange: (text: string) => void;
  editor: TEditorHandle;
  issues: TEditorIssue[];
  parsed: unknown;
  /** Called after an example was loaded, with its name (file name without `.json`). */
  onExampleLoaded?: (name: string) => void;
};

/** Monaco editor bound to the BackendSpec or FrontendSpec JSON Schema, with its toolbar. */
export function JsonTab({ kind, text, onTextChange, editor, issues, parsed, onExampleLoaded }: JsonTabProps) {
  const { fileName, exampleKey } = SPEC_KINDS[kind];
  const { data: schema } = useSpecSchema(kind);
  const { data: examples } = useExampleIndex();
  const exampleFiles = examples?.[exampleKey] ?? [];

  const loadExample = async (name: string, path: string) => {
    try {
      onTextChange(await fetchExampleText(path));
      onExampleLoaded?.(name);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not load the example");
    }
  };

  const upload = async () => {
    const file = await pickFile("application/json,.json");
    if (file) onTextChange(await file.text());
  };

  return (
    <Stack gap="sm">
      <Stack direction="row" gap="xs" wrap>
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
            <FileJson /> Load example <ChevronDown />
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {exampleFiles.map((example) => (
              <DropdownMenuItem key={example.path} onClick={() => loadExample(example.name, example.path)}>
                {example.name}
              </DropdownMenuItem>
            ))}
            {!exampleFiles.length && <DropdownMenuItem disabled>No examples found</DropdownMenuItem>}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant="outline" size="sm" onClick={upload}>
          <Upload /> Upload .json
        </Button>
        <Button variant="outline" size="sm" disabled={parsed === undefined} onClick={() => onTextChange(prettyJson(parsed))}>
          <WandSparkles /> Format
        </Button>
        <Button variant="outline" size="sm" disabled={!text.trim()} onClick={() => downloadText(fileName, text)}>
          <Download /> Download
        </Button>
        <Button variant="ghost" size="sm" disabled={!text} onClick={() => onTextChange("")}>
          <Eraser /> Clear
        </Button>
      </Stack>
      <div className="overflow-hidden rounded-lg border">
        <JsonEditor
          path={fileName}
          value={text}
          onChange={onTextChange}
          issues={issues}
          schema={schema}
          onMount={editor.onMount}
        />
      </div>
    </Stack>
  );
}
