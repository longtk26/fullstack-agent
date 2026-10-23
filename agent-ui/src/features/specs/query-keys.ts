export const specKeys = {
  all: ["specs"] as const,
  schema: () => [...specKeys.all, "schema"] as const,
  validation: (text: string) => [...specKeys.all, "validation", text] as const,
  examples: () => [...specKeys.all, "examples"] as const,
  engines: () => ["engines"] as const,
};
