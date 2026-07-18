import { base, footer, label, C } from "./theme.mjs";

export async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "Renderizado PWD: de la taxonomia a una tabla editable");
  ctx.addText(slide, {
    text: "El motor no dibuja plantillas fijas: calcula cabeceras, ejes y coordenadas desde la Table Linkbase PWD usada por BDE.",
    x: 64,
    y: 124,
    w: 890,
    h: 38,
    size: 18,
    color: C.ink,
  });
  label(slide, ctx, "Eje X: columnas", 416, 190, 240, C.blue);
  label(slide, ctx, "Eje Y: filas", 114, 286, 190, C.teal);
  label(slide, ctx, "Eje Z: filtro / slice", 832, 190, 220, C.amber);
  ctx.addShape(slide, { x: 332, y: 218, w: 430, h: 76, fill: "#EAF2F8", line: { style: "solid", fill: C.blue, width: 1 } });
  for (let i = 0; i < 4; i += 1) {
    ctx.addShape(slide, { x: 350 + i * 98, y: 242, w: 84, h: 28, fill: C.white, line: { style: "solid", fill: "#BED4E7", width: 1 } });
    ctx.addText(slide, { text: `C00${i + 1}0`, x: 360 + i * 98, y: 250, w: 64, h: 12, size: 9, bold: true, color: C.blue, align: "center" });
  }
  ctx.addShape(slide, { x: 112, y: 318, w: 192, h: 220, fill: "#EAF4F3", line: { style: "solid", fill: C.teal, width: 1 } });
  for (let i = 0; i < 4; i += 1) {
    ctx.addShape(slide, { x: 132, y: 342 + i * 44, w: 150, h: 28, fill: C.white, line: { style: "solid", fill: "#BBD9D6", width: 1 } });
    ctx.addText(slide, { text: `R00${i + 1}0`, x: 148, y: 350 + i * 44, w: 54, h: 12, size: 9, bold: true, color: C.teal });
    ctx.addText(slide, { text: "Concept label", x: 204, y: 350 + i * 44, w: 68, h: 12, size: 8.5, color: C.muted });
  }
  ctx.addShape(slide, { x: 332, y: 318, w: 430, h: 220, fill: C.white, line: { style: "solid", fill: "#CAD5DE", width: 1 } });
  for (let c = 1; c < 4; c += 1) ctx.addShape(slide, { x: 332 + c * 107.5, y: 318, w: 1, h: 220, fill: "#E1E7ED" });
  for (let r = 1; r < 4; r += 1) ctx.addShape(slide, { x: 332, y: 318 + r * 55, w: 430, h: 1, fill: "#E1E7ED" });
  ctx.addShape(slide, { x: 440, y: 373, w: 107, h: 55, fill: "#D8EFEA", line: { style: "solid", fill: C.teal, width: 2 } });
  ctx.addText(slide, { text: "Fact", x: 466, y: 389, w: 54, h: 15, size: 13, bold: true, color: C.teal, align: "center" });
  ctx.addShape(slide, { x: 655, y: 428, w: 107, h: 55, fill: "#FBE7E7", line: { style: "solid", fill: C.red, width: 2 } });
  ctx.addText(slide, { text: "Duplicado", x: 674, y: 444, w: 68, h: 15, size: 11, bold: true, color: C.red, align: "center" });
  ctx.addShape(slide, { x: 832, y: 230, w: 260, h: 44, fill: "#F7EBCB", line: { style: "solid", fill: C.amber, width: 1 } });
  ctx.addText(slide, { text: "Consolidado", x: 856, y: 244, w: 120, h: 16, size: 13, bold: true, color: C.ink });
  ctx.addShape(slide, { x: 832, y: 288, w: 260, h: 44, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
  ctx.addText(slide, { text: "Individual", x: 856, y: 302, w: 120, h: 16, size: 13, color: C.muted });
  ctx.addText(slide, {
    text: "Cada celda queda identificada por: concepto + entidad + periodo + dimensiones explicitas. Esa coordenada permite mostrar, editar y validar el hecho correcto.",
    x: 824,
    y: 388,
    w: 278,
    h: 92,
    size: 15,
    bold: true,
    color: C.ink,
  });
  footer(slide, ctx);
  return slide;
}
