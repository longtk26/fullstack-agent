import { Container } from "@/components/layout/Container";
import { AssetImage } from "./AssetImage";
import { CtaLink } from "./CtaLink";
import type { THeroContent } from "./types";

type HeroProps = THeroContent;

export function Hero({ heading, eyebrow, body, image, cta, secondaryCta }: HeroProps) {
  return (
    <section className="py-16 sm:py-24">
      <Container className={image ? "grid items-center gap-10 md:grid-cols-2" : "flex flex-col"}>
        <div className="flex flex-col gap-5">
          {eyebrow && <p className="text-sm font-medium text-primary">{eyebrow}</p>}
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">{heading}</h1>
          {body && <p className="text-lg text-muted-foreground">{body}</p>}
          {(cta || secondaryCta) && (
            <div className="flex flex-wrap gap-3">
              {cta && <CtaLink cta={cta} />}
              {secondaryCta && <CtaLink cta={secondaryCta} variant="outline" />}
            </div>
          )}
        </div>
        {image && <AssetImage asset={image} />}
      </Container>
    </section>
  );
}
