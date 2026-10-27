import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { AssetImage } from "./AssetImage";

export type TGalleryItem = { title: string; image: string };

type GalleryProps = {
  items: TGalleryItem[];
};

export function Gallery({ items }: GalleryProps) {
  return (
    <Section title="Selected work">
      <Grid columns={2}>
        {items.map((item) => (
          <figure key={item.title} className="flex flex-col gap-3">
            <AssetImage asset={item.image} />
            <figcaption className="font-medium">{item.title}</figcaption>
          </figure>
        ))}
      </Grid>
    </Section>
  );
}
