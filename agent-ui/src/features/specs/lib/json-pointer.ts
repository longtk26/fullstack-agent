import { findNodeAtLocation, parseTree } from "jsonc-parser";
import type { Node } from "jsonc-parser";

export type TTextRange = { offset: number; length: number };

function decodeSegment(segment: string): string | number {
  const key = segment.replaceAll("~1", "/").replaceAll("~0", "~");
  return /^\d+$/.test(key) ? Number(key) : key;
}

/**
 * Maps an RFC 6901 JSON pointer to the text range of the deepest node that exists, so an issue about a
 * missing property still lands on its parent object. An empty pointer maps to the whole document.
 */
export function pointerToRange(text: string, pointer: string): TTextRange | null {
  const root = parseTree(text);
  if (!root) return null;
  const segments = pointer.split("/").slice(1).map(decodeSegment);
  for (let depth = segments.length; depth >= 0; depth -= 1) {
    const node: Node | undefined = depth === 0 ? root : findNodeAtLocation(root, segments.slice(0, depth));
    if (node) {
      // Highlight "key": value for properties, not just the value.
      const target = node.parent?.type === "property" ? node.parent : node;
      return { offset: target.offset, length: target.length };
    }
  }
  return null;
}

export type TParseResult = { ok: true; value: unknown } | { ok: false; message: string; offset: number };

export function parseJson(text: string): TParseResult {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid JSON";
    const position = /position (\d+)/.exec(message);
    return { ok: false, message, offset: position ? Number(position[1]) : 0 };
  }
}
