"use client";

import Link from "next/link";
import { Grid } from "@/components/layout/Grid";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TBinding, TColumn, TRecord, TStates } from "@/components/renderer/site";
import { recordHref, useSectionRecords } from "@/components/renderer/use-section-records";
import { AssetImage } from "@/components/sections/AssetImage";
import { formatValue } from "@/components/sections/format";
import { QueryState } from "@/components/sections/QueryState";

type ProductGridProps = {
  limit?: number;
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** Product cards: the image, the name and the other fields as badges; each card links to its product. */
export default function ProductGrid({ limit = 12, items, columns = [], binding, states }: ProductGridProps) {
  const { records, isLoading, error } = useSectionRecords(items, binding);
  const images = columns.filter((column) => column.format === "image");
  const [name, ...details] = columns.filter((column) => column.format !== "image");
  return (
    <QueryState
      isLoading={isLoading}
      error={error}
      isEmpty={records.length === 0}
      emptyText={states?.empty}
      errorText={states?.error}
    >
      <Grid columns={3}>
        {records.slice(0, limit).map((record, index) => (
          <Link key={String(record.id ?? index)} href={recordHref(binding?.link, record) ?? "#"}>
            <Card className="h-full transition-colors hover:bg-muted/40">
              {images.map((column) => (
                <AssetImage key={column.key} asset={String(record[column.key] ?? "")} />
              ))}
              <CardHeader>{name && <CardTitle>{formatValue(record[name.key], name.format)}</CardTitle>}</CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {details.map((column) => (
                  <Badge key={column.key} variant="secondary">
                    {formatValue(record[column.key], column.format)}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          </Link>
        ))}
      </Grid>
    </QueryState>
  );
}
