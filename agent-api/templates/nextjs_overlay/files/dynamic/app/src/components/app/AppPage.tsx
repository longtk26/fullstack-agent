"use client";

import { notFound, usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { app, canUse, pageOperation, type TAppSection } from "./app";
import { AppSection } from "./AppSection";
import { useSession } from "./plugins";

type AppPageProps = {
  pageId: string;
};

type TBlock =
  | { kind: "one"; section: TAppSection }
  | { kind: "figures"; sections: TAppSection[] }
  | { kind: "tabs"; sections: TAppSection[] };

/** Consecutive dashboard items share a grid; consecutive tab sections (a parent's children) share one set of tabs. */
function blocks(sections: TAppSection[]): TBlock[] {
  const out: TBlock[] = [];
  for (const section of sections) {
    const last = out[out.length - 1];
    const kind = section.content?.tab ? "tabs" : section.component === "AppDashboard" ? "figures" : "one";
    if (kind !== "one" && last?.kind === kind) last.sections.push(section);
    else out.push(kind === "one" ? { kind, section } : { kind, sections: [section] });
  }
  return out;
}

/** One screen of the app (Epic 22): its app sections in the kit's one layout: one page width, one gap, the first
 *  list or the record as the page heading, figures in a grid, a parent's children in tabs. */
export function AppPage({ pageId }: AppPageProps) {
  const page = app.pages[pageId];
  const session = useSession();
  const router = useRouter();
  const pathname = usePathname();
  // Story 22.7: a page on an operation behind sign-in sends a signed-out user to sign in, and back here after
  const operation = pageOperation(pageId);
  const signedOut = session.enabled && session.ready && !session.user && Boolean(operation && app.access?.[operation]);
  useEffect(() => {
    if (signedOut && app.auth) router.replace(`${app.auth.signIn}?next=${encodeURIComponent(pathname)}`);
  }, [signedOut, router, pathname]);
  if (!page) notFound();
  if (session.enabled && (!session.ready || signedOut)) return null;
  if (session.enabled && operation && !canUse(operation, session)) {
    return (
      <Empty className="mx-auto max-w-md">
        <EmptyHeader>
          <EmptyTitle>Not for your role</EmptyTitle>
          <EmptyDescription>Your account cannot open {page.title.toLowerCase()}.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  const firstList = page.sections.find((s) => s.component === "AppList" && !s.content?.tab && s.content?.variant !== "recent");
  const hasHeading = page.sections.some((s) => s.component === "AppDetail" || s.component === "AppForm") || Boolean(firstList);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8" data-page={pageId}>
      {!hasHeading && <h1 className="text-2xl font-semibold tracking-tight">{page.title}</h1>}
      {blocks(page.sections).map((block, index) => {
        if (block.kind === "one") {
          const section = block.section;
          return (
            <AppSection
              key={section.id}
              pageId={pageId}
              section={section}
              title={page.title}
              heading={section === firstList ? "h1" : "h2"}
            />
          );
        }
        if (block.kind === "figures") {
          return (
            <div key={`figures-${index}`} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {block.sections.map((section) => (
                <div
                  key={section.id}
                  className={cn((section.content?.kind ?? "figure") !== "figure" && "sm:col-span-2")}
                >
                  <AppSection pageId={pageId} section={section} title={page.title} heading="h2" />
                </div>
              ))}
            </div>
          );
        }
        if (block.sections.length === 1) {
          const section = block.sections[0];
          return <AppSection key={section.id} pageId={pageId} section={section} title={page.title} heading="h2" />;
        }
        return (
          <Tabs key={`tabs-${index}`} defaultValue={block.sections[0].id} className="gap-4">
            <TabsList>
              {block.sections.map((section) => (
                <TabsTrigger key={section.id} value={section.id}>
                  {section.content?.tab}
                </TabsTrigger>
              ))}
            </TabsList>
            {block.sections.map((section) => (
              <TabsContent key={section.id} value={section.id}>
                <AppSection pageId={pageId} section={section} title={page.title} heading="h2" hideTitle />
              </TabsContent>
            ))}
          </Tabs>
        );
      })}
    </div>
  );
}
