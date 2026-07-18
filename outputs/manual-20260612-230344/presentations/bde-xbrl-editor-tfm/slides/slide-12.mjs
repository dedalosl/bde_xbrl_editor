import path from "node:path";
import { C } from "./theme.mjs";

export async function slide12(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: C.black });
  await ctx.addImage(slide, {
    path: path.join(ctx.assetDir, "title-background.png"),
    x: 640,
    y: 0,
    w: 640,
    h: 720,
    fit: "cover",
    alt: "Visual tecnico de tablas XBRL y validacion",
  });
  ctx.addShape(slide, { x: 560, y: 0, w: 720, h: 720, fill: "#07111BBA" });
  ctx.addShape(slide, { x: 0, y: 0, w: 720, h: 720, fill: "#07111BF4" });
  ctx.addShape(slide, { x: 78, y: 82, w: 90, h: 6, fill: C.teal });
  ctx.addText(slide, {
    text: "Conclusiones",
    x: 78,
    y: 122,
    w: 620,
    h: 60,
    size: 44,
    bold: true,
    color: C.white,
    typeface: ctx.fonts.title,
  });
  const takeaways = [
    ["Producto real", "No es un prototipo aislado: cubre carga, instancia, tabla, edicion, validacion y conformidad."],
    ["Arquitectura sostenible", "Core XBRL independiente de Qt, capas claras y modelos pensados para pruebas."],
    ["Metodo defendible", "Spec-driven development conecta problema, requisitos, diseno, tareas y verificacion."],
  ];
  let y = 232;
  for (const [title, body] of takeaways) {
    ctx.addShape(slide, { x: 92, y, w: 16, h: 70, fill: C.teal });
    ctx.addText(slide, { text: title, x: 134, y: y - 2, w: 300, h: 26, size: 21, bold: true, color: C.white });
    ctx.addText(slide, { text: body, x: 134, y: y + 32, w: 620, h: 30, size: 15, color: "#C9D4DD" });
    y += 104;
  }
  ctx.addShape(slide, { x: 78, y: 594, w: 650, h: 1, fill: "#334252" });
  ctx.addText(slide, {
    text: "Idea final: convertir la complejidad tecnica de XBRL/BDE en un flujo visual, verificable y mantenible.",
    x: 78,
    y: 620,
    w: 690,
    h: 30,
    size: 22,
    bold: true,
    color: C.amber,
  });
  return slide;
}
