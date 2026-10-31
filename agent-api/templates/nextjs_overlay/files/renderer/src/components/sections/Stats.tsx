"use client";

import { useParams } from "next/navigation";
import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import { useOperationQuery } from "@/components/renderer/bindings";
import { resolveParams } from "@/components/renderer/use-section-records";
import { backdropImage } from "./AssetImage";
import { cardClass } from "./styles";
import type { TStatItem, TStatsContent } from "./types";

type StatsProps = TStatsContent;

function StatCard({ item, cardStyle }: { item: TStatItem; cardStyle?: "outline" | "filled" | "plain" }) {
  const route = (useParams() ?? {}) as Record<string, string | string[] | undefined>;
  const operationId = item.data?.operationId;
  const query = useOperationQuery(operationId, resolveParams({}, route));

  let displayValue: string | number = item.value ?? "";
  if (operationId) {
    if (query.isLoading) {
      displayValue = "…";
    } else if (query.data !== undefined) {
      const data = query.data;
      if (item.data?.value === "count") {
        if (typeof data === "object" && data !== null) {
          const obj = data as { total?: number; count?: number; items?: unknown[] };
          displayValue = obj.total ?? obj.count ?? (Array.isArray(obj.items) ? obj.items.length : 0);
        } else if (Array.isArray(data)) {
          displayValue = data.length;
        } else if (typeof data === "number") {
          displayValue = data;
        }
      } else if (item.data?.value && typeof data === "object" && data !== null) {
        displayValue = ((data as Record<string, unknown>)[item.data.value] as string | number) ?? "—";
      }
    }
  }

  return (
    <Card className={cardClass(cardStyle)}>
      <CardContent className="flex flex-col gap-1">
        <span className="font-heading text-2xl font-semibold">{displayValue}</span>
        <span className="text-sm text-muted-foreground">{item.label}</span>
      </CardContent>
    </Card>
  );
}

export function Stats({ title, items = [], cardStyle, background, backgroundImage }: StatsProps) {
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      <Grid columns={items.length >= 4 ? 4 : items.length === 3 ? 3 : 2}>
        {items.map((item, index) => (
          <StatCard key={`${item.label}-${index}`} item={item} cardStyle={cardStyle} />
        ))}
      </Grid>
    </Section>
  );
}
