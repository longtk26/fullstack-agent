import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import type { TTestimonialsContent } from "./types";

type TestimonialsProps = TTestimonialsContent;

export function Testimonials({ title = "What clients say", items = [] }: TestimonialsProps) {
  return (
    <Section title={title}>
      <Grid columns={items.length > 1 ? 2 : 1}>
        {items.map((item) => (
          <Card key={`${item.author}-${item.quote.slice(0, 20)}`}>
            <CardContent className="flex flex-col gap-4">
              <blockquote className="text-lg">&ldquo;{item.quote}&rdquo;</blockquote>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Avatar>
                  <AvatarFallback>{item.author.slice(0, 1)}</AvatarFallback>
                </Avatar>
                <span>
                  {item.author}
                  {item.role && <span className="block text-xs">{item.role}</span>}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
