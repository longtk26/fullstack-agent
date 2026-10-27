// Serves the static export (`out/`) for the Playwright smoke tests: node scripts/serve-static.mjs out 3100
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const [root = "out", port = "3100"] = process.argv.slice(2);
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
  ".txt": "text/plain",
  ".woff2": "font/woff2",
};

function resolve(url) {
  const path = normalize(decodeURIComponent(new URL(url, "http://x").pathname)).replace(/^(\.\.[/\\])+/, "");
  for (const candidate of [join(root, path), join(root, path, "index.html"), join(root, `${path}.html`)]) {
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }
  return null;
}

createServer((request, response) => {
  const file = resolve(request.url ?? "/");
  const status = file ? 200 : 404;
  const target = file ?? join(root, "404.html");
  response.writeHead(status, { "content-type": TYPES[extname(target)] ?? "application/octet-stream" });
  if (existsSync(target)) createReadStream(target).pipe(response);
  else response.end("Not found");
}).listen(Number(port), "127.0.0.1");
