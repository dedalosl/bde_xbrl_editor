import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
import {finalizePresentation} from '/Users/javiercobo/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations/container_tools/artifact_tool_utils.mjs';
const ref='/Users/javiercobo/.codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-project-kickoff/assets/reference.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(ref));
const changes={
'7qp4be9c':'BDE XBRL\nEditor','ts7md4r2':'Aplicación de escritorio para informes financieros','k3yl0zql':'Trabajo fin de máster',
'ozy1ofad':'Contenido de la defensa',
'507y1gbi':'El problema del reporting XBRL',
'cza94vmx':'Un dominio exigente\nCada informe combina hechos, contextos, unidades y dimensiones. Las taxonomías definen conceptos, relaciones y restricciones que el editor debe respetar.',
'd0jax03i':'Una herramienta integrada\nEl proyecto reúne la carga de taxonomías, la edición de instancias y la validación en una aplicación orientada al Banco de España.',
'ozydc3u9':'Objetivo y alcance del trabajo',
'fapwfyds':'Aplicación real\nCrear una herramienta de escritorio utilizable para preparar informes XBRL y explorar taxonomías BDE.',
'0ba143al':'Núcleo verificable\nSeparar la lógica del dominio de Qt para probar taxonomías, instancias y validación automáticamente.',
'1cj2d8b6':'Alcance acotado\nCargar taxonomías existentes. Sin edición de taxonomías, colaboración en nube ni envío automático a portales.',
'sna103ap':'PRODUCTO','3ihk3et8':'INGENIERÍA','ih8ju9sn':'LÍMITES',
'cf2tcr61':'Arquitectura y tecnología',
'w32dkbuh':'Interfaz de escritorio\nPySide6 presenta tablas, asistentes y resultados. La interfaz queda aislada del núcleo del procesador.',
'x4vedgvm':'Procesamiento XBRL\nPython, lxml y xmlschema resuelven esquemas e instancias. elementpath aporta XPath 2.0 para fórmulas.',
'z2tcnm5s':'Servicios y modelos\nTaxonomías, instancias, renderizado y validación tienen responsabilidades separadas. Los modelos principales son inmutables.',
'yhkbe1o7':'Catálogo y distribución\nTypeScript y Playwright actualizan el catálogo BDE. setuptools empaqueta Python y PyInstaller permite preparar un paquete offline.',
'rapgbaxw':'Integridad de los datos',
'47yh0ve5':'Precisión financiera\ny edición segura',
'v2tcn650':'Los hechos conservan sus valores como texto. El editor evita convertir importes a float y mantiene la precisión original del documento XBRL.\n\nLos QNames usan notación Clark para identificar conceptos por su espacio de nombres.',
'ml07i9sv':'Separador decimal\nLa interfaz admite punto o coma. La preferencia cambia la visualización, no el contenido XBRL.',
'oryp8fah':'Conservación de hechos\nEl editor preserva hechos huérfanos y distingue valores duplicados o celdas excluidas.',
 'tsjad0z2':'Capacidades del editor',
'dcbud0ra':'El flujo reúne la preparación del informe en una sola aplicación. El usuario puede inspeccionar la taxonomía y trabajar sobre sus tablas regulatorias.',
'25ojml43':'Taxonomías','xcz2l03q':'Carga desde entry points locales, caché y linkbases de etiquetas, relaciones, tablas y fórmulas.',
'o761ov2t':'Instancias','p8fih03e':'Asistente de creación, apertura, edición de hechos y guardado de documentos XML/XBRL.',
'eh4jil4r':'Tablas PWD','f2d0b6lc':'Cabeceras multinivel y ejes Z. El motor asigna hechos a coordenadas dimensionales.',
'jedkn654':'Validación','id4ju1oz':'Hallazgos con severidad, navegación a celdas y exportación del informe de resultados.',
'98rehwve':'Demostración del flujo de trabajo',
'id0fu50z':'PASO 1','n6pwfmd8':'PASO 2','0jydkreh':'PASO 3',
'1k7edwv2':'Carga\nAbrir una taxonomía y explorar conceptos, tablas y etiquetas disponibles.',
'je9g3ahk':'Edición\nCrear o abrir una instancia. Introducir hechos en las tablas y guardar el informe.',
'lgbepgvm':'Comprobación\nValidar la instancia, revisar hallazgos y exportar el informe de validación.',
'0b65obm9':'Verificación y límites de la evidencia',
'cnu1kzyd':'Evidencia disponible\nEl repositorio documenta pruebas unitarias e integración y un runner de conformidad. No aporta aquí una medición final de conformidad ni resultados de usabilidad.',
'3y107axw':'3','nex4jq5k':'1','mdonql4z':'100%',
'oza1gfyh':'Suites bloqueantes: XBRL 2.1, Dimensions y Formula.',
'2xsjepgb':'Suite informativa: Table Linkbase 1.0, distinta del PWD de BDE.',
'p0ji9kf2':'Objetivo del PRD. No se presenta como resultado alcanzado.',
'k7q50v2x':'Plan propuesto en el PRD',
's7yt4b21':'Motor y descubrimiento DTS','m1cnetkj':'Creación y edición de instancias','725onyl4':'Validación dimensional','ydcnatkn':'Tablas y fórmulas','kzu5c32t':'Pruebas con usuarios','l036l83y':'Conformidad y pruebas de regresión',
'4fmh8fat':'Preparación de la entrega del TFM',
'xcryxg7y':'README disponible','250zy18b':'Código en repositorio','98rytw72':'Ejecución local','61kzalof':'Conformidad por medir','ofqtgnyt':'Publicación pendiente','0b6tc3yx':'Presentación editable',
'ra943il8':'BDE XBRL\nEditor','dcbm583y':'Conclusiones y preguntas','0f2lgnmp':'Trabajo fin de máster'
};
for(const [id,text] of Object.entries(changes)){p.resolve('sh/'+id).text=text;}
const agenda=p.resolve('tb/6hg3ylc3');
const a=[['01','Problema y objetivo','Contexto'],['02','Arquitectura y tecnología','Diseño'],['03','Integridad y capacidades','Aplicación'],['04','Demostración del flujo','Uso'],['05','Verificación y límites','Evidencia'],['06','Plan y entrega del TFM','Cierre']];
for(let r=0;r<6;r++)for(let c=0;c<3;c++)agenda.cells.set(r,c,a[r][c]);
const gantt=p.resolve('tb/mxgvador'); for(let c=0;c<5;c++)gantt.cells.set(0,c,['Sem. 1–3','Sem. 4–5','Sem. 6–9','Sem. 10–13','Entrega'][c]);
p.resolve('sh/m1cnetkj').position={left:400,top:283.31,width:550,height:53.89};p.resolve('sh/725onyl4').position={left:400,top:357.29,width:550,height:53.89};p.resolve('sh/ydcnatkn').position={left:760,top:431.26,width:459,height:53.89};
const cal=p.resolve('tb/up4zmdcb');for(let r=0;r<5;r++)for(let c=0;c<5;c++)cal.cells.set(r,c,r===0?['Documentación','Código','Ejecución','Validación','Entrega'][c]:'');

