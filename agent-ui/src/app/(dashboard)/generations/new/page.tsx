import { Container } from "@/components/layout/Container";
import { Stack } from "@/components/layout/Stack";
import { NewGenerationView } from "@/features/generations/components/NewGenerationView";

export default function NewGenerationPage() {
  return (
    <Container size="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <h1 className="text-2xl font-semibold tracking-tight">New generation</h1>
          <p className="text-sm text-muted-foreground">
            Start from a requirement, a frontend site JSON or a BackendSpec. Submit unlocks once the spec is valid.
          </p>
        </Stack>
        <NewGenerationView />
      </Stack>
    </Container>
  );
}
