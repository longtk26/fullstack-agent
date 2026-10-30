import data from "@/content/site.json";
import type { TValueFormat } from "@/components/sections/format";

export type TRecord = Record<string, unknown>;

export type TColumn = { key: string; label: string; format?: TValueFormat };

/** A link from a record to the page that shows it: `params` maps the route's parameters to record fields. */
export type TRecordLink = { route: string; params: Record<string, string> };

/** Where a data section's records come from: a content collection (static) or an API operation (dynamic). */
export type TBinding = {
  collection?: string;
  operationId?: string;
  action?: string;
  params?: Record<string, unknown>;
  columns?: TColumn[];
  link?: TRecordLink;
};

export type TStates = { loading?: string; empty?: string; error?: string; emptyImage?: string };

export type TFormFieldDef = {
  name: string;
  type: string;
  label: string;
  required?: boolean;
  hidden?: boolean;
  value?: unknown;
  values?: string[];
  placeholder?: string;
};

export type TFormDef = {
  operationId?: string | null;
  params: Record<string, unknown>;
  fields: TFormFieldDef[];
  submitLabel: string;
  onSuccess: { toast?: string; navigate?: string };
};

export type TSiteSection = {
  id: string;
  component: string;
  content?: Record<string, unknown>;
  data?: TBinding;
  states?: TStates;
  form?: string;
  children?: TSiteSection[];
};

export type TSitePage = { title: string; sections: TSiteSection[] };

export type TSite = {
  pages: Record<string, TSitePage>;
  collections: Record<string, TRecord[]>;
  forms: Record<string, TFormDef>;
};

/** The FrontendSpec pages, content collections and forms, validated when the spec was (Story 17.1). */
export const site = data as TSite;
