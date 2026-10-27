import { C } from "./theme.mjs";

export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  await ctx.addImage(slide, {
    path: `${ctx.assetDir}/title-background.png`,
    x: 0,
    y: 0,
    w: ctx.W,
    h: ctx.H,
    fit: "cover",
    alt: "Abstract XBRL processing background",
  });
  ctx.addShape(slide, { x: 0, y: 0, w: 720, h: ctx.H, fill: "#0B1117DD" });
  ctx.addShape(slide, { x: 64, y: 86, w: 86, h: 6, fill: C.teal });
  ctx.addText(slide, {
    text: "BDE XBRL Editor",
    x: 64,
    y: 126,
    w: 620,
    h: 74,
    size: 48,
    bold: true,
    color: C.white,
    typeface: ctx.fonts.title,
  });
  ctx.addText(slide, {
    text: "Editor de escritorio para crear, editar, renderizar y validar informes XBRL orientados a taxonomias del Banco de Espana",
    x: 66,
    y: 216,
    w: 560,
    h: 92,
    size: 20,
    color: "#DCE7EF",
  });
  ctx.addText(slide, {
    text: "Trabajo Fin de Master",
    x: 66,
    y: 570,
    w: 360,
    h: 26,
    size: 16,
    bold: true,
    color: C.amber,
  });
  ctx.addText(slide, {
    text: "Python 3.13+ + PySide6 | XBRL 2.1 | Table Linkbase PWD | Formula 1.0 | pytest",
    x: 66,
    y: 602,
    w: 560,
    h: 22,
    size: 12,
    color: "#B7C4CF",
  });
  return slide;
}
