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

/** Hero headline size by length, so it fits two lines at 390, 768 and 1440 px (design checklist). */
export function headlineClass(heading: string): string {
  if (heading.length <= 28) return "text-4xl sm:text-5xl lg:text-6xl";
  if (heading.length <= 42) return "text-3xl sm:text-4xl lg:text-5xl";
  return "text-2xl sm:text-4xl";
}
