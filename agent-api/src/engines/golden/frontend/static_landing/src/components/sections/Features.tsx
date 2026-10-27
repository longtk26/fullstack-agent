import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export type TFeature = { title: string; body: string };

type FeaturesProps = {
  items: TFeature[];
  title?: string;
};

export function Features({ items, title = "What we do" }: FeaturesProps) {
  return (
    <Section title={title}>
      <Grid columns={3}>
        {items.map((item) => (
          <Card key={item.title}>
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
              <CardDescription>{item.body}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
