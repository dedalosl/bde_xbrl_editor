import path from "node:path";
import { base, footer, C } from "./theme.mjs";

export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "La arquitectura separa UI, servicios y nucleo XBRL");
  ctx.addText(slide, {
    text: "La decision principal fue aislar el conocimiento XBRL de la interfaz: PySide6 queda en la capa visual y los modelos/reglas se prueban sin Qt.",
    x: 64,
    y: 116,
    w: 560,
    h: 54,
    size: 17,
    color: C.muted,
    lineSpacing: 1.08,
  });
  await ctx.addImage(slide, {
    path: path.join(ctx.assetDir, "architecture-layers-v2.png"),
    x: 676,
    y: 118,
    w: 520,
    h: 392,
    fit: "cover",
    alt: "Visual abstracto de arquitectura por capas con dependencias descendentes",
  });
  ctx.addShape(slide, { x: 676, y: 118, w: 520, h: 392, fill: "#07111B35", line: { style: "solid", fill: "#FFFFFF00", width: 0 } });
  ctx.addShape(slide, { x: 676, y: 118, w: 520, h: 392, fill: "#00000000", line: { style: "solid", fill: "#C6D1DB", width: 1 } });
  const layers = [
    ["UI / API", "PySide6: ventana principal, widgets, paneles, tablas, validacion", C.navy],
    ["Servicios de aplicacion", "orquestacion: crear instancia, editar, validar, renderizar", C.blue],
    ["Adaptacion BDE", "Table Linkbase PWD, Eurofiling filing indicators, formulas", C.teal],
    ["Core XBRL", "taxonomy/, instance/, validation/: modelos y reglas sin Qt", C.amber],
  ];
  let y = 196;
  for (const [name, body, color] of layers) {
    ctx.addShape(slide, { x: 64, y, w: 560, h: 74, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
    ctx.addShape(slide, { x: 64, y, w: 10, h: 74, fill: color });
    ctx.addText(slide, { text: name, x: 94, y: y + 13, w: 245, h: 26, size: 20, bold: true, color: C.ink });
    ctx.addText(slide, { text: body, x: 94, y: y + 42, w: 486, h: 20, size: 12.8, color: C.muted });
    y += 86;
  }
  ctx.addShape(slide, { x: 704, y: 544, w: 438, h: 52, fill: "#EAF4F3", line: { style: "solid", fill: "#BBD9D6", width: 1 } });
  ctx.addText(slide, {
    text: "Principio de dependencia: lo regulatorio vive en modelos y servicios; la UI solo orquesta experiencia.",
    x: 728,
    y: 558,
    w: 390,
    h: 24,
    size: 15,
    bold: true,
    color: C.ink,
    align: "center",
  });
  footer(slide, ctx);
  return slide;
}
