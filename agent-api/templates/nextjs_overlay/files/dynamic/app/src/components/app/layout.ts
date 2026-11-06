"use client";

import { usePathname } from "next/navigation";
import { app, type TArea, type TDesign, type TEntityDesign } from "./app";

/** The area a path belongs to (Story 23.10): the one with the longest prefix that starts the path; the first area
 *  (prefix `/`) otherwise. None in an app without areas. */
export function areaOf(pathname: string): TArea | undefined {
  const areas = app.areas ?? [];
  const inside = areas.filter((area) => area.prefix !== "/" && (pathname === area.prefix || pathname.startsWith(`${area.prefix}/`)));
  return inside.sort((a, b) => b.prefix.length - a.prefix.length)[0] ?? areas.find((area) => area.prefix === "/");
}

/** The layout on screen (Epic 23): the app's design, with the current area's choices over it. */
export function useLayout(): TDesign & { area?: TArea } {
  const pathname = usePathname() ?? "/";
  const area = areaOf(pathname);
  if (!area) return app.design;
  return {
    ...app.design,
    ...area.design,
    entities: { ...app.design.entities, ...(area.design.entities ?? {}) },
    looks: app.design.looks,
    area,
  } as TDesign & { area?: TArea };
}

/** How an entity's list is shown here: the layout's view, else the outline's list style. */
export function entityDesign(design: TDesign, entity: string | undefined): TEntityDesign {
  const found = entity ? design.entities?.[entity] : undefined;
  if (found) return found;
  const style = entity ? app.entities[entity]?.listStyle : undefined;
  return { view: style === "cards" ? "cards" : "table", roles: {} };
}

/** A page's width by the layout's frame. */
export const FRAME_WIDTH: Record<TDesign["frame"], string> = {
  narrow: "max-w-3xl",
  standard: "max-w-6xl",
  wide: "max-w-screen-2xl",
  full: "max-w-none",
};
