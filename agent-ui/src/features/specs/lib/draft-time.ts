import { elapsedMs, formatDuration } from "@/lib/format-duration";
import type { TSpecDraft } from "../types";

/** The draft's total time, start to finish (the queue wait apart when it was noticeable): "15m 12s (+20s queued)". */
export function draftTotalTime(draft: TSpecDraft): string | null {
  const total = elapsedMs(draft.startedAt, draft.finishedAt, Date.now());
  if (total == null || !draft.finishedAt) return null;
  const queued = draft.createdAt && draft.startedAt ? Date.parse(draft.startedAt) - Date.parse(draft.createdAt) : 0;
  return `${formatDuration(total)}${queued >= 5000 ? ` (+${formatDuration(queued)} queued)` : ""}`;
}
