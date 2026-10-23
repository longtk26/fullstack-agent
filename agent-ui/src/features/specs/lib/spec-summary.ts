export type TEntitySummary = { name: string; fieldCount: number; relationshipCount: number };
export type TOperationSummary = { method: string; path: string; operationId: string };
export type TSpecSummary = {
  projectName: string | null;
  entities: TEntitySummary[];
  operations: TOperationSummary[];
};

type TLoose = Record<string, unknown>;

function asArray(value: unknown): TLoose[] {
  return Array.isArray(value) ? value.filter((item): item is TLoose => typeof item === "object" && item !== null) : [];
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

/** A tolerant read of a (possibly invalid) BackendSpec for the side panel; never throws. */
export function summarizeSpec(spec: unknown): TSpecSummary {
  const root = (typeof spec === "object" && spec !== null ? spec : {}) as TLoose;
  const project = (root.project ?? {}) as TLoose;
  const relationships = asArray(root.relationships);
  const entities = asArray(root.entities).map((entity) => {
    const name = asString(entity.name) ?? "?";
    return {
      name,
      fieldCount: asArray(entity.fields).length,
      relationshipCount: relationships.filter((rel) => rel.from === name || rel.to === name).length,
    };
  });
  const operations = asArray(root.operations).map((operation) => ({
    method: (asString(operation.method) ?? "?").toUpperCase(),
    path: asString(operation.path) ?? "?",
    operationId: asString(operation.operationId) ?? asString(operation.id) ?? "—",
  }));
  return { projectName: asString(project.name), entities, operations };
}
