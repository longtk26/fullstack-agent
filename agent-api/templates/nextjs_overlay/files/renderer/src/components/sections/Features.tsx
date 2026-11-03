import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AssetImage, backdropImage } from "./AssetImage";
import { Icon } from "./Icon";
import { cardClass } from "./styles";
import type { TFeaturesContent } from "./types";

type FeaturesProps = TFeaturesContent;
type TItem = NonNullable<FeaturesProps["items"]>[number];

const number = (index: number) => String(index + 1).padStart(2, "0");

function Cards({ items, columns, cardStyle }: { items: TItem[]; columns: 2 | 3 | 4; cardStyle: FeaturesProps["cardStyle"] }) {
  return (
    <Grid columns={columns}>
      {items.map((item) => (
        <Card key={item.title} className={cardClass(cardStyle)}>
          <CardHeader>
            {item.icon && (
              <div className="mb-2 text-primary">
                <Icon icon={item.icon} framed />
              </div>
            )}
            <CardTitle>{item.title}</CardTitle>
            {item.body && <CardDescription>{item.body}</CardDescription>}
          </CardHeader>
        </Card>
      ))}
    </Grid>
  );
}

/** Numbered rows: a large numeral in the accent colour (or the item's icon, Story 20.5), then the title and text. */
function NumberedList({ items }: { items: TItem[] }) {
  return (
    <ol className="grid gap-x-12 gap-y-8 md:grid-cols-2">
      {items.map((item, index) => (
        <li key={item.title} className="flex gap-5">
          {item.icon ? (
            <span className="pt-0.5 text-2xl text-primary">
              <Icon icon={item.icon} framed className="size-[0.85em]" />
            </span>
          ) : (
            <span aria-hidden className="font-heading text-2xl font-semibold text-primary tabular-nums">
              {number(index)}
            </span>
          )}
          <div className="flex flex-col gap-1">
            <h3 className="text-lg font-semibold">{item.title}</h3>
            {item.body && <p className="max-w-prose text-muted-foreground">{item.body}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}

/** Hairline-separated rows, title on the left and text on the right, like a specification sheet. */
function Ledger({ items }: { items: TItem[] }) {
  return (
    <dl className="border-b border-border">
      {items.map((item) => (
        <div key={item.title} className="grid gap-2 border-t border-border py-6 md:grid-cols-[1fr_2fr] md:gap-12">
          <dt className="flex items-center gap-3 text-lg font-semibold">
            {item.icon && (
              <span className="text-primary">
                <Icon icon={item.icon} />
              </span>
            )}
            {item.title}
          </dt>
          <dd className="max-w-prose text-muted-foreground">{item.body}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Rows of image and text, the image switching sides from one row to the next (from 768 px). */
function Alternating({ items }: { items: TItem[] }) {
  return (
    <div className="flex flex-col gap-12 md:gap-16">
      {items.map((item, index) => (
        <div key={item.title} className="grid items-center gap-6 md:grid-cols-2 md:gap-12">
          {item.image && <AssetImage asset={item.image} className={cn(index % 2 === 1 && "md:order-last")} />}
          <div className="flex flex-col gap-2">
            <h3 className="text-2xl font-semibold tracking-tight">{item.title}</h3>
            {item.body && <p className="max-w-prose text-muted-foreground">{item.body}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * What a business offers, in four forms (Stories 17.7, 20.2): `cards` (a grid), `list` (numbered rows), `ledger`
 * (hairline rows) and `alternating` (image and text rows; without item images it shows as `list`). Items may carry an
 * icon in the site's set (Story 20.5): above a card's title, in place of the numeral, before a ledger title.
 */
export function Features(props: FeaturesProps) {
  const { title, description, items = [], columns = 3, cardStyle, form = "cards", background, backgroundImage } = props;
  const shown = form === "alternating" && !items.some((item) => item.image) ? "list" : form;
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      {shown === "list" && <NumberedList items={items} />}
      {shown === "ledger" && <Ledger items={items} />}
      {shown === "alternating" && <Alternating items={items} />}
      {shown === "cards" && <Cards items={items} columns={columns} cardStyle={cardStyle} />}
    </Section>
  );
}
