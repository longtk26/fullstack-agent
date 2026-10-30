export type TIssueSeverity = "error" | "warning";

export type TSpecIssue = {
  code: string;
  path: string;
  message: string;
  hint: string | null;
  severity: TIssueSeverity;
  /** Consistency issues only: where the BackendSpec would have to change instead (JSON pointer). */
  backendPath?: string | null;
};

export type TValidationReport = {
  valid: boolean;
  specVersion: string | null;
  errors: TSpecIssue[];
  warnings: TSpecIssue[];
};

/**
 * `checked` is false when a spec is invalid (its own validation says why) or the FrontendSpec is static.
 * `contract` is the BackendSpec's API contract (OpenAPI 3.1) when checked, for the read-only preview.
 */
export type TSpecPairReport = TValidationReport & { checked: boolean; contract?: Record<string, unknown> | null };

export type TImportNote = {
  path: string;
  message: string;
  suggestion: string | null;
};

export type TFrontendBinding = {
  page?: string;
  component?: string;
  componentPath?: string;
  operationId?: string;
  params?: Record<string, unknown>;
  [key: string]: unknown;
};

export type TSeedBlock = {
  entity: string;
  records: Record<string, unknown>[];
};

export type TFrontendImportResult = {
  backendSpec: Record<string, unknown>;
  seed: TSeedBlock[];
  assumptions: TImportNote[];
  unresolved: TImportNote[];
  bindings: TFrontendBinding[];
  validation: TValidationReport;
};

export type TExampleFile = { name: string; path: string };

export type TExampleIndex = {
  specs?: TExampleFile[];
  frontend?: TExampleFile[];
  "frontend-specs"?: TExampleFile[];
  requirements?: TExampleFile[];
};

export type TEngineInfo = {
  name: string;
  available: boolean;
  reason: string | null;
};

export type TEngineList = {
  default: string;
  engines: TEngineInfo[];
  reportedByWorker: boolean;
  reportedAt: string | null;
};

export type TSpecKind = "backend" | "frontend";

export type TSpecTab = "requirement" | "import" | "json" | "frontend" | "contract";

// -- Requirement drafting (Stories 2.4, 12.4) ---------------------------------------------------------------------

export type TDraftMode = "backend" | "static" | "dynamic";

export type TSpecDraftStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "NEEDS_REVIEW" | "FAILED";

export type TDraftNote = TImportNote & { spec: TSpecKind | null };

export type TCreateSpecDraftPayload = {
  mode: TDraftMode;
  requirementText: string;
  requirementFileName?: string | null;
  engine?: string | null;
};

export type TDraftUsage = {
  engineMs?: number;
  modelCalls?: number;
  inputTokens?: number;
  outputTokens?: number;
  costUsd?: number;
  unpriced?: number;
};

export type TSpecDraft = {
  draftId: string;
  status: TSpecDraftStatus;
  progress: string | null;
  source: "requirement" | "frontend";
  mode: TDraftMode;
  engine: string;
  attempts: number;
  requirement: { text: string | null; format: "text" | "markdown" | null; fileName: string | null };
  backendSpec: Record<string, unknown> | null;
  frontendSpec: Record<string, unknown> | null;
  assumptions: TDraftNote[];
  unresolved: TDraftNote[];
  validation: { backend: TValidationReport | null; frontend: TValidationReport | null; pair: TValidationReport | null };
  usage: TDraftUsage;
  error: string | null;
  createdAt: string | null;
  startedAt: string | null;
  finishedAt: string | null;
};
