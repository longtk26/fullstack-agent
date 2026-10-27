import { Check } from "lucide-react";
import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type TPlan = { name: string; price: string; features: string[] };

type PricingProps = {
  plans: TPlan[];
};

export function Pricing({ plans }: PricingProps) {
  return (
    <Section title="Packages">
      <Grid columns={2}>
        {plans.map((plan) => (
          <Card key={plan.name}>
            <CardHeader>
              <CardTitle className="flex items-baseline justify-between">
                {plan.name}
                <span className="text-2xl">{plan.price}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2 text-sm">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check className="size-4 text-primary" aria-hidden />
                    {feature}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
