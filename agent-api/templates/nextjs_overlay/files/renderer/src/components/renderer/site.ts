import data from "@/content/site.json";

export type TSiteSection = {
  id: string;
  component: string;
  content?: Record<string, unknown>;
  data?: { collection?: string; fields?: string[] };
  children?: TSiteSection[];
};

export type TSitePage = { title: string; sections: TSiteSection[] };

export type TSite = {
  pages: Record<string, TSitePage>;
  collections: Record<string, Record<string, unknown>[]>;
};

/** The FrontendSpec pages and content collections, validated when the spec was (Story 17.1). */
export const site = data as TSite;
