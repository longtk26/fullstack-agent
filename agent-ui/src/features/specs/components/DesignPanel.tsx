import { Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Stack } from "@/components/layout/Stack";
import { applyDirectionToText, isCurrentDirection } from "../lib/design-direction";
import type { TDesignDirection, TDraftDesign } from "../types";

const SWATCHES = ["primary", "accent", "background", "foreground", "muted"] as const;

type DesignPanelProps = {
  design: TDraftDesign;
  specText: string;
  onApply: (text: string) => void;
};

function DirectionCard({
  direction,
  picked,
  current,
  onUse,
}: {
  direction: TDesignDirection;
  picked: boolean;
  current: boolean;
  onUse: (() => void) | null;
}) {
  const { theme } = direction;
  const fonts = [...new Set([theme.typography.headingFont, theme.typography.bodyFont])].join(" / ");
  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3" data-current={current || undefined}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">{direction.label}</span>
        {picked && <Badge variant="secondary">draft&apos;s pick</Badge>}
        {current && (
          <Badge variant="outline">
            <Check /> in the editor
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-1" aria-label="Colours">
        {SWATCHES.map((name) => (
          <span
            key={name}
            className="size-5 rounded-sm border"
            style={{ background: theme.colors[name] }}
            title={`${name}: ${theme.colors[name]}`}
          />
        ))}
        <span className="ml-1 truncate text-xs text-muted-foreground">{direction.palette}</span>
      </div>
      <p className="text-xs">
        {fonts} <span className="text-muted-foreground">· {direction.fontPairing}</span>
      </p>
      <p className="text-xs text-muted-foreground">
        {theme.style} · radius {theme.radius} · hero {direction.heroVariant}
        <br />
        Home: {direction.homeOrder.join(" → ")}
      </p>
      {direction.avoid.length > 0 && (
        <p className="text-xs text-muted-foreground">Avoid: {direction.avoid.join(", ").toLowerCase()}</p>
      )}
      {!current && (
        <div>
          <Button size="sm" variant="outline" onClick={onUse ?? undefined} disabled={!onUse}>
            Use this direction
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * The design directions of the draft in the editor (Story 12.6 / 9.7b): the chosen one and two alternatives.
 * Using one replaces the theme, the home page's section order and the hero layout in the FrontendSpec, with no
 * engine call; pages, content and other edits stay.
 */
export function DesignPanel({ design, specText, onApply }: DesignPanelProps) {
  return (
    <Stack gap="sm">
      {design.directions.map((direction, index) => {
        const next = applyDirectionToText(specText, direction);
        return (
          <DirectionCard
            key={direction.label}
            direction={direction}
            picked={index === design.selected}
            current={isCurrentDirection(specText, direction)}
            onUse={next === null ? null : () => onApply(next)}
          />
        );
      })}
      <p className="text-xs text-muted-foreground">
        From {design.directions[0]?.source}. Switching keeps your pages and content.
      </p>
    </Stack>
  );
}
