import { Section } from "@/components/layout/Section";
import { cn } from "@/lib/utils";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TPriceListContent } from "./types";

type PriceListProps = TPriceListContent;
type TGroup = PriceListProps["groups"][number];
type TPrice = TGroup["items"][number];

const price = (value: TPrice["price"]) => (value === null || value === undefined || value === "" ? null : String(value));

function Entry({ item, leader }: { item: TPrice; leader: boolean }) {
  const shown = price(item.price);
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-baseline gap-3">
        <span className="font-medium">{item.name}</span>
        {leader && <span aria-hidden className="flex-1 translate-y-[-0.2em] border-b border-dotted border-border" />}
        {!leader && <span className="flex-1" />}
        {shown && <span className="font-heading font-semibold tabular-nums">{shown}</span>}
      </div>
      {(item.description || (item.tags && item.tags.length > 0)) && (
        <p className="max-w-prose text-sm text-muted-foreground">
          {item.description}
          {item.tags && item.tags.length > 0 && (
            <span className="text-primary">
              {item.description ? " · " : ""}
              {item.tags.join(" · ")}
            </span>
          )}
        </p>
      )}
    </li>
  );
}

function Group({ group, leader, className }: { group: TGroup; leader: boolean; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {group.title && <h3 className="text-lg font-semibold">{group.title}</h3>}
      <ul className="flex flex-col gap-4">
        {group.items.map((item) => (
          <Entry key={item.name} item={item} leader={leader} />
        ))}
      </ul>
    </div>
  );
}

/**
 * A menu or price list in groups (Story 20.8): `menu` (names and prices joined by dotted leaders, one column),
 * `columns` (groups side by side from 768 px) and `cards` (each group on a card). Prices are written as given.
 */
export function PriceList({ title, description, groups, form = "menu", background, backgroundImage }: PriceListProps) {
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      <div
        className={cn(
          "grid gap-10",
          form === "menu" && "max-w-2xl",
          form !== "menu" && groups.length > 1 && "md:grid-cols-2",
          form !== "menu" && groups.length > 2 && "lg:grid-cols-3",
        )}
      >
        {groups.map((group, index) => (
          <Group
            key={group.title ?? index}
            group={group}
            leader={form !== "cards"}
            className={form === "cards" ? cn(cardClass("filled"), "rounded-xl p-6") : undefined}
          />
        ))}
      </div>
    </Section>
  );
}
