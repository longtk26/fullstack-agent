import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TFeaturesContent } from "./types";

type FeaturesProps = TFeaturesContent;

export function Features(props: FeaturesProps) {
  const { title, description, items = [], columns = 3, cardStyle, background, backgroundImage } = props;
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      <Grid columns={columns}>
        {items.map((item) => (
          <Card key={item.title} className={cardClass(cardStyle)}>
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
