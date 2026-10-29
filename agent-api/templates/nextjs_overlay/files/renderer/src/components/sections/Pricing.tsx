import { Check } from "lucide-react";
import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CtaLink } from "./CtaLink";
import type { TPricingContent } from "./types";

type PricingProps = TPricingContent;

export function Pricing({ title = "Packages", description, items = [] }: PricingProps) {
  return (
    <Section title={title} description={description}>
      <Grid columns={items.length >= 3 ? 3 : 2}>
        {items.map((plan) => (
          <Card key={plan.name} className={cn(plan.highlighted && "ring-2 ring-primary")}>
            <CardHeader>
              <CardTitle className="flex items-baseline justify-between gap-2">
                <span className="flex items-center gap-2">
                  {plan.name}
                  {plan.highlighted && <Badge>Popular</Badge>}
                </span>
                <span className="text-2xl">{plan.price}</span>
              </CardTitle>
              {plan.description && <CardDescription>{plan.description}</CardDescription>}
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <ul className="flex flex-col gap-2 text-sm">
                {(plan.features ?? []).map((feature) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check className="size-4 text-primary" aria-hidden />
                    {feature}
                  </li>
                ))}
              </ul>
              {plan.cta && <CtaLink cta={plan.cta} variant={plan.highlighted ? "default" : "outline"} />}
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
