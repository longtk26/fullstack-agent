"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight, ListChecks, Plus } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Stack } from "@/components/layout/Stack";
import { useGenerationsList, type TStatusFilter } from "../hooks/use-generations-list";
import { GENERATION_STATUSES } from "../lib/status";
import { GenerationsTable } from "./GenerationsTable";

const STATUS_OPTIONS: { value: TStatusFilter; label: string }[] = [
  { value: "ALL", label: "All statuses" },
  ...GENERATION_STATUSES.map((status) => ({ value: status, label: status.toLowerCase() })),
];

export function GenerationsList() {
  const { query, status, page, changeStatus, hasPrevious, hasNext, previous, next } = useGenerationsList();
  const items = query.data?.items ?? [];

  return (
    <Stack gap="md">
      <Stack direction="row" justify="between" align="center" wrap className="gap-y-3">
        <Select items={STATUS_OPTIONS} value={status} onValueChange={(value) => changeStatus(value as TStatusFilter)}>
          <SelectTrigger className="w-44" aria-label="Filter by status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Stack direction="row" gap="xs" align="center">
          <span className="text-sm text-muted-foreground">Page {page}</span>
          <Button variant="outline" size="icon-sm" onClick={previous} disabled={!hasPrevious} aria-label="Previous page">
            <ChevronLeft />
          </Button>
          <Button variant="outline" size="icon-sm" onClick={next} disabled={!hasNext} aria-label="Next page">
            <ChevronRight />
          </Button>
        </Stack>
      </Stack>

      {query.isError && (
        <Alert variant="destructive">
          <AlertTitle>Could not load generations</AlertTitle>
          <AlertDescription>{query.error.message}</AlertDescription>
        </Alert>
      )}

      <Card className="py-0">
        <CardContent className="px-0">
          {query.isPending ? (
            <Stack gap="sm" className="p-4">
              {Array.from({ length: 5 }, (_, index) => (
                <Skeleton key={index} className="h-8 w-full" />
              ))}
            </Stack>
          ) : items.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <ListChecks />
                </EmptyMedia>
                <EmptyTitle>{status === "ALL" ? "No generations yet" : "No generations with this status"}</EmptyTitle>
                <EmptyDescription>
                  Start from a requirement, a frontend site JSON or a BackendSpec, then watch the workflow run.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button render={<Link href="/generations/new" />} nativeButton={false}>
                  <Plus /> New generation
                </Button>
              </EmptyContent>
            </Empty>
          ) : (
            <GenerationsTable items={items} />
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
