// Story 23.0 prototype only (scripts/app_design_proto): the design brief the prototype reads. Not a kit file.
import { useSyncExternalStore } from "react";
import data from "@/content/design.json";
import { useSession } from "./plugins";

export type TView = "table" | "cards" | "media-grid" | "feed" | "board" | "calendar";
export type TRoles = {
  media?: string;
  title?: string;
  subtitle?: string;
  meta?: string[];
  badge?: string;
  stat?: string;
  price?: string;
  avatar?: string;
};
export type TLayout = {
  archetype: string;
  shell: "sidebar" | "topbar" | "topbar-tabs" | "rail";
  mobileNav: "drawer" | "bottom-tabs";
  homeView: string;
  mainEntity: string;
  frame: "narrow" | "standard" | "wide";
  entities: Record<string, { view: TView; roles: TRoles; groupBy?: string; dateField?: string }>;
};
export type TArea = TLayout & { id: string; label: string; roles: string[] };
export type TBrief = TLayout & {
  looks: { recipe: string; reason: string }[];
  areas: TArea[];
};

export const brief = data as unknown as TBrief;

const subscribe = () => () => {};
const readSearch = () => window.location.search;

/** `?proto=off` shows today's kit; `?look=<recipe>` picks one of the looks (default: the first). */
export function useProto(): { on: boolean; look: string } {
  const search = useSyncExternalStore(subscribe, readSearch, () => "");
  const params = new URLSearchParams(search);
  const on = params.get("proto") !== "off";
  const look = on ? (params.get("look") ?? brief.looks[0]?.recipe ?? "minimal") : "kit";
  return { on, look };
}

/** The layout of the signed-in user's area (prototype: chosen by role at run time; Story 23.10 gives each area its
 *  own routes), else the app's. */
export function useLayout(): TLayout & { area?: TArea } {
  const session = useSession();
  const role = session.user?.role ? String(session.user.role) : null;
  const area = role ? (brief.areas ?? []).find((a) => a.roles.includes(role)) : undefined;
  return area ? { ...area, area } : brief;
}
