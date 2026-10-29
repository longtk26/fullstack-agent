"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useOperationMutation } from "@/components/renderer/bindings";
import type { TBinding, TColumn, TRecord, TStates } from "@/components/renderer/site";
import { useSectionRecords } from "@/components/renderer/use-section-records";
import { formatValue } from "@/components/sections/format";
import { QueryState } from "@/components/sections/QueryState";

type CartListProps = {
  title?: string;
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
};

/** Cart lines with their fields and a remove button (the list's delete operation). */
export default function CartList({ title, items, columns = [], binding, states }: CartListProps) {
  const { records, isLoading, error } = useSectionRecords(items, binding);
  const remove = useOperationMutation(binding?.operationId?.replace(/\.list$/, ".delete"));
  return (
    <div className="flex flex-col gap-4">
      {title && <h2 className="text-lg font-semibold">{title}</h2>}
      <QueryState
        isLoading={isLoading}
        error={error}
        isEmpty={records.length === 0}
        emptyText={states?.empty}
        errorText={states?.error}
      >
        <div className="flex flex-col gap-3">
          {records.map((record, index) => (
            <Card key={String(record.id ?? index)}>
              <CardContent className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-1 text-sm">
                  {columns.map((column) => (
                    <span key={column.key}>
                      <span className="text-muted-foreground">{column.label}: </span>
                      {formatValue(record[column.key], column.format)}
                    </span>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate({ params: { id: record.id }, body: {} })}
                >
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
