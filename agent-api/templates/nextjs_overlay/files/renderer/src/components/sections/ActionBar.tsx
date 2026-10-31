"use client";

import { Section } from "@/components/layout/Section";
import type { TSectionAction } from "@/components/renderer/site";
import { ActionButtons } from "./ActionButtons";
import type { TActionBarContent } from "./types";

type ActionBarProps = TActionBarContent & {
  actions?: TSectionAction[];
};

/** A bar of action buttons for operations not tied to a single listed record. */
export function ActionBar({ title, description, actions = [] }: ActionBarProps) {
  if (!actions.length) return null;
  return (
    <Section title={title} description={description}>
      <ActionButtons actions={actions} className="flex flex-wrap items-center gap-3" />
    </Section>
  );
}
