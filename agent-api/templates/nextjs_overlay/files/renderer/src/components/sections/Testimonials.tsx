import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TTestimonialsContent } from "./types";

type TestimonialsProps = TTestimonialsContent;

export function Testimonials(props: TestimonialsProps) {
  const { title = "What clients say", items = [], cardStyle, background, backgroundImage } = props;
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      <Grid columns={items.length > 1 ? 2 : 1}>
        {items.map((item) => (
          <Card key={`${item.author}-${item.quote.slice(0, 20)}`} className={cardClass(cardStyle)}>
            <CardContent className="flex flex-col gap-4">
              <blockquote className="max-w-prose text-lg">&ldquo;{item.quote}&rdquo;</blockquote>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Avatar>
                  <AvatarFallback>{item.author.slice(0, 1)}</AvatarFallback>
                </Avatar>
                <span>
                  {item.author}
                  {item.role && <span className="block">{item.role}</span>}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
