export type TGenerationStatus = "PENDING" | "RUNNING" | "VALIDATING" | "REPAIRING" | "COMPLETED" | "FAILED" | "CANCELLED";

export type TEngineName = "claude_code" | "antigravity" | "fake";

export type TGenerationOptions = {
  maxRepairAttempts: number;
  runTests: boolean;
  generateDockerfile: boolean;
  deployPreview: boolean;
  engine?: TEngineName | null;
  timeoutSeconds?: number | null;
};

export type TGeneration = {
  generationId: string;
  projectName: string | null;
  status: TGenerationStatus;
  currentStep: string | null;
  engine: string;
  repairAttempts: number;
  createdAt: string | null;
  startedAt: string | null;
  finishedAt: string | null;
};

export type TGenerationPage = {
  items: TGeneration[];
  nextCursor: string | null;
};

export type TEngineInvocation = {
  id: string;
  nodeRunId: string | null;
  engine: string;
  purpose: string;
  status: string;
  exitCode: number | null;
  durationMs: number | null;
  turns: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  costUsd: number | null;
  createdAt: string | null;
};

export type TStepRunStatus = "running" | "succeeded" | "failed" | "skipped" | "cancelled" | "abandoned";

export type TStepRun = {
  id: string;
  node: string;
  attempt: number;
  status: TStepRunStatus;
  summary: Record<string, unknown>;
  startedAt: string | null;
  finishedAt: string | null;
  invocations: TEngineInvocation[];
};

export type TUsageTotals = {
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
};

export type TGenerationDetail = TGeneration & {
  specId: string;
  options: TGenerationOptions;
  resumeCount: number;
  cancelRequested: boolean;
  validation: Record<string, string>;
  steps: TStepRun[];
  usage: TUsageTotals;
  trace: { traceId: string | null; langsmithUrl: string | null };
  error: string | null;
};

export type TCreateGenerationPayload = {
  backendSpec?: unknown;
  specId?: string;
  options: TGenerationOptions;
};

export type TCreateGenerationResult = {
  generationId: string;
  status: TGenerationStatus;
  createdAt: string | null;
};

export type TGenerationEventType =
  | "status.changed"
  | "job.started"
  | "job.resumed"
  | "step.started"
  | "step.finished"
  | "engine.started"
  | "engine.event"
  | "engine.finished"
  | "engine.retry"
  | (string & {});

export type TGenerationEvent = {
  id: number;
  ts: string | null;
  generationId: string;
  type: TGenerationEventType;
  step: string | null;
  status: string | null;
  payload: Record<string, unknown>;
};

export type TWorkflowGraph = {
  nodes: { id: string; label: string; status?: string }[];
  edges: { source: string; target: string; conditional: boolean; label: string | null }[];
};

export type TListFilters = {
  status?: TGenerationStatus;
  cursor?: string;
};

export type TDetailTab = "steps" | "trace" | "results" | "api";
