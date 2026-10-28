import { PAGE_MARKDOWN } from "../_ai-page-data.js";

function preferredMarkdown(acceptHeader = "") {
  const ranges = acceptHeader.split(",").map((item) => {
    const [type, ...parameters] = item.trim().toLowerCase().split(";");
    const parameter = parameters.find((value) => value.trim().startsWith("q="));
    const quality = parameter ? Number(parameter.trim().slice(2)) : 1;
    return { type: type.trim(), quality: Number.isFinite(quality) && quality >= 0 && quality <= 1 ? quality : 0 };
  });
  const markdownQuality = Math.max(0, ...ranges.filter((range) => range.type === "text/markdown").map((range) => range.quality));
  const exactHtml = ranges.find((range) => range.type === "text/html");
  const wildcard = ranges.find((range) => range.type === "*/*");
  return markdownQuality > 0 && markdownQuality > (exactHtml ? exactHtml.quality : (wildcard?.quality ?? 0));
}

function addVaryAccept(headers) {
  const values = (headers.get("Vary") || "").split(",").map((value) => value.trim()).filter(Boolean);
  if (values.some((value) => value === "*")) return;
  if (!values.some((value) => value.toLowerCase() === "accept")) values.push("Accept");
  headers.set("Vary", values.join(", "));
}

export async function onRequest(context) {
  const response = await context.next();
  const { pathname } = new URL(context.request.url);
  const wantsMarkdown = preferredMarkdown(context.request.headers.get("Accept"));
  const safeMethod = ["GET", "HEAD"].includes(context.request.method);
  const headers = new Headers(response.headers);
  const copy = Object.hasOwn(PAGE_MARKDOWN, pathname) ? PAGE_MARKDOWN[pathname] : null;
  if (copy || response.status === 404) addVaryAccept(headers);

  let body;
  if (copy && response.status === 200 && wantsMarkdown && safeMethod) {
    body = copy;
    headers.set("Link", "<https://www.madefromeffort.com" + pathname + ">; rel=\"canonical\"");
  } else if (response.status === 404 && wantsMarkdown && safeMethod) {
    body = "# Page not found\n\nThe requested page does not exist. Browse the [site index](https://www.madefromeffort.com/llms.txt), [sitemap](https://www.madefromeffort.com/sitemap.xml), or [contact page](https://www.madefromeffort.com/contact).\n";
  }
  if (body !== undefined) {
    headers.set("Content-Type", "text/markdown; charset=utf-8");
    // HTML representation validators and encodings no longer apply.
    for (const name of ["Content-Length", "Content-Encoding", "Content-Range", "ETag", "Last-Modified"]) headers.delete(name);
    return new Response(context.request.method === "HEAD" ? null : body, { status: response.status, headers });
  }
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}
