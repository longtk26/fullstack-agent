/** Helpers for React Hook Form + the generated Zod schemas in `@/lib/forms`. */

/** `register(name, { setValueAs: toNumber })` for number inputs: empty → undefined, otherwise a number. */
export function toNumber(value: unknown): number | undefined {
  if (value === "" || value === null || value === undefined) return undefined;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? undefined : parsed;
}

/** Drops empty strings and undefined before a request body is sent (optional fields stay absent). */
export function compactValues<TValues extends Record<string, unknown>>(values: TValues): Partial<TValues> {
  return Object.fromEntries(
    Object.entries(values).filter(([, value]) => value !== "" && value !== undefined),
  ) as Partial<TValues>;
}
