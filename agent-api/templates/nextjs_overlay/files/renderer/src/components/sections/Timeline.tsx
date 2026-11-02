import { Section } from "@/components/layout/Section";
import { cn } from "@/lib/utils";
import { AssetImage, backdropImage } from "./AssetImage";
import type { TTimelineContent } from "./types";

type TimelineProps = TTimelineContent;

/**
 * A story over time (Story 20.8): `vertical` (dates down a line on the left) or `alternating` (entries on both
 * sides of a centre line from 768 px; one column on phones).
 */
export function Timeline({ title, description, items = [], form = "vertical", background, backgroundImage }: TimelineProps) {
  const alternating = form === "alternating";
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      <ol className={cn("relative flex flex-col gap-10", alternating ? "md:gap-12" : "border-l border-border pl-8")}>
        {alternating && <span aria-hidden className="absolute inset-y-0 left-1/2 hidden w-px bg-border md:block" />}
        {items.map((item, index) => (
          <li
            key={`${item.date}-${item.title}`}
            className={cn(
              "relative flex flex-col gap-2",
              alternating && "md:w-1/2",
              alternating && (index % 2 === 0 ? "md:pr-12 md:text-right" : "md:ml-auto md:pl-12"),
            )}
          >
            <span
              aria-hidden
              className={cn(
                "absolute top-1.5 size-3 rounded-full bg-primary",
                alternating ? (index % 2 === 0 ? "hidden md:block md:-right-1.5" : "hidden md:block md:-left-1.5") : "-left-[2.4rem]",
              )}
            />
            <p className="text-sm font-medium text-primary">{item.date}</p>
            <h3 className="text-lg font-semibold">{item.title}</h3>
            {item.body && <p className={cn("max-w-prose text-muted-foreground", alternating && index % 2 === 0 && "md:ml-auto")}>{item.body}</p>}
            {item.image && <AssetImage asset={item.image} className="mt-2 max-w-md" />}
          </li>
        ))}
      </ol>
    </Section>
  );
}
