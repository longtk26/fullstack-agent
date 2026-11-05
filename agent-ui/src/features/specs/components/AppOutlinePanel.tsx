import { ChartColumn, LayoutDashboard, PanelLeft, Table2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Stack } from "@/components/layout/Stack";
import type { TAppOutlineSummary } from "../lib/frontend-spec-summary";

/** Epic 22: what a dynamic app draft is (navigation, entities, dashboard), in place of its pages. Code builds every
 * screen from it; edits go through the FrontendSpec editor (`app`). */
export function AppOutlinePanel({ outline }: { outline: TAppOutlineSummary }) {
  const home = outline.home === "dashboard" ? "Dashboard" : outline.home;
  return (
    <Stack gap="sm" className="text-sm">
      {outline.tagline && <p className="text-muted-foreground">{outline.tagline}</p>}
      <div className="flex flex-wrap items-center gap-1.5">
        <PanelLeft className="size-4 text-muted-foreground" aria-hidden />
        <span className="text-muted-foreground">Navigation:</span>
        {outline.nav.length ? (
          outline.nav.map((item) => (
            <Badge key={item.entity} variant="secondary">
              {item.label}
            </Badge>
          ))
        ) : (
          <span className="text-muted-foreground">none</span>
        )}
        <span className="text-muted-foreground">· opens on {home}</span>
        {outline.landing && <Badge variant="outline">public landing page</Badge>}
      </div>
      <ul className="flex flex-col gap-1">
        {outline.entities.map((entity) => (
          <li key={entity.name} className="flex flex-wrap items-baseline gap-x-2">
            <Table2 className="size-4 shrink-0 translate-y-0.5 text-muted-foreground" aria-hidden />
            <span className="font-medium">{entity.plural}</span>
            <span className="text-xs text-muted-foreground">
              {entity.listStyle ?? "table"}: {entity.listFields.join(", ") || "default fields"}
              {!entity.inNav && " · from its parent"}
            </span>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-1.5">
        <LayoutDashboard className="size-4 text-muted-foreground" aria-hidden />
        <span className="text-muted-foreground">Dashboard:</span>
        {outline.dashboard.length ? (
          outline.dashboard.map((item, index) => (
            <Badge key={`${item.label}-${index}`} variant="outline">
              {item.kind !== "figure" && <ChartColumn aria-hidden />}
              {item.label}
            </Badge>
          ))
        ) : (
          <span className="text-muted-foreground">recent records only</span>
        )}
      </div>
    </Stack>
  );
}
