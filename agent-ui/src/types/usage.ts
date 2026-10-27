/** Usage rollups shared by the Trace tab (Story 9.4) and the Usage & traces page (9.10); see Story 8.4. */

export type TTokenCounts = {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  thinking: number;
};

/** `reported` comes from the CLI (Claude Code), `estimated` is tokens × price (Antigravity). */
export type TCostSplit = {
  reported: number;
  estimated: number;
  total: number;
  unpriced: number;
};

export type TUsageBucket = {
  engineMs: number;
  sandboxMs: number;
  engineCalls: number;
  modelCalls: number;
  tokens: TTokenCounts;
  cost: TCostSplit;
};

export type TNodeUsage = TUsageBucket & {
  node: string;
  attempts: number;
  durationMs: number;
};

export type TLaneUsage = TUsageBucket & { lane: string; wallMs: number };

export type TModelUsage = Omit<TUsageBucket, "engineMs" | "sandboxMs"> & { model: string };

export type TUsageRollup = TUsageBucket & {
  wallMs: number;
  byNode: TNodeUsage[];
  byLane: TLaneUsage[];
  byModel: TModelUsage[];
};
