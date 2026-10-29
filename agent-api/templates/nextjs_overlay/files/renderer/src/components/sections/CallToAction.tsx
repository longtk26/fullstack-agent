import { Container } from "@/components/layout/Container";
import { CtaLink } from "./CtaLink";
import type { TCallToActionContent } from "./types";

type CallToActionProps = TCallToActionContent;

export function CallToAction({ heading, body, cta }: CallToActionProps) {
  return (
    <section className="py-16">
      <Container>
        <div className="flex flex-col items-start gap-4 rounded-2xl bg-primary px-8 py-10 text-primary-foreground sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold tracking-tight">{heading}</h2>
            {body && <p className="text-primary-foreground/80">{body}</p>}
          </div>
          <CtaLink cta={cta} variant="secondary" />
        </div>
      </Container>
    </section>
  );
}
