export const C = {
  ink: "#17212B",
  muted: "#566575",
  pale: "#F6F8FA",
  line: "#D7DEE6",
  navy: "#15395B",
  blue: "#2B6EA6",
  teal: "#15807A",
  amber: "#D59B2D",
  red: "#B94A48",
  green: "#3E8B5B",
  white: "#FFFFFF",
  black: "#0B1117",
};

export function base(slide, ctx, title, kicker = "BDE XBRL Editor") {
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: C.pale });
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: 7, fill: C.teal });
  ctx.addText(slide, {
    text: kicker.toUpperCase(),
    x: 64,
    y: 34,
    w: 430,
    h: 22,
    size: 12,
    bold: true,
    color: C.teal,
    typeface: ctx.fonts.body,
  });
  ctx.addText(slide, {
    text: title,
    x: 64,
    y: 58,
    w: 760,
    h: 56,
    size: 31,
    bold: true,
    color: C.ink,
    typeface: ctx.fonts.title,
  });
  ctx.addText(slide, {
    text: String(ctx.slideNumber).padStart(2, "0"),
    x: 1168,
    y: 42,
    w: 48,
    h: 24,
    size: 12,
    bold: true,
    color: C.muted,
    align: "right",
  });
}

export function footer(slide, ctx, text = "Trabajo Fin de Master | Python 3.13+ + PySide6 | XBRL / BDE") {
  ctx.addShape(slide, { x: 64, y: 676, w: 1090, h: 1, fill: C.line });
  ctx.addText(slide, {
    text,
    x: 64,
    y: 686,
    w: 720,
    h: 18,
    size: 9,
    color: C.muted,
  });
}

export function darkFooter(slide, ctx, text = "Trabajo Fin de Master | Python 3.13+ + PySide6 | XBRL / BDE") {
  ctx.addShape(slide, { x: 64, y: 676, w: 1090, h: 1, fill: "#314252" });
  ctx.addText(slide, {
    text,
    x: 64,
    y: 686,
    w: 720,
    h: 18,
    size: 9,
    color: "#9CADBC",
  });
}

export function topRule(slide, ctx, color = C.teal) {
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: 7, fill: color });
}

export function label(slide, ctx, text, x, y, w, color = C.muted) {
  return ctx.addText(slide, {
    text,
    x,
    y,
    w,
    h: 20,
    size: 11,
    bold: true,
    color,
  });
}

export function box(slide, ctx, { x, y, w, h, title, body, fill = C.white, accent = C.blue, dark = false }) {
  ctx.addShape(slide, {
    x,
    y,
    w,
    h,
    fill,
    line: { style: "solid", fill: dark ? "#FFFFFF33" : C.line, width: 1 },
  });
  ctx.addShape(slide, { x, y, w: 5, h, fill: accent });
  ctx.addText(slide, {
    text: title,
    x: x + 18,
    y: y + 16,
    w: w - 30,
    h: 26,
    size: 17,
    bold: true,
    color: dark ? C.white : C.ink,
  });
  ctx.addText(slide, {
    text: body,
    x: x + 18,
    y: y + 48,
    w: w - 30,
    h: h - 58,
    size: 12.5,
    color: dark ? "#DCE7EF" : C.muted,
    lineSpacing: 1.08,
  });
}

export function pill(slide, ctx, text, x, y, w, fill, color = C.white) {
  ctx.addShape(slide, { x, y, w, h: 30, fill, line: { style: "solid", fill, width: 0 } });
  ctx.addText(slide, {
    text,
    x: x + 10,
    y: y + 7,
    w: w - 20,
    h: 16,
    size: 10.5,
    bold: true,
    color,
    align: "center",
  });
}

export function arrow(slide, ctx, x1, y1, x2, y2, color = C.blue) {
  const horizontal = Math.abs(x2 - x1) >= Math.abs(y2 - y1);
  if (horizontal) {
    const left = Math.min(x1, x2);
    const y = y1 - 1.5;
    ctx.addShape(slide, { x: left, y, w: Math.abs(x2 - x1) - 12, h: 3, fill: color });
    ctx.addShape(slide, { x: x2 - 12, y: y1 - 7, w: 13, h: 13, fill: color, geometry: "triangle" });
  } else {
    const top = Math.min(y1, y2);
    const x = x1 - 1.5;
    ctx.addShape(slide, { x, y: top, w: 3, h: Math.abs(y2 - y1) - 12, fill: color });
    ctx.addShape(slide, { x: x1 - 7, y: y2 - 12, w: 13, h: 13, fill: color, geometry: "triangle" });
  }
}

export function metric(slide, ctx, value, labelText, x, y, w, color = C.blue) {
  ctx.addText(slide, { text: value, x, y, w, h: 42, size: 34, bold: true, color, typeface: ctx.fonts.title });
  ctx.addText(slide, { text: labelText, x, y: y + 43, w, h: 36, size: 11.5, color: C.muted });
}
