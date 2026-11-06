"use client";


import type { ReactNode } from "react";
import { AppShell } from "@/components/app/AppShell";
import { ProtoShell } from "@/components/app/ProtoShell";

type SiteShellProps = {
  children: ReactNode;
};

/** Story 23.0 prototype: the brief's shell around the kit's (`?proto=off` keeps the kit's). */
export function SiteShell({ children }: SiteShellProps) {
  return <ProtoShell Kit={AppShell}>{children}</ProtoShell>;
}
