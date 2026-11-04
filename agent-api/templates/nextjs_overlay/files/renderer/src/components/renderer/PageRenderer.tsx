import { notFound } from "next/navigation";
import { MotionRoot } from "./MotionRoot";
import { site } from "./site";
import { SectionRenderer } from "./SectionRenderer";
import { TreeRenderer } from "./tree/TreeRenderer";

// Story 20.6: motion on only when JavaScript runs and the visitor has not asked for reduced motion; "off" if the page
// has not come alive within 3 s (MotionRoot sets data-motion-ready), so content is never left hidden.
const MOTION_SCRIPT =
  "(function(){var d=document.documentElement;try{if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;" +
  "d.dataset.motion='on';setTimeout(function(){if(!d.dataset.motionReady)d.dataset.motion='off'},3000)}catch(e){}})();";

type PageRendererProps = {
  pageId: string;
};

/**
 * A FrontendSpec page: its sections, in order (Story 17.2), or its designed tree (Epic 21) with the page's own
 * scoped CSS; with a motion feel (Story 20.6) the script and component that run it. No page-wide `<Suspense>`:
 * only a section with controls reads the URL, behind its own boundary, so the static export keeps every other
 * section in the HTML.
 */
export function PageRenderer({ pageId }: PageRendererProps) {
  const page = site.pages[pageId];
  if (!page) notFound();
  return (
    <>
      {site.motion && <script dangerouslySetInnerHTML={{ __html: MOTION_SCRIPT }} />}
      {page.tree ? (
        <div data-page={pageId} data-bga-section={`${pageId}/tree`} data-bga-component="Tree">
          {page.css && <style dangerouslySetInnerHTML={{ __html: page.css }} />}
          <TreeRenderer node={page.tree} pageId={pageId} />
        </div>
      ) : (
        page.sections.map((section, index) => (
          <SectionRenderer
            key={section.id}
            pageId={pageId}
            section={section}
            divider={page.rhythm === "dividers" && index > 0}
          />
        ))
      )}
      {site.motion && <MotionRoot />}
    </>
  );
}
