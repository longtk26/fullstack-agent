"use client";

import { Check, Palette, PanelLeft, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Stack } from "@/components/layout/Stack";
import { cn } from "@/lib/utils";
import { SHELLS, VIEWS, editAppDesign, readAppDesign } from "../lib/app-design";

type AppDesignPanelProps = {
  specText: string;
  onApply: (text: string) => void;
};

/** How loud a recipe is (`agent-api` `frontend/app/recipes.py` FAMILIES), for the cards' hint. */
const FAMILY: Record<string, string> = {
  minimal: "quiet",
  swiss: "quiet",
  enterprise: "quiet",
  editorial: "quiet",
  material: "quiet",
  soft: "soft",
  clay: "soft",
  playful: "soft",
  glass: "bold",
  aurora: "bold",
  brutalist: "bold",
  neon: "bold",
};

/**
 * Epic 23 (Stories 23.6, 23.7): an app draft's design brief in the editor: pick one of the three looks, the shell and
 * each entity's view. Each is a spec edit the app kit reads (no model call, no other screen changes).
 */
export function AppDesignPanel({ specText, onApply }: AppDesignPanelProps) {
  const design = readAppDesign(specText);
  if (!design) return null;
  const apply = (next: string | null) => {
    if (next !== null) onApply(next);
  };
  return (
    <Stack gap="md" className="text-sm">
      <div className="flex flex-col gap-2">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          <Palette className="size-4" aria-hidden /> Looks
        </span>
        <div className="grid gap-2">
          {design.looks.map((look) => {
            const picked = look.recipe === design.recipe;
            return (
              <button
                key={look.recipe}
                type="button"
                aria-pressed={picked}
                onClick={() => apply(editAppDesign(specText, { recipe: look.recipe }))}
                className={cn(
                  "flex items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent",
                  picked && "border-primary bg-accent",
                )}
              >
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full border">
                  {picked && <Check className="size-3.5" aria-hidden />}
                </span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="flex items-center gap-2 font-medium capitalize">
                    {look.recipe}
                    <Badge variant="outline">{FAMILY[look.recipe] ?? "custom"}</Badge>
                  </span>
                  {look.reason && <span className="text-xs text-muted-foreground">{look.reason}</span>}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          <PanelLeft className="size-4" aria-hidden /> Layout
          {design.archetype && <Badge variant="secondary">{design.archetype}</Badge>}
        </span>
        <label className="flex items-center justify-between gap-2">
          <span>Shell</span>
          <Select value={design.shell ?? "sidebar"} onValueChange={(value) => value && apply(editAppDesign(specText, { shell: String(value) }))}>
            <SelectTrigger size="sm" className="w-36" aria-label="Shell">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SHELLS.map((shell) => (
                <SelectItem key={shell} value={shell}>
                  {shell}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        {design.views.map(({ entity, view }) => (
          <label key={entity} className="flex items-center justify-between gap-2">
            <span className={cn(entity === design.mainEntity && "font-medium")}>{entity}</span>
            <Select value={view} onValueChange={(value) => value && apply(editAppDesign(specText, { entity, view: String(value) }))}>
              <SelectTrigger size="sm" className="w-36" aria-label={`${entity} view`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VIEWS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
        ))}
      </div>
      {design.areas.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Users className="size-4" aria-hidden /> Areas
          </span>
          {design.areas.map((area) => (
            <span key={area.id}>
              {area.label} <span className="text-muted-foreground">({area.roles.join(", ")})</span>
            </span>
          ))}
        </div>
      )}
      {design.replaced.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Changed by code ({design.replaced.length})</summary>
          <ul className="mt-1 list-disc pl-4">
            {design.replaced.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="text-xs text-muted-foreground">Looks, the shell and views change without a model call.</p>
    </Stack>
  );
}
