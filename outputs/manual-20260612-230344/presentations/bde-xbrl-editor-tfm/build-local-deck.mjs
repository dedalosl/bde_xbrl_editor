import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const WORKSPACE = "/Users/javiercobo/git/bde_xbrl_editor/outputs/manual-20260612-230344/presentations/bde-xbrl-editor-tfm";
const SLIDES_DIR = path.join(WORKSPACE, "slides");
const PREVIEW_DIR = path.join(WORKSPACE, "preview");
const LAYOUT_DIR = path.join(WORKSPACE, "layout");
const OUTPUT = path.join(WORKSPACE, "output", "bde-xbrl-editor-tfm.pptx");
const MANIFEST = path.join(WORKSPACE, "output", "artifact-build-manifest.json");
const ARTIFACT_TOOL = "/Users/javiercobo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const SPEAKER_NOTES = [
  "Abrir explicando que el proyecto no es solo una interfaz, sino una herramienta completa para cargar taxonomias, editar instancias, renderizar tablas y validar informes XBRL. Mencionar stack actual: Python 3.13+, PySide6, lxml, xmlschema y elementpath.",
  "Enfatizar el problema: XBRL exige coherencia entre conceptos, contextos, unidades, dimensiones y reglas. BDE anade particularidades: distribucion local de taxonomias y Table Linkbase PWD.",
  "Explicar el ciclo completo: cargar taxonomia, crear o abrir instancia, navegar tablas, editar hechos, guardar y validar. La propuesta de valor es un flujo local unificado.",
  "Presentar la arquitectura por capas. Mensaje clave: el core XBRL no depende de Qt; la UI consume servicios y modelos, pero la logica se puede probar de forma aislada.",
  "Explicar spec-driven development: PRD, spec, plan, data model, contratos y tareas. Hay seis features y 248 tareas completadas; esto da trazabilidad para un dominio complejo.",
  "Resumir capacidades: catalogo BDE con scraper TypeScript/Playwright, workspace de instancia, validacion/conformidad y distribucion offline con runtime del scraper preparado.",
  "Detallar el renderizado PWD: ejes X/Y/Z, coordenada de celda y mapeo a hechos. Recalcar que las tablas no estan hardcodeadas: salen de la taxonomia.",
  "Describir el pipeline de validacion: parser, checks estructurales, dimensionales, relaciones y formulas. El resultado es un ValidationReport con findings accionables.",
  "Mostrar calidad verificable: tests unitarios, integracion y runner offline de conformidad. Table Linkbase 1.0 es informativa porque v1 prioriza PWD por BDE.",
  "Usar esta slide como checklist de demo. No intentar demostrar todo; ensenar hilo completo: app, taxonomia, instancia, tabla, edicion, validacion y CLI si hay tiempo.",
  "Explicar limites como decisiones de alcance: iXBRL, envio BDE, batch/diferencial y reglas externas BDE quedan fuera de v1. Presentar roadmap incremental.",
  "Cerrar con tres ideas: producto real, arquitectura sostenible y metodo defendible. Frase final: convertir complejidad XBRL/BDE en un flujo visual, verificable y mantenible.",
];

function normalizeFrame(options) {
  const left = options.left ?? options.x ?? 0;
  const top = options.top ?? options.y ?? 0;
  const width = options.width ?? options.w;
  const height = options.height ?? options.h;
  if (!Number.isFinite(width) || !Number.isFinite(height)) {
    throw new Error("Frame requires finite width and height.");
  }
  return { left, top, width, height };
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function saveBlobToFile(blob, outputPath) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, Buffer.from(await blob.arrayBuffer()));
}

