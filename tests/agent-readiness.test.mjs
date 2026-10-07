import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const read = (path) => readFile(new URL(path, root), "utf8");
const middlewareSource = await read("functions/_middleware.js");
const middlewareUrl = `data:text/javascript;base64,${Buffer.from(middlewareSource).toString("base64")}`;
const { onRequest } = await import(middlewareUrl);

function visibleText(html) {
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<!--([\s\S]*?)-->/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&(?:nbsp|amp|lt|gt|quot|#39);/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

test("homepage has substantial raw content and sequential heading levels", async () => {
  const html = await read("index.html");
  const text = visibleText(html);
  assert.ok(text.length >= 500, `homepage raw text is only ${text.length} characters`);
  assert.match(html, /<h1\b[^>]*>[^<]*Gym design built/s);
  const levels = [...html.matchAll(/<h([1-6])\b[^>]*>/gi)].map((match) => Number(match[1]));
  assert.ok(levels.length > 1, "homepage should have a useful heading structure");
  assert.equal(levels[0], 1, "first heading should be H1");
  for (let index = 1; index < levels.length; index += 1) {
    assert.ok(levels[index] <= levels[index - 1] + 1, `heading level jumps from H${levels[index - 1]} to H${levels[index]}`);
  }
});

test("trust pages provide substantive content and contact routes", async () => {
  for (const path of ["about.html", "privacy.html", "contact.html"]) {
    const html = await read(path);
    assert.ok(visibleText(html).length >= 500, `${path} has fewer than 500 visible content characters`);
    assert.match(html, /<h1\b/i, `${path} has no H1`);
  }
});

test("homepage Person JSON-LD has a description and URL", async () => {
  const html = await read("index.html");
  const json = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/i)?.[1];
  assert.ok(json, "homepage JSON-LD is missing");
  const graph = JSON.parse(json);
  const person = graph["@graph"].find((entry) => entry.founder?.["@type"] === "Person")?.founder;
  assert.ok(person, "Person entity is missing");
  assert.ok(person.description?.length > 30, "Person description is missing or too short");
  assert.equal(person.url, "https://www.madefromeffort.com/about.html");
});

test("llms.txt and agent instructions state specific fit and safe contact guidance", async () => {
  const llms = await read("llms.txt");
  const instructions = await read("agent-instructions.md");
  assert.match(llms, /^# Made From Effort/m);
  assert.match(llms, /^> /m);
  assert.match(llms, /agent-instructions\.md/);
  assert.match(instructions, /## When to use this business/);
  assert.match(instructions, /yacht|marine/i);
  assert.match(instructions, /Do not fill in or submit/i);
});

test("sitemap includes the new trust pages", async () => {
  const sitemap = await read("sitemap.xml");
  assert.match(sitemap, /https:\/\/www\.madefromeffort\.com\/about\.html/);
  assert.match(sitemap, /https:\/\/www\.madefromeffort\.com\/privacy\.html/);
});

test("Accept: text/markdown returns Markdown at the homepage with Vary: Accept", async () => {
  const request = new Request("https://example.test/", { headers: { Accept: "text/markdown" } });
  const response = await onRequest({ request, next: async () => new Response("<h1>HTML</h1>", {
    headers: { "Content-Type": "text/html; charset=utf-8", Vary: "Accept-Encoding" }
  }) });
  assert.equal(response.status, 200);
  assert.match(response.headers.get("Content-Type"), /^text\/markdown\s*;/);
  assert.match(response.headers.get("Vary"), /Accept-Encoding/i);
  assert.match(response.headers.get("Vary"), /(?:^|,\s*)Accept(?:,|$)/i);
  const body = await response.text();
  assert.ok(body.length >= 500);
  assert.match(body, /^# Made From Effort Gym Design/m);
});

test("HTML remains HTML while varying on Accept", async () => {
  const request = new Request("https://example.test/", { headers: { Accept: "text/html" } });
  const response = await onRequest({ request, next: async () => new Response("<h1>HTML</h1>", {
    headers: { "Content-Type": "text/html; charset=utf-8", Vary: "Accept-Encoding" }
  }) });
  assert.match(response.headers.get("Content-Type"), /^text\/html/);
  assert.match(response.headers.get("Vary"), /Accept-Encoding/i);
  assert.match(response.headers.get("Vary"), /Accept/i);
  assert.equal(await response.text(), "<h1>HTML</h1>");
});

test("Markdown 404 keeps status 404 and links to discovery pages", async () => {
  const request = new Request("https://example.test/does-not-exist", { headers: { Accept: "text/markdown" } });
  const response = await onRequest({ request, next: async () => new Response("not found", { status: 404 }) });
  assert.equal(response.status, 404);
  assert.match(response.headers.get("Content-Type"), /^text\/markdown\s*;/);
  assert.match(response.headers.get("Vary"), /Accept/i);
  const body = await response.text();
  assert.ok(body.length >= 20);
  assert.match(body, /\[site index\].*\/llms\.txt/);
});

test("Markdown is not selected when HTML has a higher Accept quality", async () => {
  const request = new Request("https://example.test/", { headers: { Accept: "text/markdown;q=0.6, text/html;q=0.9" } });
  const response = await onRequest({ request, next: async () => new Response("<html>HTML</html>", {
    headers: { "Content-Type": "text/html" }
  }) });
  assert.match(response.headers.get("Content-Type"), /^text\/html/);
  assert.equal(await response.text(), "<html>HTML</html>");
});
