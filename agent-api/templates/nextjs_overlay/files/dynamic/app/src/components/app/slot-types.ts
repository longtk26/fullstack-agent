import type { ComponentType, ReactNode } from "react";
import type { TAppEntity, TFieldRoles, TRecord } from "./app";

/** Story 23.11: what an engine-written card gets. Everything it shows is here; it never loads data. */
export type TCardProps = {
  record: TRecord;
  entity?: TAppEntity;
  roles: TFieldRoles;
  title: string;
  /** The record's page, when it has one. */
  href?: string;
  /** The record's menu (its actions, already filtered by `allowedActions`). */
  actions: ReactNode;
  view: string;
};

export type TShellNavItem = { label: string; href: string; icon: ReactNode; current: boolean };

/** Story 23.11: what an engine-written shell gets: the navigation this user may use, the account controls, the page. */
export type TShellProps = { appName: string; nav: TShellNavItem[]; account: ReactNode; children: ReactNode };

export type TSlots = { shell?: ComponentType<TShellProps>; cards: Record<string, ComponentType<TCardProps>> };
