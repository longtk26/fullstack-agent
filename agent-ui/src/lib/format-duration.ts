/** Durations as people read them ("850 ms", "42s", "15m 12s", "1h 3m"); shared by generations and drafts. */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.max(0, Math.round(ms))} ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

/** From start to finish, or to `now` while it runs; null before it starts. */
export function elapsedMs(startedAt: string | null, finishedAt: string | null, now: number): number | null {
  if (!startedAt) return null;
  const end = finishedAt ? Date.parse(finishedAt) : now;
  return end - Date.parse(startedAt);
}
