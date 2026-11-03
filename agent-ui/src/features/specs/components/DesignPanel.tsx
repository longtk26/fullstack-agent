import { Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Stack } from "@/components/layout/Stack";
import { applyDirectionToText, isCurrentDirection } from "../lib/design-direction";
import type { TDesignDirection, TDraftDesign } from "../types";

const SWATCHES = ["primary", "accent", "background", "foreground", "muted"] as const;
const TONE_LABELS = [
  ["energy", "quiet", "loud"],
  ["finish", "raw", "refined"],
  ["density", "airy", "dense"],
  ["weight", "light", "heavy"],
  ["seriousness", "playful", "serious"],
] as const;

/** The tone's leaning words ("loud, raw, airy"): scales at 1–2 or 4–5; the neutral middle says nothing. */
function toneWords(tone: TDesignDirection["tone"]): string {
  if (!tone) return "";
  return TONE_LABELS.flatMap(([scale, low, high]) => {
    const level = tone[scale] ?? 3;
    return level <= 2 ? [low] : level >= 4 ? [high] : [];
  }).join(", ");
}

/** Story 20.5 / 20.6: the direction's icon style and motion feel, e.g. "icons phosphor duotone tile · motion drop". */
function MotionAndIcons({ theme }: { theme: TDesignDirection["theme"] }) {
  const icons = theme.icons as { set?: string; weight?: string; treatment?: string } | undefined;
  const motion = theme.motion as { feel?: string; signature?: string } | undefined;
  const iconText =
    icons?.set === "none" ? "no icons" : icons ? `icons ${icons.set} ${icons.weight}${icons.treatment === "tile" ? " tile" : ""}` : "";
  const motionText =
    motion?.feel && motion.feel !== "none"
      ? `motion ${motion.feel}${motion.signature && motion.signature !== "none" ? ` + ${motion.signature}` : ""}`
      : "still";
  return (
    <>
      <br />
      {[iconText, motionText].filter(Boolean).join(" · ")}
    </>
  );
}

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
  const card = direction.source === "card";
  const fonts = [...new Set([theme.typography.headingFont, theme.typography.bodyFont])].join(" / ");
  const feel = toneWords(direction.tone);
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
      {card && direction.concept && <p className="text-xs">{direction.concept}</p>}
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
        {fonts}
        {!card && <span className="text-muted-foreground"> · {direction.fontPairing}</span>}
      </p>
      <p className="text-xs text-muted-foreground">
        hero {direction.heroVariant}
        {direction.keyVisual ? ` · ${direction.keyVisual}` : ""}
        {feel ? ` · ${feel}` : ` · ${theme.style} · radius ${theme.radius}`}
        <br />
        Home: {direction.homeOrder.join(" → ")}
        {card && <MotionAndIcons theme={theme} />}
      </p>
      {card && direction.givesUp && (
        <p className="text-xs text-muted-foreground">Gives up: {direction.givesUp.toLowerCase()}</p>
      )}
      {!card && direction.avoid.length > 0 && (
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
 * The design directions of the draft in the editor (Stories 12.6, 20.4 / 9.7b): the chosen one and two
 * alternatives. Using one replaces the theme, the home page (its sections and their order, from the draft's pool),
 * the hero layout, section forms and rhythm in the FrontendSpec, with no engine call; other pages and edits stay.
 */
export function DesignPanel({ design, specText, onApply }: DesignPanelProps) {
  const cards = design.directions.some((direction) => direction.source === "card");
  return (
    <Stack gap="sm">
      {design.directions.map((direction, index) => {
        const next = applyDirectionToText(specText, direction, design.pool);
        return (
          <DirectionCard
            key={`${index}-${direction.label}`}
            direction={direction}
            picked={index === design.selected}
            current={isCurrentDirection(specText, direction)}
            onUse={next === null ? null : () => onApply(next)}
          />
        );
      })}
      <p className="text-xs text-muted-foreground">
        {cards
          ? `Written for this requirement${design.seed ? ` (variation ${design.seed})` : ""}; checked to differ from each other.`
          : `From ${design.directions[0]?.source}.`}{" "}
        Switching keeps your pages and content.
      </p>
    </Stack>
  );
}

type DesignPanelProps = {
  design: TDraftDesign;
  specText: string;
  onApply: (text: string) => void;
};
