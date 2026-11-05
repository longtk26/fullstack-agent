"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment } from "react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { app } from "./app";

/** The page whose route pattern matches a path (`/decks/3` → `/decks/[id]`). */
function pageFor(path: string): { title: string; route: string } | undefined {
  const parts = path.split("/").filter(Boolean);
  return Object.values(app.pages).find((page) => {
    const pattern = page.route.split("/").filter(Boolean);
    return pattern.length === parts.length && pattern.every((part, i) => part.startsWith("[") || part === parts[i]);
  });
}

/** Where the page is: each ancestor path that is a page of the app, as a link (a record's page by its section's
 *  title, since its name is loaded on the page itself). */
export function AppBreadcrumbs() {
  const pathname = usePathname() ?? "/";
  const parts = pathname.split("/").filter(Boolean);
  const trail = parts
    .map((_, index) => `/${parts.slice(0, index + 1).join("/")}`)
    .map((path) => ({ path, page: pageFor(path) }))
    .filter((item): item is { path: string; page: { title: string; route: string } } => Boolean(item.page));
  if (trail.length === 0) return null;
  return (
    <Breadcrumb className="min-w-0">
      <BreadcrumbList className="flex-nowrap">
        {trail.map((item, index) => (
          <Fragment key={item.path}>
            {index > 0 && <BreadcrumbSeparator className="hidden sm:block" />}
            <BreadcrumbItem className={index < trail.length - 1 ? "hidden sm:inline-flex" : "min-w-0"}>
              {index === trail.length - 1 ? (
                <BreadcrumbPage className="truncate">{item.page.title}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink render={<Link href={item.path} />}>{item.page.title}</BreadcrumbLink>
              )}
            </BreadcrumbItem>
          </Fragment>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
