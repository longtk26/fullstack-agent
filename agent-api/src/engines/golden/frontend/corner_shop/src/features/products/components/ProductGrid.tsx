"use client";

import Link from "next/link";
import { Grid } from "@/components/layout/Grid";
import { QueryState } from "@/components/sections/QueryState";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useProductGrid } from "@/features/products/hooks/use-product-grid";

type ProductGridProps = {
  limit?: number;
};

export function ProductGrid({ limit = 12 }: ProductGridProps) {
  const { products, isLoading, error } = useProductGrid(limit);
  return (
    <QueryState
      isLoading={isLoading}
      error={error}
      isEmpty={products.length === 0}
      emptyText="No products yet"
      errorText="Could not load products"
    >
      <Grid columns={3}>
        {products.map((product) => (
          <Link key={product.id} href={`/products/${product.id}`}>
            <Card className="h-full transition-colors hover:bg-muted/40">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle>{product.name}</CardTitle>
                  <Badge variant="secondary">${Number(product.price).toFixed(2)}</Badge>
                </div>
              </CardHeader>
              {product.description && (
                <CardContent>
                  <p className="text-sm text-muted-foreground">{product.description}</p>
                </CardContent>
              )}
            </Card>
          </Link>
        ))}
      </Grid>
    </QueryState>
  );
}
