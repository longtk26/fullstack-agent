import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";

export type TTestimonial = { author: string; quote: string };

type TestimonialsProps = {
  items: TTestimonial[];
};

export function Testimonials({ items }: TestimonialsProps) {
  return (
    <Section title="What clients say">
      <Grid columns={items.length > 1 ? 2 : 1}>
        {items.map((item) => (
          <Card key={item.author}>
            <CardContent className="flex flex-col gap-4">
              <blockquote className="text-lg">&ldquo;{item.quote}&rdquo;</blockquote>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Avatar>
                  <AvatarFallback>{item.author.slice(0, 1)}</AvatarFallback>
                </Avatar>
                {item.author}
              </div>
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
