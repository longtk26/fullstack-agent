export type TIssueSeverity = "error" | "warning";

export type TSpecIssue = {
  code: string;
  path: string;
  message: string;
  hint: string | null;
  severity: TIssueSeverity;
};

export type TValidationReport = {
  valid: boolean;
  specVersion: string | null;
  errors: TSpecIssue[];
  warnings: TSpecIssue[];
};

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

export type TSpecTab = "requirement" | "import" | "json";
