import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { Container } from "./Container";

type SectionProps = ComponentProps<"section"> & {
  title?: string;
  description?: string;
};

/** A page section: vertical rhythm from the density token, optional heading. */
export function Section({ title, description, className, children, ...props }: SectionProps) {
  return (
    <section className={cn("py-[calc(var(--density-gap)*2)]", className)} {...props}>
      <Container className="flex flex-col gap-6">
        {(title || description) && (
          <div className="flex flex-col gap-2">
            {title && <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>}
            {description && <p className="text-muted-foreground">{description}</p>}
          </div>
        )}
        {children}
      </Container>
    </section>
  );
}
