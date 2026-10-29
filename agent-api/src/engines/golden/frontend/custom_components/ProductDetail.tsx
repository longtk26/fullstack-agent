"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { TBinding, TColumn, TStates } from "@/components/renderer/site";
import { useSectionRecords } from "@/components/renderer/use-section-records";
import { AssetImage } from "@/components/sections/AssetImage";
import { formatValue } from "@/components/sections/format";
import { QueryState } from "@/components/sections/QueryState";

type ProductDetailProps = {
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** One product: its image, its name as the title and the other fields as labelled rows. */
export default function ProductDetail({ columns = [], binding, states }: ProductDetailProps) {
  const { record, isLoading, error } = useSectionRecords(undefined, binding);
  const images = columns.filter((column) => column.format === "image");
  const [name, ...details] = columns.filter((column) => column.format !== "image");
  return (
    <QueryState isLoading={isLoading} error={error} isEmpty={!record} emptyText={states?.empty} errorText={states?.error}>
      {record && (
        <Card>
          {images.map((column) => (
            <AssetImage key={column.key} asset={String(record[column.key] ?? "")} />
          ))}
          <CardHeader>
            {name && <CardTitle className="text-2xl">{formatValue(record[name.key], name.format)}</CardTitle>}
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Separator />
            {details.map((column) => (
              <div key={column.key} className="flex justify-between gap-4 text-sm">
                <span className="text-muted-foreground">{column.label}</span>
                <span>{formatValue(record[column.key], column.format)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </QueryState>
  );
}
