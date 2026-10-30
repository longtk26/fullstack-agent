"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchArtifactJson, fetchFiles } from "../../api/generations-api";
import { generationKeys } from "../../query-keys";
import type { TArtifact, TManifestAsset } from "../../types";

type TPalette = Record<string, string>;
type TPlanTheme = { theme: { light: TPalette; dark: TPalette | null } };

type AssetGalleryProps = {
  generationId: string;
  assets: TManifestAsset[];
  planArtifact: TArtifact | undefined;
};

const MODE_LABELS: Record<TManifestAsset["render"], string> = {
  "svg-component": "drawn",
  "public-file": "upload",
  remote: "link",
  icon: "icon",
  placeholder: "placeholder",
};

/**
 * A drawing as an image with the site's theme filled in: generated SVGs only reference `var(--primary)` and friends,
 * so the gallery defines them for the light and the dark palette. Rendered through `<img>`, where an SVG can run no
 * script and load nothing.
 */
function themedSvgUrl(svg: string, palette: TPalette): string {
  const variables = Object.entries(palette)
    .map(([name, value]) => `--${name}:${value};`)
    .join("");
  const themed = svg.replace(/<svg\b[^>]*>/, (open) => `${open}<style>:root{${variables}}</style>`);
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(themed)}`;
}

function formatBytes(size: number): string {
  return size < 1024 ? `${size} B` : `${(size / 1024).toFixed(1)} KB`;
}

/** The site's images (Story 15.2): each drawing on the light and dark theme, then the other assets by source. */
export function AssetGallery({ generationId, assets, planArtifact }: AssetGalleryProps) {
  const plan = useQuery({
    queryKey: generationKeys.artifact(generationId, planArtifact?.artifactId ?? ""),
    queryFn: () => fetchArtifactJson<TPlanTheme>(generationId, planArtifact!.artifactId),
    enabled: Boolean(planArtifact),
    staleTime: Infinity,
  });
  const drawings = assets.filter((asset) => asset.render === "svg-component" && asset.file);
  const files = useQueries({
    queries: drawings.map((asset) => ({
      queryKey: generationKeys.files(generationId, asset.file ?? "", "frontend"),
      queryFn: () => fetchFiles(generationId, asset.file ?? "", "frontend"),
      staleTime: Infinity,
    })),
  });
  const others = assets.filter((asset) => !drawings.includes(asset));
  const light = plan.data?.theme.light;
  const dark = plan.data?.theme.dark ?? light;

  return (
    <div className="flex flex-col gap-6">
      {drawings.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {drawings.map((asset, index) => {
            const file = files[index]?.data;
            const svg = file?.type === "file" ? file.content : null;
            return (
              <figure key={asset.id} className="flex flex-col gap-2" data-asset={asset.id}>
                <div className="grid grid-cols-2 gap-2">
                  {[light, dark].map((palette, tile) =>
                    svg && palette ? (
                      // eslint-disable-next-line @next/next/no-img-element -- a data: URL of the themed drawing
                      <img
                        key={tile}
                        src={themedSvgUrl(svg, palette)}
                        alt={`${asset.id} on the ${tile ? "dark" : "light"} theme`}
                        className="aspect-video w-full rounded-md border object-contain"
                        style={{ background: palette.background }}
                      />
                    ) : (
                      <Skeleton key={tile} className="aspect-video w-full" />
                    ),
                  )}
                </div>
                <figcaption className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-mono">{asset.id}</span>
                  <Badge variant="outline">{asset.source}</Badge>
                  {asset.cached && <Badge variant="secondary">cached</Badge>}
                  {file?.type === "file" && <span className="text-muted-foreground">{formatBytes(file.size)}</span>}
                </figcaption>
              </figure>
            );
          })}
        </div>
      )}
      {others.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm">
          {others.map((asset) => (
            <li key={asset.id} className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs">{asset.id}</span>
              <Badge variant={asset.fallback ? "destructive" : "outline"}>{MODE_LABELS[asset.render]}</Badge>
              <span className="truncate text-xs text-muted-foreground">{asset.fallback ?? asset.source}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
