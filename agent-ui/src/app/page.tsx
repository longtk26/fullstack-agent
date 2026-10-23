import { Boxes } from "lucide-react";
import { Container } from "@/components/layout/Container";
import { Stack } from "@/components/layout/Stack";

export default function HomePage() {
  return (
    <Container size="md">
      <Stack
        gap="sm"
        align="center"
        className="rounded-xl border border-dashed border-border px-6 py-16 text-center"
      >
        <Boxes className="size-10 text-muted-foreground" />
        <h1 className="text-xl font-semibold">No generations yet</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          Submitting a requirement, a frontend site JSON or a BackendSpec arrives in Epic 9. The agent API is
          running behind this shell.
        </p>
      </Stack>
    </Container>
  );
}
