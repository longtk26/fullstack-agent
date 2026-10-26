"use client";

import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { Skeleton } from "@/components/ui/skeleton";
import "@scalar/api-reference-react/style.css";

// Scalar renders in the browser only (it mounts a Vue app).
const ApiReferenceReact = dynamic(
  () => import("@scalar/api-reference-react").then((module) => module.ApiReferenceReact),
  { ssr: false, loading: () => <Skeleton className="h-[720px] w-full" /> },
);

type ApiExplorerProps = {
  document: object;
  serverUrl: string | null;
  onRequestSent: () => void;
};

// Scalar offers hosted features on localhost (AI agent, toolbar, "Generate SDK" which uploads the document).
// Generated APIs stay local: those are switched off, and the SDK button, which has no switch, is hidden.
const LOCAL_ONLY_CSS = `.generate-sdk-button, button[aria-haspopup="dialog"].text-c-1 { display: none !important; }`;

/** OpenAPI reference + try-it. Requests go from the browser straight to the preview container (CORS allows the
 * UI origin); nothing is sent to Scalar's services (no telemetry, no hosted fonts, no proxy, no agent). */
export function ApiExplorer({ document, serverUrl, onRequestSent }: ApiExplorerProps) {
  const { resolvedTheme } = useTheme();
  const live = serverUrl !== null;
  return (
    <div className="overflow-hidden rounded-lg border">
      <ApiReferenceReact
        key={`${serverUrl ?? "offline"}-${resolvedTheme}`}
        configuration={{
          content: document,
          servers: live ? [{ url: serverUrl, description: "Preview container" }] : [],
          hideTestRequestButton: !live,
          hideClientButton: !live,
          showOperationId: true,
          telemetry: false,
          withDefaultFonts: false,
          persistAuth: false,
          hideDarkModeToggle: true,
          forceDarkModeState: resolvedTheme === "dark" ? "dark" : "light",
          documentDownloadType: "json",
          agent: { disabled: true },
          showDeveloperTools: "never",
          customCss: LOCAL_ONLY_CSS,
          onRequestSent: () => onRequestSent(),
        }}
      />
    </div>
  );
}
