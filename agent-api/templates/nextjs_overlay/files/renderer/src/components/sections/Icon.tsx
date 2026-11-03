import { glyphSet, glyphs, icons, iconStyle, type TGlyph } from "@/components/renderer/icons";
import { cn } from "@/lib/utils";

// Lucide draws weights as stroke widths; fill and duotone exist only in Phosphor (Lucide shows them bold).
const STROKE = { thin: 1, light: 1.5, regular: 2, bold: 2.5, fill: 2.5, duotone: 2.5 } as const;

type IconProps = {
  /** An item's icon, already resolved to the site's set when the site was generated (`phosphor:Truck`). */
  icon?: string | null;
  /** One of the library's own marks (a check, contact details), drawn in the site's set. */
  glyph?: TGlyph;
  /** A glyph that only decorates (contact details): left out when the site has no content icons. */
  decorative?: boolean;
  /** Draw content icons in the site's treatment (`tile`: a small rounded square in the muted tone). */
  framed?: boolean;
  className?: string;
};

/**
 * A content icon in the site's set, weight and treatment (Story 20.5, `theme.icons`). Decorative: hidden from
 * assistive technology, since the text next to it carries the meaning. 1.25 × the surrounding text, so it follows
 * the text it sits with. Renders nothing for an item without an icon or with the set "none".
 */
export function Icon({ icon, glyph, decorative = false, framed = false, className }: IconProps) {
  const Component = glyph ? glyphs[glyph] : icon ? icons[icon] : undefined;
  if (!Component || (glyph && decorative && iconStyle.set === "none")) return null;
  const set = glyph ? glyphSet : iconStyle.set;
  const weight = set === "phosphor" ? { weight: iconStyle.weight } : { strokeWidth: STROKE[iconStyle.weight] };
  const svg = (
    <Component aria-hidden focusable="false" size="1.25em" className={cn("shrink-0", className)} {...weight} />
  );
  if (!framed || glyph || iconStyle.treatment !== "tile") return svg;
  return (
    <span aria-hidden className="inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-primary">
      {svg}
    </span>
  );
}
