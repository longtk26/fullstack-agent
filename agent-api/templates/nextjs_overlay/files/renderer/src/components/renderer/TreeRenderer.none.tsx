import type { TTreeNode } from "../site"; // copied into tree/

/**
 * Copied as `tree/TreeRenderer.tsx` on a site without designed pages (Epic 21): `PageRenderer` and `SiteShell`
 * import the tree renderer, but such a site has no tree to draw, so it ships without the renderer and its primitives.
 */
export function TreeRenderer(_props: { node: TTreeNode; pageId: string }) {
  return null;
}
