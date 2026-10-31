import { Suspense } from "react";
import { notFound } from "next/navigation";
import { site } from "./site";
import { SectionRenderer } from "./SectionRenderer";

type PageRendererProps = {
  pageId: string;
};

/** A FrontendSpec page: its sections, in order (Story 17.2). */
export function PageRenderer({ pageId }: PageRendererProps) {
  const page = site.pages[pageId];
  if (!page) notFound();
  return (
    <Suspense fallback={null}>
      {page.sections.map((section) => (
        <SectionRenderer key={section.id} pageId={pageId} section={section} />
      ))}
    </Suspense>
  );
}