p.resolve('sh/250zy18b').position={left:296.27,top:187.77,width:210.4,height:35.69};
p.resolve('sh/0b6tc3yx').position={left:1013.27,top:187.77,width:210.4,height:35.69};
p.resolve('sh/61kzalof').position={left:773.6,top:446.98,width:210.4,height:35.69};
p.resolve('sh/ofqtgnyt').position={left:534.93,top:446.98,width:210.4,height:35.69};
for(let c=0;c<5;c++){cal.cells.set(2,c,['Instalación y uso','GitHub','Python y PySide6','Runner CLI','Archivo PPTX'][c]);cal.cells.set(4,c,['Actualizar enlaces','Acceso al evaluador','Paquete offline','Informe final','Formulario'][c]);}
const im=p.resolve('im/7ut4nih0'); const b=await fs.readFile('illustration.png'); im.replace({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',alt:'Ilustración conceptual de documentos y tablas financieras. No representa la interfaz del editor.',fit:'cover'}); im.crop={left:0,top:0,right:0,bottom:0};
// Keep imported typography and geometry. Repair only source title/content overlap.
p.resolve('sh/cnu1kzyd').position={left:41.33,top:155,width:1197.33,height:140};
p.resolve('sh/18byd4zy').position={left:35.46,top:354.2,width:1203,height:0.03};
const notes=[
'Fuente: README.MD, descripción general y estado del proyecto. No se identifica autor, institución ni fecha de defensa en las fuentes utilizadas.',
'Estructura de la defensa basada en README.MD y docs/Documentacion-TFM.pdf.',
'Fuentes: README.MD, introducción y funcionalidades. docs/xbrl-processor-prd.md, Problem Statement. Ilustración conceptual generada con ImageGen, no es una captura de la aplicación.',
'Fuentes: docs/Documentacion-TFM.pdf, objetivo. README.MD, arquitectura testable. docs/xbrl-processor-prd.md, Goals y Non-Goals.',
'Fuente: README.MD, Stack tecnológico, módulos principales, arquitectura testable y distribución. El README actual exige Python 3.13+, frente a otras guías antiguas. Se omite la versión para evitar mezclar estados.',
'Fuente: README.MD, Separador decimal de la interfaz, Convenciones técnicas y Creación y edición de instancias.',
'Fuente: README.MD, Funcionalidades principales. Capacidad documentada, no afirmación de certificación normativa.',
'Fuente: README.MD, Flujo principal de uso. Guion de demostración recomendado, no resultado de una sesión de ejecución.',
'Fuentes: README.MD, Verificación rápida y Runner de conformidad. docs/xbrl-processor-prd.md, Success Metrics. El 100% es un objetivo de aceptación, no una medición alcanzada. docs/conformance-xbrl21-validator-roadmap.md menciona unas 199 fallas obligatorias en una comprobación anterior sin fecha ni informe adjunto. No se usa ese valor como estado actual. Una batería pytest verde no certifica conformidad XBRL.',
'Fuente: docs/xbrl-processor-prd.md, Timeline Considerations. Es un plan sugerido de 13 semanas, no una cronología ejecutada. El PRD es borrador del 24/03/2026 y su objetivo Q2 2026 no acredita finalización. Barras heredadas de la plantilla, orientativas y sin medición de duración real.',
'Fuentes: docs/Documentacion-TFM.pdf, Requisitos y Entrega. README.MD, Entrega TFM. Código: https://github.com/dedalosl/bde_xbrl_editor. El README mantiene la publicación pendiente. Presentación entregada como documento adjunto en el repositorio. No se inventa fecha límite ni identidad del alumno.',
'Conclusión: el trabajo documenta una aplicación de escritorio que aborda el ciclo de preparación de informes XBRL y un núcleo separado de Qt. Queda por medir conformidad final y evaluación con usuarios. Fuentes: README.MD y docs/xbrl-processor-prd.md.'
];
for(let i=0;i<p.slides.items.length;i++){p.slides.items[i].speakerNotes.text=notes[i];}
for(let i=0;i<p.slides.items.length;i++){await fs.writeFile(`final-${i+1}.png`,new Uint8Array(await(await p.export({slide:p.slides.items[i],format:'png',scale:1})).arrayBuffer()));}
await fs.writeFile('final-montage.webp',new Uint8Array(await(await p.export({format:'webp',montage:true})).arrayBuffer()));
await (await PresentationFile.exportPptx(p)).save('candidate.pptx');
const skill='/Users/javiercobo/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const result=await finalizePresentation({workspaceDir:'/Users/javiercobo/git/bde_xbrl_editor/output/tfm',candidatePath:'/Users/javiercobo/git/bde_xbrl_editor/output/tfm/.build/candidate.pptx',finalPath:'/Users/javiercobo/git/bde_xbrl_editor/output/tfm/final/BDE-XBRL-Editor-TFM-v3.pptx',pythonExecutable:'/Users/javiercobo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','2','--require-native-table-slide','10','--require-native-table-slide','11'],fontPolicy:{basis:'reference',families:['Inter','Inter Medium','Inter SemiBold','Helvetica Neue','Helvetica Neue Medium'],referencePath:ref,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(ref)).digest('hex')},requiredNativeTableOwnerSlides:[2,10,11],verifyArtifactToolImport:true,receiptPath:'/Users/javiercobo/git/bde_xbrl_editor/output/tfm/.build/validation-v3.json'});console.log(JSON.stringify(result));
