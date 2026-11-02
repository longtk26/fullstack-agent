import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TTestimonialsContent } from "./types";

type TestimonialsProps = TTestimonialsContent;
type TItem = NonNullable<TestimonialsProps["items"]>[number];

const key = (item: TItem) => `${item.author}-${item.quote.slice(0, 20)}`;

function Author({ item }: { item: TItem }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground">
      <Avatar>
        <AvatarFallback>{item.author.slice(0, 1)}</AvatarFallback>
      </Avatar>
      <span>
        {item.author}
        {item.role && <span className="block">{item.role}</span>}
      </span>
    </div>
  );
}

function QuoteCard({ item, cardStyle }: { item: TItem; cardStyle: TestimonialsProps["cardStyle"] }) {
  return (
    <Card className={cardClass(cardStyle)}>
      <CardContent className="flex flex-col gap-4">
        <blockquote className="max-w-prose text-lg">&ldquo;{item.quote}&rdquo;</blockquote>
        <Author item={item} />
      </CardContent>
    </Card>
  );
}

/** One large quote, with the others (if any) as a short list beneath. */
function LargeQuote({ items }: { items: TItem[] }) {
  const [first, ...rest] = items;
  if (!first) return null;
  return (
    <div className="flex flex-col gap-10">
      <figure className="flex flex-col gap-6">
        <blockquote className="max-w-4xl text-2xl font-medium tracking-tight text-balance">
          &ldquo;{first.quote}&rdquo;
        </blockquote>
        <figcaption>
          <Author item={first} />
        </figcaption>
      </figure>
      {rest.length > 0 && (
        <ul className="grid gap-6 border-t border-border pt-8 md:grid-cols-2">
          {rest.map((item) => (
            <li key={key(item)} className="flex flex-col gap-3">
              <blockquote className="max-w-prose text-muted-foreground">&ldquo;{item.quote}&rdquo;</blockquote>
              <span className="text-sm">
                {item.author}
                {item.role && <span className="text-muted-foreground">, {item.role}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** One row of quotes; on small screens it scrolls sideways instead of stacking. */
function Strip({ items, cardStyle, label }: { items: TItem[]; cardStyle: TestimonialsProps["cardStyle"]; label: string }) {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0"
    >
      {items.map((item) => (
        <div key={key(item)} className="w-[85%] shrink-0 snap-start sm:w-[calc(50%-0.5rem)] lg:w-[calc(33.333%-0.667rem)]">
          <QuoteCard item={item} cardStyle={cardStyle} />
        </div>
      ))}
    </div>
  );
}

/**
 * Quotes with their authors, in three forms (Stories 17.7, 20.2): `cards` (a grid), `quote` (the first as one large
 * quote) and `strip` (one sideways-scrolling row).
 */
export function Testimonials(props: TestimonialsProps) {
  const { title = "What clients say", items = [], cardStyle, form = "cards", background, backgroundImage } = props;
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      {form === "quote" && <LargeQuote items={items} />}
      {form === "strip" && <Strip items={items} cardStyle={cardStyle} label={title} />}
      {form === "cards" && (
        <Grid columns={items.length > 1 ? 2 : 1}>
          {items.map((item) => (
            <QuoteCard key={key(item)} item={item} cardStyle={cardStyle} />
          ))}
        </Grid>
      )}
    </Section>
  );
}
