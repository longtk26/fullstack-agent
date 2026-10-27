import { Container } from "@/components/layout/Container";
import { CtaLink, type TCta } from "./CtaLink";

type CallToActionProps = {
  heading: string;
  cta: TCta;
};

export function CallToAction({ heading, cta }: CallToActionProps) {
  return (
    <section className="py-16">
      <Container>
        <div className="flex flex-col items-start gap-4 rounded-2xl bg-primary px-8 py-10 text-primary-foreground sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">{heading}</h2>
          <CtaLink cta={cta} variant="secondary" />
        </div>
      </Container>
    </section>
  );
}
