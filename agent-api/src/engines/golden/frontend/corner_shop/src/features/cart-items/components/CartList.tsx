"use client";

import { QueryState } from "@/components/sections/QueryState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useCartList } from "@/features/cart-items/hooks/use-cart-list";

type CartListProps = {
  title?: string;
};

export function CartList({ title }: CartListProps) {
  const { items, isLoading, error, removeItem } = useCartList();
  return (
    <div className="flex flex-col gap-4">
      {title && <h2 className="text-lg font-semibold">{title}</h2>}
      <QueryState isLoading={isLoading} error={error} isEmpty={items.length === 0} emptyText="Your cart is empty">
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex items-center justify-between gap-4 py-4">
                <div>
                  <p className="font-medium">Product {item.productId}</p>
                  <p className="text-sm text-muted-foreground">Qty: {item.quantity}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => removeItem(item.id)}>
                  Remove
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </QueryState>
    </div>
  );
}
