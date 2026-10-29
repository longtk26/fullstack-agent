import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import type { TStatsContent } from "./types";

type StatsProps = TStatsContent;

export function Stats({ title, items = [] }: StatsProps) {
  return (
    <Section title={title}>
      <Grid columns={items.length >= 4 ? 4 : items.length === 3 ? 3 : 2}>
        {items.map((item) => (
          <Card key={item.label}>
            <CardContent className="flex flex-col gap-1">
              <span className="text-3xl font-semibold">{item.value}</span>
              <span className="text-sm text-muted-foreground">{item.label}</span>
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
