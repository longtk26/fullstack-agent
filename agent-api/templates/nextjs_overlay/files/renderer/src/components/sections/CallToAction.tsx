import { Container } from "@/components/layout/Container";
import { Backdrop, surfaceClass } from "@/components/layout/Section";
import { cn } from "@/lib/utils";
import { backdropImage } from "./AssetImage";
import { CtaLink } from "./CtaLink";
import type { TCallToActionContent } from "./types";

type CallToActionProps = TCallToActionContent;

/** A closing panel; `background` colours the panel (primary by default, outlined on `default`). */
export function CallToAction({ heading, body, cta, background = "primary", backgroundImage }: CallToActionProps) {
  return (
    <section className="py-16">
      <Container>
        <div
          className={cn(
            "flex flex-col items-start gap-4 rounded-2xl px-8 py-10 sm:flex-row sm:items-center sm:justify-between",
            background === "default" ? "bg-card ring-1 ring-border" : surfaceClass(background),
          )}
        >
          {background === "image" && backgroundImage && <Backdrop>{backdropImage(backgroundImage)}</Backdrop>}
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold tracking-tight text-balance">{heading}</h2>
            {body && <p className="max-w-prose text-muted-foreground">{body}</p>}
          </div>
          <CtaLink cta={cta} />
        </div>
      </Container>
    </section>
  );
}
