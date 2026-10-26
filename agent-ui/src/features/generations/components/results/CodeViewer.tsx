"use client";

import Editor, { loader } from "@monaco-editor/react";
import { useTheme } from "next-themes";
import { Skeleton } from "@/components/ui/skeleton";

loader.config({ paths: { vs: "/monaco/vs" } });

const LANGUAGES: Record<string, string> = {
  py: "python",
  md: "markdown",
  json: "json",
  yml: "yaml",
  yaml: "yaml",
  toml: "ini",
  ini: "ini",
  sh: "shell",
  txt: "plaintext",
  mako: "plaintext",
};

function languageFor(path: string): string {
  const name = path.split("/").pop() ?? "";
  if (name === "Dockerfile") return "dockerfile";
  if (name === "Makefile") return "plaintext";
  return LANGUAGES[name.split(".").pop() ?? ""] ?? "plaintext";
}

type CodeViewerProps = {
  path: string;
  content: string;
  height?: number | string;
};

export function CodeViewer({ path, content, height = 560 }: CodeViewerProps) {
  const { resolvedTheme } = useTheme();
  return (
    <Editor
      path={`source://${path}`}
      language={languageFor(path)}
      value={content}
      height={height}
      theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
      loading={<Skeleton className="h-full w-full" />}
      options={{
        readOnly: true,
        domReadOnly: true,
        minimap: { enabled: false },
        fontSize: 13,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        renderLineHighlight: "none",
      }}
    />
  );
}
