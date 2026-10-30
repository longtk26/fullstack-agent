"use client";

import { useState, type DragEvent } from "react";
import { ImagePlus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Stack } from "@/components/layout/Stack";
import { uploadContentUrl, type TUpload } from "../api/uploads-api";
import { useUploads } from "../hooks/use-uploads";
import { addUploadAsset, setAssetSource, specAssets } from "../lib/spec-assets";

const ACCEPT = "image/png,image/jpeg,image/webp,image/svg+xml";
const NEW_ASSET = "__new__";

type AssetsPanelProps = {
  specText: string;
  onApply: (text: string) => void;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function sourceLabel(source: string | undefined): string {
  if (!source || source === "placeholder") return "placeholder";
  if (source === "generate") return "drawn";
  if (source.startsWith("upload:")) return "upload";
  if (source.startsWith("lucide:")) return "icon";
  return "link";
}

function UploadRow({
  upload,
  targets,
  onUse,
  onDelete,
}: {
  upload: TUpload;
  targets: string[];
  onUse: (target: string) => void;
  onDelete: () => void;
}) {
  return (
    <li className="flex items-center gap-3">
      {/* eslint-disable-next-line @next/next/no-img-element -- a user's upload through the API proxy */}
      <img
        src={uploadContentUrl(upload.uploadId)}
        alt={upload.filename}
        className="size-12 shrink-0 rounded-md border bg-muted object-contain"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="truncate text-xs font-medium">{upload.filename}</span>
        <span className="text-xs text-muted-foreground">
          {upload.width && upload.height ? `${upload.width}×${upload.height} · ` : ""}
          {formatSize(upload.bytes)}
        </span>
      </div>
      <Select onValueChange={(value) => value && onUse(String(value))}>
        <SelectTrigger size="sm" className="w-32" aria-label={`Use ${upload.filename} for`}>
          <SelectValue placeholder="Use for…" />
        </SelectTrigger>
        <SelectContent>
          {targets.map((id) => (
            <SelectItem key={id} value={id}>
              {id}
            </SelectItem>
          ))}
          <SelectItem value={NEW_ASSET}>New asset</SelectItem>
        </SelectContent>
      </Select>
      <Button size="icon-sm" variant="ghost" aria-label={`Delete ${upload.filename}`} onClick={onDelete}>
        <Trash2 />
      </Button>
    </li>
  );
}

/**
 * The FrontendSpec's images and the user's uploads (Story 15.4): drop or pick PNG, JPEG, WebP or SVG files, then use
 * one for an existing asset (`source: "upload:<id>"`) or as a new asset. Changes go into the editor text.
 */
export function AssetsPanel({ specText, onApply }: AssetsPanelProps) {
  const { list, upload, remove } = useUploads();
  const [dragging, setDragging] = useState(false);
  const assets = specAssets(specText);
  const uploads = list.data?.uploads ?? [];

  const send = (files: FileList | null) => {
    for (const file of Array.from(files ?? [])) upload.mutate(file);
  };
  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    send(event.dataTransfer.files);
  };
  const use = (item: TUpload, target: string) => {
    const next =
      target === NEW_ASSET
        ? addUploadAsset(specText, item.source, item.filename)
        : setAssetSource(specText, target, item.source);
    if (next) onApply(next);
  };

  return (
    <Stack gap="sm">
      {assets.length > 0 && (
        <ul className="flex flex-col gap-1">
          {assets.map((asset) => (
            <li key={asset.id} className="flex items-center gap-2 text-xs">
              <span className="font-mono">{asset.id}</span>
              <Badge variant="outline">{sourceLabel(asset.source)}</Badge>
              <span className="truncate text-muted-foreground">{asset.alt}</span>
            </li>
          ))}
        </ul>
      )}
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        data-dragging={dragging || undefined}
        className="flex cursor-pointer flex-col items-center gap-1 rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground data-[dragging]:border-primary data-[dragging]:bg-muted"
      >
        <ImagePlus className="size-5" aria-hidden />
        Drop images here or choose files (PNG, JPEG, WebP, SVG)
        <input
          type="file"
          accept={ACCEPT}
          multiple
          className="sr-only"
          onChange={(event) => {
            send(event.target.files);
            event.target.value = "";
          }}
        />
      </label>
      {upload.isPending && <p className="text-xs text-muted-foreground">Uploading…</p>}
      {upload.error && <p className="text-xs text-destructive">{upload.error.message}</p>}
      {uploads.length > 0 && (
        <ul className="flex flex-col gap-2">
          {uploads.map((item) => (
            <UploadRow
              key={item.uploadId}
              upload={item}
              targets={assets.map((asset) => asset.id)}
              onUse={(target) => use(item, target)}
              onDelete={() => remove.mutate(item.uploadId)}
            />
          ))}
        </ul>
      )}
      {list.data && (
        <p className="text-xs text-muted-foreground">
          {formatSize(list.data.usedBytes)} of {formatSize(list.data.quotaBytes)} used. A new asset still needs
          `asset:&lt;id&gt;` in a section to show.
        </p>
      )}
    </Stack>
  );
}
