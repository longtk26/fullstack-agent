import { Container } from "@/components/layout/Container";
import { Backdrop, surfaceClass } from "@/components/layout/Section";
import { cn } from "@/lib/utils";
import { AssetImage } from "./AssetImage";
import { CtaLink } from "./CtaLink";
import { headlineClass } from "./styles";
import type { THeroContent } from "./types";

type HeroProps = THeroContent;

/**
 * The page opener, in three layouts: `split` (text beside the image from 1024 px, image below on smaller screens),
 * `centered` (centred text, image below) and `banner` (full width; the image fills the band behind the text, or the
 * band takes the primary colour).
 */
export function Hero({
  variant = "split",
  background = "default",
  backgroundImage,
  heading,
  eyebrow,
  body,
  image,
  cta,
  secondaryCta,
}: HeroProps) {
  const banner = variant === "banner";
  const centered = variant === "centered";
  const backdrop = banner && image ? image : background === "image" ? backgroundImage : undefined;
  const surface = backdrop ? "image" : banner && background === "default" ? "primary" : background;
  const inline = image && !banner ? image : undefined;
  return (
    <section className={cn(banner ? "py-24 sm:py-32" : "py-16 sm:py-24", surfaceClass(surface))}>
      {backdrop && (
        <Backdrop className={banner ? "bg-linear-to-r from-background via-background/85 to-background/40" : undefined}>
          <AssetImage asset={backdrop} className="aspect-auto h-full rounded-none" />
        </Backdrop>
      )}
      <Container
        className={cn(
          "flex flex-col gap-10",
          centered && "items-center text-center",
          inline && variant === "split" && "lg:grid lg:grid-cols-2 lg:items-center",
        )}
      >
        <div className={cn("flex flex-col gap-5", centered ? "max-w-3xl items-center" : "max-w-2xl")}>
          {eyebrow && <p className="text-sm font-medium text-primary">{eyebrow}</p>}
          <h1 className={cn("font-semibold tracking-tight text-balance", headlineClass(heading))}>{heading}</h1>
          {body && <p className="max-w-prose text-lg text-muted-foreground">{body}</p>}
          {(cta || secondaryCta) && (
            <div className={cn("flex flex-wrap gap-3", centered && "justify-center")}>
              {cta && <CtaLink cta={cta} />}
              {secondaryCta && <CtaLink cta={secondaryCta} variant="outline" />}
            </div>
          )}
        </div>
        {inline && <AssetImage asset={inline} className={centered ? "max-w-4xl" : undefined} priority />}
      </Container>
    </section>
  );
}
