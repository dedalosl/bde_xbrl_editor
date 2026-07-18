import path from "node:path";
import { darkFooter, topRule, C } from "./theme.mjs";

export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: C.black });
  await ctx.addImage(slide, {
    path: path.join(ctx.assetDir, "regulatory-workflow-v2.png"),
    x: 0,
    y: 0,
    w: ctx.W,
    h: ctx.H,
    fit: "cover",
    alt: "Visual tecnico de flujo XBRL regulatorio con taxonomia, validacion y tabla final",
  });
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: "#08111BCC" });
  ctx.addShape(slide, { x: 0, y: 0, w: 560, h: ctx.H, fill: "#07111BEA" });
  topRule(slide, ctx, C.teal);
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
    text: "El reto es trabajar con confianza sobre XBRL",
    x: 64,
    y: 94,
    w: 470,
    h: 118,
    size: 37,
    bold: true,
    color: C.white,
    typeface: ctx.fonts.title,
  });
  ctx.addText(slide, {
    text: "La informacion esta repartida entre taxonomias, XML, dimensiones, reglas de validacion y plantillas regulatorias. Sin una vista integrada, cada revision aumenta el coste y el riesgo.",
    x: 66,
    y: 242,
    w: 438,
    h: 84,
    size: 18,
    color: "#DCE7EF",
    lineSpacing: 1.08,
  });
  const pains = [
    ["Dominio XBRL", "conceptos, contextos, unidades, dimensiones y hechos"],
    ["BDE", "zips de taxonomia, Table Linkbase PWD e indicadores Eurofiling"],
    ["Validacion", "errores tecnicos que deben ser accionables antes del envio"],
  ];
  let y = 382;
  for (const [title, body] of pains) {
    ctx.addShape(slide, { x: 66, y, w: 420, h: 68, fill: "#FFFFFF12", line: { style: "solid", fill: "#FFFFFF26", width: 1 } });
    ctx.addShape(slide, { x: 66, y, w: 6, h: 68, fill: title === "BDE" ? C.teal : title === "Validacion" ? C.amber : C.blue });
    ctx.addText(slide, { text: title, x: 88, y: y + 11, w: 160, h: 22, size: 17, bold: true, color: C.white });
    ctx.addText(slide, { text: body, x: 88, y: y + 36, w: 360, h: 18, size: 12.5, color: "#B9C8D4" });
    y += 78;
  }
  ctx.addText(slide, {
    text: "Tesis del proyecto",
    x: 690,
    y: 540,
    w: 190,
    h: 22,
    size: 14,
    bold: true,
    color: C.amber,
  });
  ctx.addText(slide, {
    text: "Un editor especializado puede convertir una taxonomia compleja en un flujo visual, validable y mantenible para el usuario final.",
    x: 690,
    y: 566,
    w: 460,
    h: 54,
    size: 20,
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
