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

export type TSectionAction = {
  id: string;
  label: string;
  kind: "link" | "mutation";
  page?: string;
  params?: Record<string, unknown>;
  operationId?: string;
  body?: Record<string, unknown>;
  confirm?: string | boolean;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  onSuccess?: { toast?: string; navigate?: string };
};

export type TSectionControls = {
  search?: boolean;
  filters?: string[];
  sort?: string[];
  pageSize?: number;
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

export type TFormLoad = {
  operationId: string;
  params: Record<string, unknown>;
};

export type TFormDef = {
  operationId?: string | null;
  load?: TFormLoad;
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

/** Story 20.2: `alternate` backgrounds are written into the sections' content by the generator; `dividers` draws a
 * hairline between sections (PageRenderer). */
export type TRhythm = "uniform" | "alternate" | "dividers";

/** Epic 21: where a tree's data component reads: a content collection, or an API operation (with `computed`, the
 * browser aggregates the list itself); `route` is a record's detail page. */
export type TTreeBinding = {
  collection?: string;
  operationId?: string;
  action?: string;
  params?: Record<string, unknown>;
  computed?: boolean;
  route?: string;
};

/** Epic 21: one node of a designed page, classified by the generator (`frontend_renderer.tree_site`). */
export type TTreeNode = {
  kind: "element" | "image" | "icon" | "link" | "primitive" | "section" | "data";
  type: string;
  props?: Record<string, unknown>;
  children?: (TTreeNode | string)[];
  asset?: string;
  icon?: string;
  id?: string;
  component?: string;
  content?: Record<string, unknown>;
  binding?: TTreeBinding;
  /** A library section node: its data binding, form and states, as a page section has them. */
  data?: TBinding;
  form?: string;
  states?: TStates;
};

export type TSitePage = { title: string; rhythm?: TRhythm; sections: TSiteSection[]; tree?: TTreeNode; css?: string };

/** Story 20.6: the theme's motion; absent for a still site. */
export type TMotion = {
  feel: "click" | "slide" | "flow" | "drop" | "bounce" | "float" | "cut";
  signature: "none" | "countUp" | "headlineRise" | "imageUnmask" | "indicator";
};

export type TSite = {
  pages: Record<string, TSitePage>;
  motion?: TMotion;
  /** Epic 21: designed chrome and footer, replacing the shell's own header and footer when present. */
  chrome?: TTreeNode;
  footerTree?: TTreeNode;
  collections: Record<string, TRecord[]>;
  forms: Record<string, TFormDef>;
};

/** The FrontendSpec pages, content collections and forms, validated when the spec was (Story 17.1). */
// Via unknown: a designed page's tree (Epic 21) is a deep union the JSON import infers differently from TTreeNode.
export const site = data as unknown as TSite;
