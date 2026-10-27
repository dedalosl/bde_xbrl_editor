import { base, arrow, footer, pill, C } from "./theme.mjs";

export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "Objetivo: cubrir el ciclo de vida completo de una instancia XBRL");
  const steps = [
    ["1", "Taxonomia", "Cargar DTS, linkbases, etiquetas, tablas y formulas"],
    ["2", "Instancia", "Crear o abrir XML/XBRL con entidad, periodo y filing indicators"],
    ["3", "Tabla", "Renderizar layouts BDE y mapear hechos a celdas"],
    ["4", "Edicion", "Modificar valores con validacion de tipo y guardado seguro"],
    ["5", "Validacion", "Ejecutar checks estructurales, dimensionales, calculo y formulas"],
  ];
  let x = 70;
  for (let i = 0; i < steps.length; i += 1) {
    const [n, t, b] = steps[i];
    ctx.addShape(slide, { x, y: 214, w: 190, h: 210, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
    ctx.addShape(slide, { x, y: 214, w: 190, h: 8, fill: i % 2 ? C.teal : C.blue });
    ctx.addText(slide, { text: n, x: x + 18, y: 244, w: 42, h: 42, size: 28, bold: true, color: i % 2 ? C.teal : C.blue });
    ctx.addText(slide, { text: t, x: x + 18, y: 298, w: 152, h: 28, size: 19, bold: true, color: C.ink });
    ctx.addText(slide, { text: b, x: x + 18, y: 340, w: 150, h: 56, size: 12, color: C.muted });
    if (i < steps.length - 1) arrow(slide, ctx, x + 190, 319, x + 226, 319, C.line);
    x += 222;
  }
  ctx.addShape(slide, { x: 188, y: 486, w: 806, h: 64, fill: "#EAF4F3", line: { style: "solid", fill: "#BBD9D6", width: 1 } });
  ctx.addText(slide, {
    text: "Resultado buscado: una unica aplicacion local para preparar informes, entender su estructura y detectar errores antes de la entrega.",
    x: 226,
    y: 506,
    w: 730,
    h: 26,
    size: 18,
    bold: true,
    color: C.ink,
  });
  pill(slide, ctx, "Offline por defecto", 210, 592, 150, C.navy);
  pill(slide, ctx, "Core testeable sin Qt", 390, 592, 170, C.teal);
  pill(slide, ctx, "Precision numerica", 590, 592, 150, C.blue);
  pill(slide, ctx, "Conformidad medible", 770, 592, 170, C.amber, C.ink);
  footer(slide, ctx);
  return slide;
}
