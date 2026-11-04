"use client";

// A client component on purpose: the data components below are client modules, and a server component importing
// their map would only get client references, not the components (every node still renders on the server first).
import { createElement, Fragment, type CSSProperties, type ReactNode } from "react";
import Link from "next/link";
import { AssetImage } from "@/components/assets/AssetImage";
import { Container } from "@/components/layout/Container";
import { Icon } from "@/components/sections/Icon";
import { SectionRenderer } from "../SectionRenderer";
import type { TTreeNode } from "../site";
import { PRIMITIVES } from "./primitives";
import { DATA_COMPONENTS } from "./tree-data";

/**
 * A designed page (Epic 21): the element tree the drafting engine wrote, checked and bound by the generator
 * (`frontend_renderer.tree_site`). Elements render as they are; primitives come from shadcn; icons, library
 * sections and data components from the renderer. `animate` becomes `data-animate`, which the motion CSS reveals
 * (Story 20.6); without motion every node is in its final state.
 */
export function TreeRenderer({ node, pageId }: { node: TTreeNode; pageId: string }) {
  return <>{renderNode(node, pageId, "t")}</>;
}

function renderChildren(node: TTreeNode, pageId: string, key: string): ReactNode[] | undefined {
  if (!node.children?.length) return undefined;
  return node.children.map((child, index) =>
    typeof child === "string" ? child : renderNode(child, pageId, `${key}-${index}`),
  );
}

function animateProps(props: Record<string, unknown>): Record<string, unknown> {
  const { animate, ...rest } = props;
  if (!animate || typeof animate !== "object") return rest;
  const motion = animate as { type?: string; delay?: number };
  const style = { ...((rest.style as CSSProperties | undefined) ?? {}) } as CSSProperties & Record<string, string>;
  if (motion.delay) style["--animate-delay"] = `${motion.delay}s`;
  return { ...rest, "data-animate": motion.type ?? "fade-up", style };
}

export function renderNode(node: TTreeNode, pageId: string, key: string): ReactNode {
  const props = animateProps(node.props ?? {});
  const children = renderChildren(node, pageId, key);
  switch (node.kind) {
    case "element":
      return createElement(node.type, { key, ...props }, children);
    case "image":
      return (
        <AssetImage
          key={key}
          asset={String(node.asset)}
          className={typeof props.className === "string" ? props.className : undefined}
        />
      );
    case "icon":
      return (
        <Icon
          key={key}
          icon={String(node.icon)}
          className={typeof props.className === "string" ? props.className : undefined}
        />
      );
    case "link": {
      const { href, external, ...rest } = props as { href?: string; external?: boolean } & Record<string, unknown>;
      if (!href) return <span key={key} {...rest}>{children}</span>;
      if (external) {
        return (
          <a key={key} href={href} rel="noreferrer" target="_blank" {...rest}>
            {children}
          </a>
        );
      }
      return (
        <Link key={key} href={href} {...rest}>
          {children}
        </Link>
      );
    }
    case "primitive": {
      if (node.type === "Container") {
        return (
          <Container key={key} className={typeof props.className === "string" ? props.className : undefined}>
            {children}
          </Container>
        );
      }
      const Primitive = PRIMITIVES[node.type];
      if (!Primitive) return <Fragment key={key}>{children}</Fragment>;
      return createElement(Primitive, { key, ...props }, children);
    }
    case "section":
      return (
        <SectionRenderer
          key={key}
          pageId={pageId}
          section={{
            id: node.id ?? key,
            component: String(node.component),
            content: node.content ?? {},
            data: node.data,
            form: node.form,
            states: node.states,
          }}
        />
      );
    case "data": {
      const Data = DATA_COMPONENTS[String(node.component)];
      if (!Data) return <Fragment key={key}>{children}</Fragment>;
      return (
        <Data key={key} node={node} pageId={pageId} {...props}>
          {children}
        </Data>
      );
    }
    default:
      return <Fragment key={key}>{children}</Fragment>;
  }
}
