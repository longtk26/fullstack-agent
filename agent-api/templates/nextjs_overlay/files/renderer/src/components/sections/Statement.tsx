import { Section } from "@/components/layout/Section";
import { cn } from "@/lib/utils";
import { AssetImage, backdropImage } from "./AssetImage";
import type { TStatementContent } from "./types";

type StatementProps = TStatementContent;

/**
 * One statement or one real quote, set apart (Story 20.8): `large` (the text in the heading face and weight, wide,
 * with an optional image beside it), `quote` (quotation marks and an accent rule) and `band` (centred; on the primary
 * colour unless a background is given). It keeps to the section title's size step and never takes the heading case,
 * so pages keep five type sizes at most and long text is never set in capitals (design checklist).
 */
export function Statement({ text, attribution, image, form = "large", background, backgroundImage }: StatementProps) {
  const band = form === "band";
  return (
    <Section background={background ?? (band ? "primary" : "default")} backdrop={backdropImage(backgroundImage)}>
      <div className={cn("flex flex-col gap-10", image && !band && "lg:grid lg:grid-cols-[3fr_2fr] lg:items-center")}>
        <figure className={cn("flex flex-col gap-5 py-[var(--density-gap)]", band && "items-center text-center")}>
          <blockquote
            className={cn(
              "max-w-4xl font-heading text-2xl text-balance [font-weight:var(--heading-weight)]",
              form === "quote" && "border-l-2 border-primary pl-6",
            )}
          >
            {form === "quote" ? <>&ldquo;{text}&rdquo;</> : text}
          </blockquote>
          {attribution && <figcaption className="text-sm text-muted-foreground">{attribution}</figcaption>}
        </figure>
        {image && !band && <AssetImage asset={image} className="aspect-[4/3]" />}
      </div>
    </Section>
  );
}
