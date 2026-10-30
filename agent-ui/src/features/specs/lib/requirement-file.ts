/** Requirement input (Stories 2.4, 12.4): mirrors the API's checks so a bad file is caught before upload. */
export const REQUIREMENT_MAX_BYTES = 65_536;
export const REQUIREMENT_MIN_CHARS = 20;
export const REQUIREMENT_ACCEPT = ".md,.markdown,.txt,text/markdown,text/plain";

const EXTENSIONS = [".md", ".markdown", ".txt"];

export function requirementBytes(text: string): number {
  return new TextEncoder().encode(text).length;
}

/** Reads a `.md` / `.txt` file as UTF-8 text; throws an Error with a message for the user. */
export async function readRequirementFile(file: File): Promise<string> {
  const name = file.name.toLowerCase();
  if (!EXTENSIONS.some((extension) => name.endsWith(extension))) {
    throw new Error(`"${file.name}" is not a text requirement; use a .md or .txt file`);
  }
  if (file.size > REQUIREMENT_MAX_BYTES) {
    throw new Error(`"${file.name}" is larger than ${REQUIREMENT_MAX_BYTES / 1024} KB`);
  }
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
  } catch {
    throw new Error(`"${file.name}" is not UTF-8 text`);
  }
  // Binary content shows up as control characters (tab, newline and carriage return are fine).
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text)) {
    throw new Error(`"${file.name}" contains binary content`);
  }
  return text.replace(/^\uFEFF/, "");
}
