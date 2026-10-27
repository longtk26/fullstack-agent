import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";

export type TStat = { label: string; value: string };

type StatsProps = {
  items: TStat[];
};

export function Stats({ items }: StatsProps) {
  return (
    <Section>
      <Grid columns={2}>
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
