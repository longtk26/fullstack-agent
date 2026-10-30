import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Container } from "./Container";

export type TSurface = "default" | "muted" | "primary" | "image";

// `surface-inverse` (globals.css) swaps the tokens inside: primary becomes the background, so text, cards and
// buttons keep their contrast in every theme and in dark mode.
const SURFACES: Record<TSurface, string> = {
  default: "",
  muted: "bg-muted",
  primary: "surface-inverse bg-background text-foreground",
  image: "relative isolate overflow-hidden",
};

export function surfaceClass(background: TSurface = "default"): string {
  return SURFACES[background];
}

/** An image behind a section's content, under a scrim in the page colour so text stays readable. */
export function Backdrop({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div aria-hidden className="absolute inset-0 -z-10">
      {children}
      <div className={cn("absolute inset-0 bg-background/85", className)} />
    </div>
  );
}

type SectionProps = ComponentProps<"section"> & {
  title?: string;
  description?: string;
  background?: TSurface;
  backdrop?: ReactNode;
};

/** A page section: vertical rhythm from the density token, optional heading, a background from the theme. */
export function Section({ title, description, background, backdrop, className, children, ...props }: SectionProps) {
  return (
    <section className={cn("py-[calc(var(--density-gap)*2)]", surfaceClass(background), className)} {...props}>
      {background === "image" && backdrop && <Backdrop>{backdrop}</Backdrop>}
      <Container className="flex flex-col gap-6">
        {(title || description) && (
          <div className="flex flex-col gap-2">
            {title && <h2 className="text-2xl font-semibold tracking-tight text-balance">{title}</h2>}
            {description && <p className="max-w-prose text-muted-foreground">{description}</p>}
          </div>
        )}
        {children}
      </Container>
    </section>
  );
}
