"use client";

import { AppWindow, Globe, Server } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TGenerationMode } from "../types";

const MODE_CARDS: { mode: TGenerationMode; title: string; description: string; icon: LucideIcon }[] = [
  { mode: "static", title: "Static website", description: "Pages only, no backend", icon: Globe },
  {
    mode: "dynamic",
    title: "Dynamic web app",
    description: "Frontend + backend from one API contract",
    icon: AppWindow,
  },
  { mode: "backend", title: "Backend API only", description: "A tested FastAPI backend from a BackendSpec", icon: Server },
];

type ModeCardsProps = {
  mode: TGenerationMode;
  onChange: (mode: TGenerationMode) => void;
};

export function ModeCards({ mode, onChange }: ModeCardsProps) {
  return (
    <div role="radiogroup" aria-label="What to generate" className="grid gap-3 sm:grid-cols-3">
      {MODE_CARDS.map((card) => {
        const selected = card.mode === mode;
        const Icon = card.icon;
        return (
          <button
            key={card.mode}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(card.mode)}
            className={cn(
              "flex items-start gap-3 rounded-xl bg-card p-4 text-left ring-1 ring-foreground/10 transition-colors hover:bg-muted/50 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none",
              selected && "bg-primary/5 ring-2 ring-primary hover:bg-primary/5",
            )}
          >
            <Icon className={cn("mt-0.5 size-5 shrink-0", selected ? "text-primary" : "text-muted-foreground")} />
            <span className="min-w-0">
              <span className="block font-medium">{card.title}</span>
              <span className="block text-sm text-muted-foreground">{card.description}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
