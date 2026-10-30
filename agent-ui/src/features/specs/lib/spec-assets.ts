/** Reading and editing a FrontendSpec's `assets` in the editor text (Story 15.4); null while the JSON does not parse. */

export type TSpecAsset = { id: string; kind?: string; source?: string; alt?: string; decorative?: boolean };

type TSpec = Record<string, unknown> & { assets?: TSpecAsset[] };

function parse(text: string): TSpec | null {
  try {
    const spec = JSON.parse(text) as unknown;
    return spec && typeof spec === "object" && !Array.isArray(spec) ? (spec as TSpec) : null;
  } catch {
    return null;
  }
}

function serialize(spec: TSpec): string {
  return `${JSON.stringify(spec, null, 2)}\n`;
}

export function specAssets(text: string): TSpecAsset[] {
  const assets = parse(text)?.assets;
  return Array.isArray(assets) ? assets.filter((asset) => typeof asset?.id === "string") : [];
}

/** The text with one asset's `source` replaced (e.g. by `upload:<id>`). */
export function setAssetSource(text: string, assetId: string, source: string): string | null {
  const spec = parse(text);
  if (!spec) return null;
  const assets = (spec.assets ?? []).map((asset) => (asset.id === assetId ? { ...asset, source } : asset));
  return serialize({ ...spec, assets });
}

/** An asset id from a file name, unique among the spec's assets: `Team Photo.JPG` → `team-photo`. */
export function assetIdFor(filename: string, taken: string[]): string {
  const base =
    filename
      .replace(/\.[^.]+$/, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/^(?![a-z])/, "image-")
      .slice(0, 50) || "image";
  let id = base;
  for (let n = 2; taken.includes(id); n += 1) id = `${base}-${n}`;
  return id;
}

/** The text with a new image asset for an upload; the page sections still need `asset:<id>` to show it. */
export function addUploadAsset(text: string, source: string, filename: string, kind = "image"): string | null {
  const spec = parse(text);
  if (!spec) return null;
  const assets = spec.assets ?? [];
  const id = assetIdFor(filename, assets.map((asset) => asset.id));
  const alt = filename.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
  return serialize({ ...spec, assets: [...assets, { id, kind, source, alt }] });
}
