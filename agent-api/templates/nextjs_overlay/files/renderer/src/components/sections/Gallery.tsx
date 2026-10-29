import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { AssetImage } from "./AssetImage";
import type { TGalleryContent } from "./types";

type GalleryProps = TGalleryContent;

export function Gallery({ title = "Selected work", items = [], columns = 2 }: GalleryProps) {
  return (
    <Section title={title}>
      <Grid columns={columns}>
        {items.map((item) => (
          <figure key={item.image + (item.title ?? "")} className="flex flex-col gap-3">
            <AssetImage asset={item.image} />
            {(item.title || item.caption) && (
              <figcaption className="flex flex-col gap-1">
                {item.title && <span className="font-medium">{item.title}</span>}
                {item.caption && <span className="text-sm text-muted-foreground">{item.caption}</span>}
              </figcaption>
            )}
          </figure>
        ))}
      </Grid>
    </Section>
  );
}
