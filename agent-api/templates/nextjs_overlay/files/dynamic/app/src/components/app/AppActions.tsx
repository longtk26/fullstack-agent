"use client";

import type { TAppSection } from "./app";
import { ActionButtons } from "./RecordActions";

/** Operations on a whole collection (Story 22.3: a custom operation without a record), as buttons; a body opens its
 *  form in a dialog, a confirm asks first. */
export function AppActions({ section }: { section: TAppSection }) {
  return <ActionButtons actions={section.content?.actions ?? []} />;
}