function createSlideContext(artifact, slideNumber) {
  const transparent = "#00000000";
  const ctx = {
    W: 1280,
    H: 720,
    slideSize: { width: 1280, height: 720 },
    slideNumber,
    outputDir: path.join(WORKSPACE, "output"),
    assetDir: path.join(WORKSPACE, "assets"),
    workspaceDir: WORKSPACE,
    fonts: {
      title: "Aptos Display",
      body: "Aptos",
      mono: "Aptos Mono",
    },
    artifact,
    addShape(slide, optionsForShape) {
      const {
        geometry = "rect",
        fill = transparent,
        line = { style: "solid", fill: transparent, width: 0 },
        name,
        ...frameOptions
      } = optionsForShape;
      return slide.shapes.add({
        geometry,
        name,
        position: normalizeFrame(frameOptions),
        fill,
        line,
      });
    },
    addText(slide, optionsForText) {
      const {
        text = "",
        size,
        fontSize = size ?? 24,
        color = "#111827",
        bold = false,
        face,
        typeface = face ?? ctx.fonts.body,
        align = "left",
        valign = "top",
        fill = transparent,
        line = { style: "solid", fill: transparent, width: 0 },
        insets = { left: 0, right: 0, top: 0, bottom: 0 },
        name,
        lineSpacing,
        ...frameOptions
      } = optionsForText;
      const shape = ctx.addShape(slide, { ...frameOptions, name, geometry: "rect", fill, line });
      shape.text = text;
      shape.text.fontSize = fontSize;
      shape.text.color = color;
      shape.text.bold = Boolean(bold);
      shape.text.typeface = typeface;
      shape.text.alignment = align;
      shape.text.verticalAlignment = valign;
      shape.text.insets = insets;
      if (lineSpacing !== undefined) {
        shape.text.lineSpacing = lineSpacing;
      }
      return shape;
    },
    async addImage(slide, optionsForImage) {
      const {
        path: imagePath,
        blob,
        dataUrl,
        uri,
        fit = "cover",
        alt = "",
        name,
        ...frameOptions
      } = optionsForImage;
      const source = blob
        ? { blob }
        : dataUrl
          ? { dataUrl }
          : uri
            ? { uri }
            : { blob: await readImageBlob(imagePath) };
      const image = slide.images.add({ ...source, fit, alt, name });
      image.position = normalizeFrame(frameOptions);
      return image;
    },
  };
  return ctx;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

async function main() {
  const artifact = await import(pathToFileURL(ARTIFACT_TOOL).href);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  const modules = (await fs.readdir(SLIDES_DIR))
    .filter((entry) => /^slide-\d+\.mjs$/.test(entry))
    .sort();

  for (const [index, entry] of modules.entries()) {
    const slideNumber = index + 1;
    const modulePath = path.join(SLIDES_DIR, entry);
    const module = await import(`${pathToFileURL(modulePath).href}?mtime=${Date.now()}`);
    const fn = module[`slide${pad(slideNumber)}`];
    if (typeof fn !== "function") {
      throw new Error(`Missing export slide${pad(slideNumber)} in ${entry}`);
    }
    const slide = await fn(presentation, createSlideContext(artifact, slideNumber));
    const createdSlide = slide || presentation.slides.getItem(presentation.slides.count - 1);
    createdSlide.speakerNotes.setText(SPEAKER_NOTES[index] || "");
  }

  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });
  const previewPaths = [];
  for (let index = 0; index < presentation.slides.count; index += 1) {
    const slide = presentation.slides.getItem(index);
    const previewPath = path.join(PREVIEW_DIR, `slide-${pad(index + 1)}.png`);
    const preview = await presentation.export({ slide, format: "png", scale: 1 });
    await saveBlobToFile(preview, previewPath);
    previewPaths.push(previewPath);
    const layout = await presentation.export({ slide, format: "layout" });
    await fs.writeFile(path.join(LAYOUT_DIR, `slide-${pad(index + 1)}.layout.json`), await layout.text(), "utf8");
  }

  const pptx = await PresentationFile.exportPptx(presentation);
  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await pptx.save(OUTPUT);
  const stat = await fs.stat(OUTPUT);
  const manifest = {
    output: OUTPUT,
    outputBytes: stat.size,
    slideCount: presentation.slides.count,
    slideSize: { width: 1280, height: 720 },
    previewDir: PREVIEW_DIR,
    previewPaths,
  };
  await fs.writeFile(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
