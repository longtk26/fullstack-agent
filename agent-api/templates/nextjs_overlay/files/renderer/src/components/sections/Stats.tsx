import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TStatsContent } from "./types";

type StatsProps = TStatsContent;

export function Stats({ title, items = [], cardStyle, background, backgroundImage }: StatsProps) {
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      <Grid columns={items.length >= 4 ? 4 : items.length === 3 ? 3 : 2}>
        {items.map((item) => (
          <Card key={item.label} className={cardClass(cardStyle)}>
            <CardContent className="flex flex-col gap-1">
              <span className="font-heading text-2xl font-semibold">{item.value}</span>
              <span className="text-sm text-muted-foreground">{item.label}</span>
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
