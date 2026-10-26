"use client";

import { ChevronRight, File, Folder, FolderOpen } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useSourceBrowser } from "../../hooks/use-source-browser";
import type { TFileEntry } from "../../types";
import { CodeViewer } from "./CodeViewer";

type SourceBrowserProps = {
  generationId: string;
};

export function SourceBrowser({ generationId }: SourceBrowserProps) {
  const browser = useSourceBrowser(generationId, true);
  const file = browser.file.data;

  if (browser.rootError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{browser.rootError.message}</AlertDescription>
      </Alert>
    );
  }
  return (
    <div className="grid overflow-hidden rounded-lg border md:grid-cols-[260px_minmax(0,1fr)]">
      <nav aria-label="Generated files" className="max-h-[600px] overflow-auto border-b p-2 md:border-r md:border-b-0">
        {browser.loadingRoot ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <TreeLevel path="" depth={0} browser={browser} />
        )}
      </nav>
      <div className="min-w-0">
        <div className="border-b px-3 py-2 font-mono text-xs text-muted-foreground">
          {browser.selected ?? "Select a file"}
        </div>
        {browser.file.isError ? (
          <p className="p-4 text-sm text-muted-foreground">{browser.file.error.message}</p>
        ) : file?.type === "file" ? (
          <CodeViewer path={file.path} content={file.content} />
        ) : (
          <Skeleton className="m-3 h-[540px]" />
        )}
      </div>
    </div>
  );
}

type TreeLevelProps = {
  path: string;
  depth: number;
  browser: ReturnType<typeof useSourceBrowser>;
};

function TreeLevel({ path, depth, browser }: TreeLevelProps) {
  const entries = browser.children.get(path);
  if (!entries) return <Skeleton className="my-1 h-5" style={{ marginLeft: depth * 12 }} />;
  return (
    <ul className="flex flex-col">
      {entries.map((entry) => (
        <TreeEntry key={entry.path} entry={entry} depth={depth} browser={browser} />
      ))}
    </ul>
  );
}

function TreeEntry({ entry, depth, browser }: { entry: TFileEntry; depth: number; browser: TreeLevelProps["browser"] }) {
  const isDir = entry.type === "dir";
  const open = isDir && browser.expanded.has(entry.path);
  const Icon = isDir ? (open ? FolderOpen : Folder) : File;
  return (
    <li>
      <button
        type="button"
        onClick={() => (isDir ? browser.toggle(entry.path) : browser.select(entry.path))}
        className={cn(
          "flex w-full items-center gap-1.5 rounded-md px-1.5 py-1 text-left text-xs hover:bg-muted",
          browser.selected === entry.path && "bg-muted font-medium",
        )}
        style={{ paddingLeft: depth * 12 + 6 }}
      >
        {isDir ? (
          <ChevronRight className={cn("size-3 shrink-0 transition-transform", open && "rotate-90")} />
        ) : (
          <span className="size-3 shrink-0" />
        )}
        <Icon className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="truncate">{entry.name}</span>
      </button>
      {open && <TreeLevel path={entry.path} depth={depth + 1} browser={browser} />}
    </li>
  );
}
