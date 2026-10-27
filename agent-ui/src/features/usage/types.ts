import type { TCostSplit, TModelUsage, TTokenCounts } from "@/types/usage";
import type { TEngineName, TGenerationStatus } from "@/features/generations/types";

export type TUsagePeriod = "7d" | "30d" | "90d";
export type TUsageScope = "mine" | "all";

type TGroupTotals = {
  generations: number;
  completed: number;
  wallMs: number;
  modelCalls: number;
  cost: TCostSplit;
  avgWallMs: number;
  avgCost: number;
};

export type TUsageDay = {
  date: string;
  generations: number;
  wallMs: number;
  modelCalls: number;
  cost: TCostSplit;
};

export type TUsageNode = {
  node: string;
  runs: number;
  generations: number;
  durationMs: number;
  engineMs: number;
  sandboxMs: number;
  modelCalls: number;
  cost: TCostSplit;
  avgDurationMs: number;
  avgCost: number;
};

export type TUsageGeneration = {
  generationId: string;
  projectName: string | null;
  mode: string;
  engine: TEngineName;
  status: TGenerationStatus;
  repairAttempts: number;
  createdAt: string | null;
  wallMs: number | null;
  modelCalls: number;
  tokens: TTokenCounts;
  cost: TCostSplit;
  langsmithUrl: string | null;
};

export type TUsageReport = {
  from: string;
  to: string;
  truncated: boolean;
  totals: {
    generations: number;
    completed: number;
    failed: number;
    successRate: number | null;
    wallMs: number;
    engineMs: number;
    sandboxMs: number;
    modelCalls: number;
    tokens: TTokenCounts;
    cost: TCostSplit;
    avgCostPerCompleted: number | null;
    avgWallMsPerCompleted: number | null;
  };
  byDay: TUsageDay[];
  byEngine: (TGroupTotals & { engine: string })[];
  byMode: (TGroupTotals & { mode: string })[];
  byModel: TModelUsage[];
  byNode: TUsageNode[];
  byLane: { lane: string; wallMs: number; modelCalls: number; cost: TCostSplit }[];
  generations: TUsageGeneration[];
};

export type TBreakdownDimension = "engine" | "model" | "node" | "lane";
export type TBreakdownMetric = "cost" | "time";

export type TBreakdownRow = {
  label: string;
  cost: number;
  estimated: boolean;
  timeMs: number | null;
  modelCalls: number;
};

export type TGenerationSortKey = "createdAt" | "wallMs" | "modelCalls" | "tokens" | "cost";

export type TGenerationFilters = {
  engine: string;
  mode: string;
  status: string;
};
