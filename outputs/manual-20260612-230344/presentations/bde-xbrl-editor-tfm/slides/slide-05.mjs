import { base, footer, metric, C } from "./theme.mjs";

export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, "Como se trabajo: Spec-Driven Development");
  const phases = [
    ["PRD", "Problema, usuarios, objetivos y criterios de exito"],
    ["spec.md", "Historias de usuario, requisitos y casos limite"],
    ["plan.md", "Contexto tecnico, arquitectura y decisiones"],
    ["data-model", "Entidades, servicios y relaciones"],
    ["contracts", "API esperada antes de implementar"],
    ["tasks.md", "Trabajo desglosado y verificable"],
  ];
  let x = 60;
  for (let i = 0; i < phases.length; i += 1) {
    ctx.addShape(slide, { x, y: 178, w: 170, h: 112, fill: i % 2 ? "#F1FBFA" : C.white, line: { style: "solid", fill: C.line, width: 1 } });
    ctx.addText(slide, { text: phases[i][0], x: x + 16, y: 204, w: 138, h: 24, size: 18, bold: true, color: i % 2 ? C.teal : C.blue, align: "center" });
    ctx.addText(slide, { text: phases[i][1], x: x + 14, y: 240, w: 142, h: 36, size: 10.5, color: C.muted, align: "center" });
    x += 190;
  }
  ctx.addShape(slide, { x: 86, y: 352, w: 1010, h: 1, fill: C.line });
  metric(slide, ctx, "6", "features especificadas de forma incremental", 126, 400, 170, C.blue);
  metric(slide, ctx, "248", "tareas marcadas como completadas en specs/", 378, 400, 210, C.teal);
  metric(slide, ctx, "100%", "trazabilidad de requisito a modulo y prueba", 674, 400, 220, C.amber);
  ctx.addText(slide, {
    text: "El enfoque reduce ambiguedad: antes de escribir codigo se fija que debe hacer cada feature, como se prueba y donde encaja en la arquitectura.",
    x: 126,
    y: 560,
    w: 920,
    h: 42,
    size: 19,
    bold: true,
    color: C.ink,
    align: "center",
  });
  footer(slide, ctx);
  return slide;
}
