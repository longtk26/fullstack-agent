"use client";

import type { TAppSection } from "./app";
import { AppActions } from "./AppActions";
import { AppDashboard } from "./AppDashboard";
import { AppDetail } from "./AppDetail";
import { AppForm } from "./AppForm";
import { AppList } from "./AppList";

type AppSectionProps = {
  pageId: string;
  section: TAppSection;
  title: string;
  /** The first list of a page is its heading (h1); a tab's or a dashboard's list is a sub-heading. */
  heading: "h1" | "h2";
  /** In a set of tabs the tab names the list; its heading stays for screen readers. */
  hideTitle?: boolean;
};

/** An app section by its component name; the markers let checks find it on the page. */
export function AppSection({ pageId, section, title, heading, hideTitle }: AppSectionProps) {
  let body = null;
  switch (section.component) {
    case "AppList":
      body = <AppList section={section} heading={heading} pageId={pageId} hideTitle={hideTitle} />;
      break;
    case "AppDetail":
      body = <AppDetail section={section} />;
      break;
    case "AppForm":
      body = <AppForm section={section} title={title} />;
      break;
    case "AppDashboard":
      body = <AppDashboard section={section} />;
      break;
    case "AppActions":
      body = <AppActions section={section} />;
      break;
  }
  return (
    <section data-bga-section={`${pageId}/${section.id}`} data-bga-component={section.component} className="min-w-0">
      {body}
    </section>
  );
}
