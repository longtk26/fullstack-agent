import type { TFormField, TRecord } from "../app";

export { enumLabel } from "../app";

/** What every field component of the form kit takes (Story 22.5). */
export type TFieldProps = {
  field: TFormField;
  id: string;
  value: unknown;
  onChange: (value: unknown) => void;
  onBlur?: () => void;
  invalid: boolean;
  /** The record an edit form loaded (Story 22.7: its `allowedActions` and file URLs). */
  record?: TRecord;
};
