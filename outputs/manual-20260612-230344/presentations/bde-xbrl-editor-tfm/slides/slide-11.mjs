import { base, box, footer, C } from "./theme.mjs";

export async function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "Limites actuales y evolucion futura");
  ctx.addShape(slide, { x: 80, y: 168, w: 480, h: 420, fill: C.white, line: { style: "solid", fill: C.line, width: 1 } });
  ctx.addText(slide, { text: "Fuera de alcance v1", x: 112, y: 198, w: 280, h: 30, size: 22, bold: true, color: C.ink });
  const limits = [
    "Reglas BDE publicadas fuera de la taxonomia",
    "iXBRL y tagging sobre HTML",
    "Envio directo al portal BDE",
    "Validacion batch y diferencial",
    "Undo/redo avanzado y multi-instancia",
  ];
  for (const [i, txt] of limits.entries()) {
    ctx.addShape(slide, { x: 120, y: 258 + i * 48, w: 12, h: 12, fill: C.red });
    ctx.addText(slide, { text: txt, x: 148, y: 250 + i * 48, w: 350, h: 26, size: 14, color: C.muted });
  }
  ctx.addShape(slide, { x: 630, y: 168, w: 480, h: 420, fill: C.navy });
  ctx.addText(slide, { text: "Roadmap razonable", x: 662, y: 198, w: 280, h: 30, size: 22, bold: true, color: C.white });
  box(slide, ctx, {
    x: 662,
    y: 252,
    w: 386,
    h: 82,
    title: "v1.1: robustez operativa",
    body: "Mejoras de UX, empaquetado offline, reporting de errores y cobertura adicional.",
    fill: "#FFFFFF10",
    accent: C.teal,
    dark: true,
  });
  box(slide, ctx, {
    x: 662,
    y: 358,
    w: 386,
    h: 82,
    title: "v2: reglas BDE externas",
    body: "Incorporar validaciones publicadas fuera de la taxonomia y trazabilidad documental.",
    fill: "#FFFFFF10",
    accent: C.amber,
    dark: true,
  });
  box(slide, ctx, {
    x: 662,
    y: 464,
    w: 386,
    h: 82,
    title: "v3: interoperabilidad",
    body: "iXBRL, exportaciones, comparativas y automatizacion de flujos de reporting.",
    fill: "#FFFFFF10",
    accent: C.blue,
    dark: true,
  });
  footer(slide, ctx);
  return slide;
}
