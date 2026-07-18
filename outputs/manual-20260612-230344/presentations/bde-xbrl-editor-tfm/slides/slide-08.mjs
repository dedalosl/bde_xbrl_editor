import path from "node:path";
import { darkFooter, topRule, C } from "./theme.mjs";

export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: C.black });
  await ctx.addImage(slide, {
    path: path.join(ctx.assetDir, "validation-conformance-v2.png"),
    x: 0,
    y: 0,
    w: ctx.W,
    h: ctx.H,
    fit: "cover",
    alt: "Visual tecnico de pipeline de validacion XBRL con checks, avisos e informe final",
  });
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: "#08111BAA" });
  ctx.addShape(slide, { x: 0, y: 0, w: 526, h: ctx.H, fill: "#07111BE8" });
  topRule(slide, ctx, C.red);
  ctx.addText(slide, {
    text: "BDE XBRL Editor",
    x: 64,
    y: 34,
    w: 340,
    h: 22,
    size: 12,
    bold: true,
    color: C.teal,
  });
  ctx.addText(slide, {
    text: "Validar no debe romper el flujo: debe producir hallazgos accionables",
    x: 64,
    y: 86,
    w: 430,
    h: 136,
    size: 37,
    bold: true,
    color: C.white,
    typeface: ctx.fonts.title,
  });
  ctx.addText(slide, {
    text: "El orquestador captura errores, aplica reglas por niveles y devuelve un ValidationReport inmutable con severidad, regla, mensaje y contexto de negocio.",
    x: 66,
    y: 248,
    w: 420,
    h: 82,
    size: 17,
    color: "#DCE7EF",
    lineSpacing: 1.08,
  });
  const stages = [
    ["Parser instancia", "XML, schemaRef, contextos, unidades, hechos", C.blue],
    ["Estructural", "referencias, namespaces, duplicados, tipos base", C.teal],
    ["Dimensional", "hypercubes, miembros permitidos, contextElement", C.amber],
    ["Relaciones", "calculation, essence-alias, consistencia", C.navy],
    ["Formula 1.0", "assertions, variables, filtros, XPath 2.0", C.red],
  ];
  let y = 372;
  for (let i = 0; i < stages.length; i += 1) {
    const [title, body, color] = stages[i];
    ctx.addShape(slide, { x: 66, y, w: 406, h: 42, fill: "#FFFFFF12", line: { style: "solid", fill: "#FFFFFF22", width: 1 } });
    ctx.addShape(slide, { x: 66, y, w: 6, h: 42, fill: color });
    ctx.addText(slide, { text: `${i + 1}`, x: 84, y: y + 10, w: 22, h: 18, size: 14, bold: true, color });
    ctx.addText(slide, { text: title, x: 116, y: y + 8, w: 136, h: 20, size: 15, bold: true, color: C.white });
    ctx.addText(slide, { text: body, x: 260, y: y + 10, w: 188, h: 18, size: 10.5, color: "#B9C8D4" });
    y += 49;
  }
  ctx.addShape(slide, { x: 642, y: 538, w: 486, h: 76, fill: "#07111BE6", line: { style: "solid", fill: "#46A8A333", width: 1 } });
  ctx.addText(slide, {
    text: "findings inmutables con severidad, regla, mensaje, concepto, contexto y tabla asociada cuando existe mapeo a celda.",
    x: 674,
    y: 570,
    w: 420,
    h: 28,
    size: 15,
    color: "#DCE7EF",
  });
  ctx.addText(slide, {
    text: "ValidationReport",
    x: 674,
    y: 552,
    w: 190,
    h: 22,
    size: 18,
    bold: true,
    color: C.white,
  });
  ctx.addText(slide, {
    text: String(ctx.slideNumber).padStart(2, "0"),
    x: 1168,
    y: 42,
    w: 48,
    h: 24,
    size: 12,
    bold: true,
    color: "#A7B7C5",
    align: "right",
  });
  darkFooter(slide, ctx);
  return slide;
}
