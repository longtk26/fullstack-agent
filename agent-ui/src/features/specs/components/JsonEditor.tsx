"use client";

import { useEffect, useRef, useState } from "react";
import Editor, { loader } from "@monaco-editor/react";
import type { Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { useTheme } from "next-themes";
import { Skeleton } from "@/components/ui/skeleton";
import { issueRange } from "../hooks/use-json-editor";
import type { TEditorIssue } from "../hooks/use-spec-validation";

loader.config({ paths: { vs: "/monaco/vs" } });

const MARKER_OWNER = "bga-spec";
const SCHEMA_URI = "bga://schemas/backend-spec.json";

type TJsonDefaults = {
  setDiagnosticsOptions: (options: {
    validate: boolean;
    enableSchemaRequest: boolean;
    schemas: { uri: string; fileMatch: string[]; schema: unknown }[];
  }) => void;
};

/** The AMD build exposes JSON language defaults as `monaco.json`; older typings only know `languages.json`. */
function jsonDefaults(monaco: Monaco): TJsonDefaults | undefined {
  const withJson = monaco as Monaco & { json?: { jsonDefaults?: TJsonDefaults } };
  const legacy = monaco.languages as unknown as { json?: { jsonDefaults?: TJsonDefaults } };
  return withJson.json?.jsonDefaults ?? legacy.json?.jsonDefaults;
}

type JsonEditorProps = {
  path: string;
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  height?: number | string;
  issues?: TEditorIssue[];
  schema?: unknown;
  onMount?: (instance: editor.IStandaloneCodeEditor, monaco: Monaco) => void;
};

export function JsonEditor({ path, value, onChange, readOnly, height = 520, issues, schema, onMount }: JsonEditorProps) {
  const { resolvedTheme } = useTheme();
  const [instance, setInstance] = useState<{ editor: editor.IStandaloneCodeEditor; monaco: Monaco } | null>(null);
  const emitted = useRef(value);

  useEffect(() => {
    if (!instance || !schema) return;
    const modelUri = instance.editor.getModel()?.uri.toString();
    jsonDefaults(instance.monaco)?.setDiagnosticsOptions({
      validate: true,
      enableSchemaRequest: false,
      schemas: [{ uri: SCHEMA_URI, fileMatch: modelUri ? [modelUri] : ["*"], schema }],
    });
  }, [instance, schema]);

  // Uncontrolled: typing never round-trips through React (a stale `value` would overwrite newer keystrokes).
  // Only values the editor did not emit itself (load, format, clear, import) are pushed in, as an undoable edit.
  useEffect(() => {
    const model = instance?.editor.getModel();
    if (!instance || !model || value === emitted.current) return;
    emitted.current = value;
    if (model.getValue() === value) return;
    if (readOnly) {
      model.setValue(value);
      return;
    }
    instance.editor.pushUndoStop();
    instance.editor.executeEdits("external", [{ range: model.getFullModelRange(), text: value }]);
    instance.editor.pushUndoStop();
  }, [instance, value, readOnly]);

  useEffect(() => {
    if (!instance || !issues) return;
    const model = instance.editor.getModel();
    if (!model) return;
    const markers = issues.flatMap((issue) => {
      const range = issueRange(model, issue);
      if (!range) return [];
      return [
        {
          ...range,
          message: issue.hint ? `${issue.message}\n${issue.hint}` : issue.message,
          code: issue.code,
          severity:
            issue.severity === "error" ? instance.monaco.MarkerSeverity.Error : instance.monaco.MarkerSeverity.Warning,
        },
      ];
    });
    instance.monaco.editor.setModelMarkers(model, MARKER_OWNER, markers);
  }, [instance, issues, value]);

  return (
    <Editor
      path={path}
      language="json"
      height={height}
      defaultValue={value}
      theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
      loading={<Skeleton className="h-full w-full" />}
      onChange={(next) => {
        emitted.current = next ?? "";
        onChange?.(emitted.current);
      }}
      onMount={(mounted, monaco) => {
        setInstance({ editor: mounted, monaco });
        onMount?.(mounted, monaco);
      }}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        tabSize: 2,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        formatOnPaste: true,
        fixedOverflowWidgets: true,
      }}
    />
  );
}
