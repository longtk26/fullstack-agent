import { Suspense } from "react";
import { Container } from "@/components/layout/Container";
import { Stack } from "@/components/layout/Stack";
import { Skeleton } from "@/components/ui/skeleton";
import { NewGenerationView } from "@/features/generations/components/NewGenerationView";

export default function NewGenerationPage() {
  return (
    <Container size="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <h1 className="text-2xl font-semibold tracking-tight">New generation</h1>
          <p className="text-sm text-muted-foreground">
            Choose what to build, then give its spec. Submit unlocks once every spec is valid.
          </p>
        </Stack>
        {/* The mode comes from `?mode=` (useSearchParams), so the view renders on the client. */}
        <Suspense fallback={<Skeleton className="h-[640px] w-full rounded-xl" />}>
          <NewGenerationView />
        </Suspense>
      </Stack>
    </Container>
  );
}
