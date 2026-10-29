import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AssetImage } from "./AssetImage";
import { formatValue, isImage, recordFields, recordKey, type TRecord } from "./records";
import type { TDataSectionContent } from "./types";

type CardGridProps = TDataSectionContent & {
  items?: TRecord[];
  fields?: string[];
};

/** Records of a content collection as cards: images first, the first text field as the title. */
export function CardGrid({ title, description, items = [], fields }: CardGridProps) {
  const shown = recordFields(items, fields);
  const images = shown.filter((field) => isImage(items[0]?.[field]));
  const [heading, ...rest] = shown.filter((field) => !images.includes(field));
  return (
    <Section title={title} description={description}>
      <Grid columns={3}>
        {items.map((record, index) => (
          <Card key={recordKey(record, index)}>
            {images.map((field) => isImage(record[field]) && <AssetImage key={field} asset={record[field]} />)}
            <CardHeader>{heading && <CardTitle>{formatValue(record[heading])}</CardTitle>}</CardHeader>
            {rest.length > 0 && (
              <CardContent className="flex flex-col gap-1 text-sm text-muted-foreground">
                {rest.map((field) => (
                  <span key={field}>{formatValue(record[field])}</span>
                ))}
              </CardContent>
            )}
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
