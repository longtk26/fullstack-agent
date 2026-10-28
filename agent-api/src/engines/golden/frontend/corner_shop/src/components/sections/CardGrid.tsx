import Link from "next/link";
import { Grid } from "@/components/layout/Grid";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export type TCardItem = { key: string; title: string; description?: string | null; href?: string };

type CardGridProps = {
  items: TCardItem[];
};

/** Records as cards (title, description, optional link). */
export function CardGrid({ items }: CardGridProps) {
  return (
    <Grid columns={3}>
      {items.map((item) => {
        const card = (
          <Card className="h-full transition-colors hover:bg-muted/40">
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
              {item.description && <CardDescription>{item.description}</CardDescription>}
            </CardHeader>
          </Card>
        );
        return item.href ? (
          <Link key={item.key} href={item.href}>
            {card}
          </Link>
        ) : (
          <div key={item.key}>{card}</div>
        );
      })}
    </Grid>
  );
}
