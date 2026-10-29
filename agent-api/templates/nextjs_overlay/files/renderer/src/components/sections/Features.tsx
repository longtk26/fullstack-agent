import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TFeaturesContent } from "./types";

type FeaturesProps = TFeaturesContent;

export function Features({ title, description, items = [], columns = 3 }: FeaturesProps) {
  return (
    <Section title={title} description={description}>
      <Grid columns={columns}>
        {items.map((item) => (
          <Card key={item.title}>
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
              {item.body && <CardDescription>{item.body}</CardDescription>}
            </CardHeader>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
