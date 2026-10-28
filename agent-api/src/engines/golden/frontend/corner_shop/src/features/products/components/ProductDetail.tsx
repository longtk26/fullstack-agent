"use client";

import { QueryState } from "@/components/sections/QueryState";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useProductDetail } from "@/features/products/hooks/use-product-detail";

type ProductDetailProps = {
  id: string;
};

export function ProductDetail({ id }: ProductDetailProps) {
  const { product, isLoading, error } = useProductDetail(id);
  return (
    <QueryState isLoading={isLoading} error={error} isEmpty={!product} errorText="Could not load the data">
      {product && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle className="text-2xl">{product.name}</CardTitle>
              <Badge>${Number(product.price).toFixed(2)}</Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {product.description && <p className="text-muted-foreground">{product.description}</p>}
            <Separator />
            <p className="text-sm text-muted-foreground">In stock: {product.stock ?? 0}</p>
          </CardContent>
        </Card>
      )}
    </QueryState>
  );
}
