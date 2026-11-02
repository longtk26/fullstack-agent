import { notFound } from "next/navigation";
import { site } from "./site";
import { SectionRenderer } from "./SectionRenderer";

type PageRendererProps = {
  pageId: string;
};

/**
 * A FrontendSpec page: its sections, in order (Story 17.2). No page-wide `<Suspense>`: only a section with controls
 * reads the URL, behind its own boundary, so the static export keeps every other section in the HTML.
 */
export function PageRenderer({ pageId }: PageRendererProps) {
  const page = site.pages[pageId];
  if (!page) notFound();
  return (
    <>
      {page.sections.map((section) => (
        <SectionRenderer key={section.id} pageId={pageId} section={section} />
      ))}
    </>
  );
}
