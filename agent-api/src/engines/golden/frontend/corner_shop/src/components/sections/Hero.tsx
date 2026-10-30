import { Container } from "@/components/layout/Container";
import { AssetImage } from "@/components/assets/AssetImage";
import { CtaLink, type TCta } from "./CtaLink";

type HeroProps = {
  heading: string;
  body?: string;
  image?: string;
  cta?: TCta;
};

export function Hero({ heading, body, image, cta }: HeroProps) {
  return (
    <section className="py-16 sm:py-24">
      <Container className="grid items-center gap-10 md:grid-cols-2">
        <div className="flex flex-col gap-5">
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">{heading}</h1>
          {body && <p className="text-lg text-muted-foreground">{body}</p>}
          {cta && (
            <div>
              <CtaLink cta={cta} />
            </div>
          )}
        </div>
        {image && <AssetImage asset={image} />}
      </Container>
    </section>
  );
}
