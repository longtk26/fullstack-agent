"use client";

import { useCallback, useRef } from "react";
import type { RefObject } from "react";
import type { Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { pointerToRange } from "../lib/json-pointer";
import type { TEditorIssue } from "./use-spec-validation";

export type TEditorHandle = {
  onMount: (instance: editor.IStandaloneCodeEditor, monaco: Monaco) => void;
  jumpTo: (issue: TEditorIssue) => void;
  editorRef: RefObject<editor.IStandaloneCodeEditor | null>;
  monacoRef: RefObject<Monaco | null>;
};

export function issueRange(model: editor.ITextModel, issue: TEditorIssue) {
  const text = model.getValue();
  const range =
    issue.offset !== undefined ? { offset: issue.offset, length: 1 } : pointerToRange(text, issue.path);
  if (!range) return null;
  const start = model.getPositionAt(range.offset);
  const end = model.getPositionAt(Math.min(text.length, range.offset + Math.max(range.length, 1)));
  return { startLineNumber: start.lineNumber, startColumn: start.column, endLineNumber: end.lineNumber, endColumn: end.column };
}

/** Holds the Monaco instance so sibling components (the issue list) can move the cursor. */
export function useJsonEditor(): TEditorHandle {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);

  const onMount = useCallback((instance: editor.IStandaloneCodeEditor, monaco: Monaco) => {
    editorRef.current = instance;
    monacoRef.current = monaco;
  }, []);

  const jumpTo = useCallback((issue: TEditorIssue) => {
    const instance = editorRef.current;
    const model = instance?.getModel();
    if (!instance || !model) return;
    const range = issueRange(model, issue);
    if (!range) return;
    instance.revealRangeInCenter(range);
    instance.setSelection(range);
    instance.focus();
  }, []);

  return { onMount, jumpTo, editorRef, monacoRef };
}
