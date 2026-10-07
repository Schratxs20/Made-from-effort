const HOME_MARKDOWN = `# Made From Effort Gym Design

> Made From Effort is the website and Journal of Performance Edge Training + Gym Design, led by Scott Schratwieser, a gym designer and CSCS-certified performance professional based on Long Island, New York.

Performance Edge plans private residential and estate gyms across Nassau and Suffolk counties, and accepts select yacht and marine, commercial, boutique-studio, and country-club fitness projects. Its design perspective connects the room, equipment, materials, and project decisions to real training use. Private and remote performance coaching is offered separately.

## Services

- [Residential and estate gym design](https://www.madefromeffort.com/residential-gym-design.html)
- [Yacht and marine gym design](https://www.madefromeffort.com/yacht-gym-design.html)
- [Commercial gym and boutique studio design](https://www.madefromeffort.com/commercial-gym-design.html)
- [Country-club fitness design](https://www.madefromeffort.com/country-club-fitness-design.html)
- [Private and remote coaching](https://www.madefromeffort.com/training.html)

## Explore

- [Selected projects](https://www.madefromeffort.com/#portfolio)
- [Journal](https://www.madefromeffort.com/journal/)
- [About Scott Schratwieser](https://www.madefromeffort.com/about.html)
- [Contact and project inquiry](https://www.madefromeffort.com/contact.html)
- [Sitemap](https://www.madefromeffort.com/sitemap.xml)
- [Agent guidance](https://www.madefromeffort.com/agent-instructions.md)
`;

function preferredMarkdown(acceptHeader = "") {
  const ranges = acceptHeader.split(",").map((item) => {
    const [type, ...parameters] = item.trim().toLowerCase().split(";");
    const qualityParameter = parameters.find((parameter) => parameter.trim().startsWith("q="));
    const quality = qualityParameter ? Number(qualityParameter.trim().slice(2)) : 1;
    return { type: type.trim(), quality: Number.isFinite(quality) ? quality : 0 };
  });
  const markdownQuality = Math.max(0, ...ranges.filter((range) => range.type === "text/markdown").map((range) => range.quality));
  const exactHtml = ranges.find((range) => range.type === "text/html");
  const wildcard = ranges.find((range) => range.type === "*/*");
  const htmlQuality = exactHtml ? exactHtml.quality : (wildcard?.quality ?? 0);
  return markdownQuality > 0 && markdownQuality > htmlQuality;
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
  const headers = new Headers(response.headers);
  addVaryAccept(headers);

  if (pathname === "/" && wantsMarkdown) {
    headers.set("Content-Type", "text/markdown; charset=utf-8");
    headers.delete("Content-Length");
    return new Response(HOME_MARKDOWN, { status: response.status, headers });
  }

  if (response.status === 404 && wantsMarkdown) {
    headers.set("Content-Type", "text/markdown; charset=utf-8");
    headers.delete("Content-Length");
    return new Response(`# Page not found\n\nThe requested page does not exist. Browse the [site index](https://www.madefromeffort.com/llms.txt), [sitemap](https://www.madefromeffort.com/sitemap.xml), or [contact page](https://www.madefromeffort.com/contact.html).\n`, { status: 404, headers });
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}
