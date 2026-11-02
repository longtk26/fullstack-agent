import { Section } from "@/components/layout/Section";
import { cn } from "@/lib/utils";
import { backdropImage } from "./AssetImage";
import type { TStepsContent } from "./types";

type StepsProps = TStepsContent;

/**
 * How something works, step by step (Story 20.8), in three forms: `numbered` (rows with a numeral), `horizontal`
 * (one row of steps from 768 px, joined by a line) and `connected` (a vertical line joining numbered dots). An ordered
 * list in every form, so the order is read out too.
 */
export function Steps({ title, description, items = [], form = "numbered", background, backgroundImage }: StepsProps) {
  const horizontal = form === "horizontal";
  const connected = form === "connected";
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      <ol
        className={cn(
          "grid gap-8",
          horizontal && "md:grid-flow-col md:auto-cols-fr md:gap-6",
          connected && "relative gap-10 border-l border-border pl-8",
        )}
      >
        {items.map((item, index) => (
          <li key={item.title} className={cn("relative flex gap-5", horizontal && "md:flex-col md:gap-4")}>
            <span
              aria-hidden
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-full font-heading font-semibold tabular-nums",
                connected
                  ? "absolute top-0 -left-[3.25rem] bg-primary text-primary-foreground"
                  : "bg-background text-primary ring-1 ring-border",
              )}
            >
              {index + 1}
            </span>
            {horizontal && index < items.length - 1 && (
              <span aria-hidden className="absolute top-5 left-14 hidden h-px w-[calc(100%-2.5rem)] bg-border md:block" />
            )}
            <div className="flex flex-col gap-1">
              <h3 className="text-lg font-semibold">{item.title}</h3>
              {item.body && <p className="max-w-prose text-muted-foreground">{item.body}</p>}
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}
