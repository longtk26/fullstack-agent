export type TCardStyle = "outline" | "filled" | "plain";

// Card looks for list sections (Story 17.7), on top of the shadcn card: outlined (default), a muted surface, or no
// surface at all. Theme tokens only.
const CARD_STYLES: Record<TCardStyle, string> = {
  outline: "",
  filled: "bg-muted ring-0",
  plain: "gap-2 rounded-none bg-transparent ring-0 [--card-spacing:0px]",
};

export function cardClass(style: TCardStyle = "outline"): string {
  return CARD_STYLES[style];
}

// Hero sizes (Story 20.3) read `--hero-<step>` from globals.css: Tailwind's display steps after the theme's ratio and
// display scale (a wide heading face or capitals shrink them), with Tailwind's line heights, so a theme without
// tokens and with a face of normal width renders exactly the sizes `text-4xl` … `text-9xl` would.

/** Hero headline size by length, so it fits two lines at 390, 768 and 1440 px (design checklist). */
export function headlineClass(heading: string): string {
  if (heading.length <= 28) {
    return "text-(length:--hero-4xl) leading-[1.111] sm:text-(length:--hero-5xl) sm:leading-none lg:text-(length:--hero-6xl)";
  }
  if (heading.length <= 42) {
    return "text-(length:--hero-3xl) leading-[1.2] sm:text-(length:--hero-4xl) sm:leading-[1.111] lg:text-(length:--hero-5xl) lg:leading-none";
  }
  return "text-(length:--hero-2xl) leading-[1.333] sm:text-(length:--hero-4xl) sm:leading-[1.111]";
}

/** The `type` hero (Story 20.2): the headline is the image, set larger than `headlineClass` but still two lines at
 * most at 390, 768 and 1440 px; long headlines fall back to the normal size. */
export function displayClass(heading: string): string {
  if (heading.length <= 16) {
    return "text-(length:--hero-5xl) leading-none sm:text-(length:--hero-7xl) lg:text-(length:--hero-9xl)";
  }
  if (heading.length <= 28) {
    return "text-(length:--hero-4xl) leading-[1.111] sm:text-(length:--hero-6xl) sm:leading-none lg:text-(length:--hero-8xl)";
  }
  if (heading.length <= 42) {
    return "text-(length:--hero-3xl) leading-[1.2] sm:text-(length:--hero-5xl) sm:leading-none lg:text-(length:--hero-7xl)";
  }
  return headlineClass(heading);
}
