import { base, arrow, footer, C } from "./theme.mjs";

export async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "Demo en vivo: mostrar el hilo completo, no todos los detalles");
  const items = [
    ["1", "Arrancar aplicacion", "./run.sh o python -m bde_xbrl_editor."],
    ["2", "Cargar taxonomia", "Metadatos, catalogo BDE, tablas y cache."],
    ["3", "Abrir instancia", "schemaRef, entidad, periodo y filing indicators."],
    ["4", "Navegar tabla", "Cabeceras multinivel, codigos RC, eje Z y hechos."],
    ["5", "Editar y validar", "Valor como string, finding y navegacion a celda."],
    ["6", "Conformance CLI", "pytest integration o runner con JSON."],
  ];
  let y = 148;
  for (let i = 0; i < items.length; i += 1) {
    const [n, title, body] = items[i];
    ctx.addShape(slide, { x: 122, y, w: 58, h: 58, fill: i % 2 ? C.teal : C.blue });
    ctx.addText(slide, { text: n, x: 122, y: y + 14, w: 58, h: 22, size: 22, bold: true, color: C.white, align: "center" });
    ctx.addShape(slide, { x: 210, y, w: 770, h: 58, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
    ctx.addText(slide, { text: title, x: 236, y: y + 10, w: 260, h: 20, size: 16, bold: true, color: C.ink });
    ctx.addText(slide, { text: body, x: 520, y: y + 13, w: 410, h: 18, size: 12.5, color: C.muted });
    if (i < items.length - 1) arrow(slide, ctx, 151, y + 58, 151, y + 86, "#B7C4CF");
    y += 78;
  }
  ctx.addText(slide, {
    text: "Regla de demo: preparar una instancia conocida, evitar esperas largas y verbalizar que cada paso corresponde a una feature especificada.",
    x: 164,
    y: 632,
    w: 850,
    h: 24,
    size: 17,
    bold: true,
    color: C.ink,
    align: "center",
  });
  footer(slide, ctx);
  return slide;
}
