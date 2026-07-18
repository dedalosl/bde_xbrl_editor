import { base, footer, C } from "./theme.mjs";

export async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "La calidad se demuestra con pruebas reproducibles");
  ctx.addShape(slide, { x: 64, y: 132, w: 424, h: 444, fill: C.navy, line: { style: "solid", fill: C.navy, width: 0 } });
  ctx.addText(slide, {
    text: "Evidencia de trabajo",
    x: 96,
    y: 164,
    w: 260,
    h: 30,
    size: 24,
    bold: true,
    color: C.white,
  });
  ctx.addText(slide, {
    text: "La conformidad deja de ser una declaracion: se mide con datos locales, resultados reproducibles y automatizacion apta para CI.",
    x: 96,
    y: 214,
    w: 330,
    h: 78,
    size: 17,
    color: "#DCE7EF",
    lineSpacing: 1.08,
  });
  const metrics = [
    ["248", "tareas completadas"],
    ["6", "features especificadas"],
    ["offline", "runner sin red"],
  ];
  let y = 332;
  for (const [value, label] of metrics) {
    ctx.addShape(slide, { x: 96, y, w: 320, h: 58, fill: "#FFFFFF12", line: { style: "solid", fill: "#FFFFFF26", width: 1 } });
    ctx.addText(slide, { text: value, x: 120, y: y + 10, w: 120, h: 32, size: value.length > 4 ? 24 : 30, bold: true, color: value === "offline" ? C.amber : C.teal, typeface: ctx.fonts.title });
    ctx.addText(slide, { text: label, x: 238, y: y + 20, w: 150, h: 20, size: 14, color: "#DCE7EF" });
    y += 72;
  }
  ctx.addText(slide, {
    text: "pytest + pytest-qt + suites de conformidad",
    x: 96,
    y: 546,
    w: 320,
    h: 22,
    size: 14,
    bold: true,
    color: C.amber,
    align: "center",
  });

  const suites = [
    ["XBRL 2.1", "procesador e instancias", C.blue, "bloqueante"],
    ["Dimensions 1.0", "hipercubos y contexto", C.teal, "bloqueante"],
    ["Formula 1.0", "assertions y XPath", C.red, "bloqueante"],
    ["Table Linkbase 1.0", "seguimiento; BDE prioriza PWD", C.amber, "informativa"],
  ];
  ctx.addText(slide, { text: "Suites de conformidad", x: 552, y: 142, w: 360, h: 30, size: 25, bold: true, color: C.ink });
  ctx.addText(slide, { text: "Cada suite actua como una barrera de confianza sobre una parte distinta del dominio.", x: 552, y: 178, w: 520, h: 24, size: 15, color: C.muted });
  y = 238;
  for (let i = 0; i < suites.length; i += 1) {
    const [title, body, color, status] = suites[i];
    ctx.addShape(slide, { x: 552, y, w: 590, h: 66, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
    ctx.addShape(slide, { x: 552, y, w: 9, h: 66, fill: color });
    ctx.addText(slide, { text: title, x: 584, y: y + 12, w: 210, h: 24, size: 18, bold: true, color: C.ink });
    ctx.addText(slide, { text: body, x: 584, y: y + 39, w: 260, h: 16, size: 12.5, color: C.muted });
    ctx.addShape(slide, { x: 948, y: y + 17, w: 150, h: 30, fill: status === "bloqueante" ? "#EAF4F3" : "#F8F0DE", line: { style: "solid", fill: status === "bloqueante" ? "#BBD9D6" : "#E1C480", width: 1 } });
    ctx.addText(slide, { text: status, x: 966, y: y + 25, w: 114, h: 14, size: 11, bold: true, color: status === "bloqueante" ? C.teal : C.amber, align: "center" });
    if (i < suites.length - 1) {
      ctx.addShape(slide, { x: 826, y: y + 66, w: 2, h: 19, fill: "#B7C4CF" });
    }
    y += 85;
  }
  ctx.addShape(slide, { x: 552, y: 590, w: 590, h: 1, fill: C.line });
  ctx.addText(slide, {
    text: "Resultado: errores detectables localmente antes de una entrega regulatoria.",
    x: 552,
    y: 608,
    w: 590,
    h: 24,
    size: 18,
    bold: true,
    color: C.ink,
    align: "center",
  });
  footer(slide, ctx);
  return slide;
}
