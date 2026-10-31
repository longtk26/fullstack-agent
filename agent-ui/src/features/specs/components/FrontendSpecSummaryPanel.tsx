"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Stack } from "@/components/layout/Stack";
import type { TFrontendSpecSummary } from "../lib/frontend-spec-summary";

type FrontendSpecSummaryPanelProps = {
  summary: TFrontendSpecSummary;
  showOperations: boolean;
  onDropManageArea?: () => void;
};

/** What the FrontendSpec will build (Story 9.7b): pages and routes, theme, components and, in dynamic mode, API use. */
export function FrontendSpecSummaryPanel({ summary, showOperations, onDropManageArea }: FrontendSpecSummaryPanelProps) {
  const [manageOpen, setManageOpen] = useState(false);

  if (summary.pages.length === 0) {
    return <p className="text-sm text-muted-foreground">Pages, theme and components appear here once the JSON parses.</p>;
  }

  const regularPages = summary.pages.filter(
    (page) => !page.route.startsWith("/manage") && !page.id.startsWith("manage-"),
  );
  const managePages = summary.pages.filter(
    (page) => page.route.startsWith("/manage") || page.id.startsWith("manage-"),
  );
  const { theme } = summary;
  const fonts = [theme.headingFont, theme.bodyFont].filter(Boolean);

  return (
    <Stack gap="md">
      <Stack gap="xs">
        <h3 className="text-sm font-medium">Pages ({summary.pages.length})</h3>
        <div className="max-h-60 overflow-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Route</TableHead>
                <TableHead>Title</TableHead>
                {showOperations && <TableHead>Operations</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {regularPages.map((page) => (
                <TableRow key={page.id}>
                  <TableCell className="font-mono text-xs">{page.route}</TableCell>
                  <TableCell className="text-xs">
                    {page.title} <span className="text-muted-foreground">· {page.sectionCount}</span>
                  </TableCell>
                  {showOperations && (
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {page.operations.join(", ") || "—"}
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {managePages.length > 0 && (
          <div className="rounded-md border p-2">
            <div className="flex items-center justify-between">
              <button
                type="button"
                className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={() => setManageOpen((prev) => !prev)}
              >
                <span>{manageOpen ? "▼" : "▶"}</span>
                <span>Manage area ({managePages.length} pages)</span>
                <Badge variant="secondary">generated</Badge>
              </button>
              {onDropManageArea && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs text-destructive hover:text-destructive"
                  onClick={onDropManageArea}
                >
                  Drop area
                </Button>
              )}
            </div>
            {manageOpen && (
              <div className="mt-2 max-h-48 overflow-auto border-t pt-2">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Route</TableHead>
                      <TableHead>Title</TableHead>
                      {showOperations && <TableHead>Operations</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {managePages.map((page) => (
                      <TableRow key={page.id}>
                        <TableCell className="font-mono text-xs">{page.route}</TableCell>
                        <TableCell className="text-xs">
                          {page.title} <span className="text-muted-foreground">· {page.sectionCount}</span>
                        </TableCell>
                        {showOperations && (
                          <TableCell className="font-mono text-xs text-muted-foreground">
                            {page.operations.join(", ") || "—"}
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}
      </Stack>

      <Stack gap="xs">
        <h3 className="text-sm font-medium">Theme</h3>
        <Stack direction="row" gap="xs" wrap align="center">
          {theme.colors.map((color) => (
            <span key={color.name} className="flex items-center gap-1 text-xs" title={`${color.name}: ${color.value}`}>
              <span className="size-4 rounded-sm border" style={{ background: color.value }} />
              {color.name}
            </span>
          ))}
          {theme.colors.length === 0 && <span className="text-xs text-muted-foreground">preset colours</span>}
        </Stack>
        <Stack direction="row" gap="xs" wrap>
          {theme.style && <Badge variant="outline">{theme.style}</Badge>}
          {theme.colorScheme && <Badge variant="outline">{theme.colorScheme}</Badge>}
          {theme.radius && <Badge variant="outline">radius {theme.radius}</Badge>}
          {fonts.length > 0 && <Badge variant="outline">{[...new Set(fonts)].join(" / ")}</Badge>}
        </Stack>
      </Stack>

      <Stack gap="xs">
        <h3 className="text-sm font-medium">Components ({summary.components.length})</h3>
        <Stack gap="xs">
          {summary.components.map((component) => (
            <div key={component.name} className="flex flex-wrap items-baseline gap-x-2 text-xs">
              <span className="font-medium">{component.name}</span>
              {component.custom && <Badge variant="secondary">custom</Badge>}
              <span className="text-muted-foreground">{component.pages.join(", ") || "unused"}</span>
            </div>
          ))}
        </Stack>
      </Stack>
    </Stack>
  );
}
