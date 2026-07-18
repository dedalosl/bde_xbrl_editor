import { base, box, footer, C } from "./theme.mjs";

export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "Capacidades principales de la aplicacion");
  ctx.addShape(slide, { x: 72, y: 145, w: 1038, h: 468, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
  ctx.addShape(slide, { x: 92, y: 176, w: 244, h: 390, fill: "#F1F5F8", line: { style: "solid", fill: "#CAD5DE", width: 1 } });
  ctx.addText(slide, { text: "Catalogo BDE y taxonomias", x: 112, y: 198, w: 220, h: 26, size: 16, bold: true, color: C.ink });
  for (const [i, txt] of ["entry points", "linkbases", "tablas", "scraper", "cache"].entries()) {
    ctx.addShape(slide, { x: 116, y: 246 + i * 48, w: 176, h: 28, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
    ctx.addText(slide, { text: txt, x: 132, y: 253 + i * 48, w: 140, h: 14, size: 10.5, color: C.muted });
  }
  ctx.addShape(slide, { x: 378, y: 176, w: 430, h: 390, fill: "#FBFCFD", line: { style: "solid", fill: "#CAD5DE", width: 1 } });
  ctx.addText(slide, { text: "Workspace de instancia", x: 402, y: 198, w: 260, h: 28, size: 19, bold: true, color: C.ink });
  for (let c = 0; c < 5; c += 1) ctx.addShape(slide, { x: 414 + c * 70, y: 258, w: 56, h: 240, fill: "#EAF2F8", line: { style: "solid", fill: C.white, width: 2 } });
  for (let r = 0; r < 5; r += 1) ctx.addShape(slide, { x: 414, y: 258 + r * 48, w: 336, h: 2, fill: C.white });
  ctx.addShape(slide, { x: 484, y: 354, w: 56, h: 48, fill: "#D8EFEA", line: { style: "solid", fill: C.teal, width: 1 } });
  ctx.addShape(slide, { x: 624, y: 402, w: 56, h: 48, fill: "#F7EBCB", line: { style: "solid", fill: C.amber, width: 1 } });
  ctx.addText(slide, { text: "edicion directa sobre celdas renderizadas", x: 428, y: 515, w: 310, h: 20, size: 11, color: C.muted, align: "center" });
  box(slide, ctx, {
    x: 842,
    y: 176,
    w: 236,
    h: 118,
    title: "Validacion",
    body: "Estructural, tipos, dimensiones, calculo, essence-alias y Formula 1.0.",
    accent: C.red,
  });
  box(slide, ctx, {
    x: 842,
    y: 318,
    w: 236,
    h: 118,
    title: "Conformidad",
    body: "Runner CLI contra suites XBRL.org, con salida textual, JSON y exit code para CI.",
    accent: C.blue,
  });
  box(slide, ctx, {
    x: 842,
    y: 460,
    w: 236,
    h: 106,
    title: "Distribucion",
    body: "Ejecucion local, scripts run.sh/run.bat y paquete offline con runtime del scraper.",
    accent: C.teal,
  });
  footer(slide, ctx);
  return slide;
}
