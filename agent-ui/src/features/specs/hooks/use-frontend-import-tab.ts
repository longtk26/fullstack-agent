"use client";

import { useState } from "react";
import { toast } from "sonner";
import { pickFile, prettyJson } from "@/lib/files";
import { useSpecDraftStore } from "@/store/spec-draft-store";
import { fetchExampleText } from "../api/specs-api";
import { useExampleIndex, useFrontendImport } from "./use-spec-queries";

export function useFrontendImportTab() {
  const [siteText, setSiteText] = useState<string | null>(null);
  const [sourceName, setSourceName] = useState<string | null>(null);
  const [includeAdminCrud, setIncludeAdminCrud] = useState(true);
  const [acknowledged, setAcknowledged] = useState(false);
  const setSpecText = useSpecDraftStore((state) => state.setSpecText);
  const setActiveTab = useSpecDraftStore((state) => state.setActiveTab);
  const { data: examples } = useExampleIndex();
  const conversion = useFrontendImport();

  const convert = (raw: string, adminCrud: boolean) => {
    setAcknowledged(false);
    conversion.mutate({ raw, includeAdminCrud: adminCrud });
  };

  const loadSite = (raw: string, name: string) => {
    setSiteText(raw);
    setSourceName(name);
    convert(raw, includeAdminCrud);
  };

  const sample = examples?.frontend?.[0];
  const result = conversion.data;
  const needsAcknowledgement = Boolean(result && (result.assumptions.length || result.unresolved.length));

  return {
    sourceName,
    includeAdminCrud,
    acknowledged,
    setAcknowledged,
    conversion,
    result,
    needsAcknowledgement,
    hasSample: Boolean(sample),
    loadFile: async (file: File | null) => {
      if (file) loadSite(await file.text(), file.name);
    },
    upload: async () => {
      const file = await pickFile("application/json,.json");
      if (file) loadSite(await file.text(), file.name);
    },
    loadSample: async () => {
      if (!sample) return;
      try {
        loadSite(await fetchExampleText(sample.path), `${sample.name}.json`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not load the sample");
      }
    },
    toggleAdminCrud: (value: boolean) => {
      setIncludeAdminCrud(value);
      if (siteText) convert(siteText, value);
    },
    editInJsonTab: () => {
      if (!result) return;
      setSpecText(prettyJson(result.backendSpec));
      setActiveTab("json");
    },
  };
}
