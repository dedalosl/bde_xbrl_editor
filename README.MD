# BDE XBRL Editor

BDE XBRL Editor es una aplicacion de escritorio para cargar taxonomias XBRL, crear y editar documentos instancia, renderizar tablas regulatorias y validar informes financieros orientados a taxonomias del Banco de Espana.

El proyecto nace como Trabajo de Fin de Master y tiene como objetivo construir una herramienta real, mantenible y verificable para un dominio tecnico exigente: el reporting financiero en XBRL. La aplicacion combina una interfaz PySide6 con un nucleo Python independiente de Qt, de forma que la logica de taxonomias, instancias, renderizado y validacion pueda probarse automaticamente sin depender de la interfaz grafica.

## Estado del proyecto

Version actual: `0.1.0`.

El repositorio contiene:

- Aplicacion de escritorio ejecutable con `bde-xbrl-editor` o `python -m bde_xbrl_editor`.
- Carga y cache de taxonomias XBRL desde entry points locales.
- Soporte para linkbases de etiquetas, presentacion, calculo, definicion, tablas y formulas.
- Catalogo de taxonomias BDE y deteccion de cambios mediante un scraper TypeScript/Playwright incluido en el paquete.
- Creacion, apertura, edicion y guardado de documentos instancia XBRL.
- Renderizado de tablas XBRL basado en Table Linkbase PWD, utilizado por BDE.
- Validacion estructural, dimensional, de calculo y formulas.
- Runner CLI para suites de conformidad XBRL.
- Tests unitarios e integracion con `pytest` y `pytest-qt`.

## Stack tecnologico

- Lenguaje: Python 3.13+
- Interfaz grafica: PySide6
- XML/XSD: lxml y xmlschema
- XPath 2.0 y formulas XBRL: elementpath
- Cache en memoria: cachetools
- Scraper de catalogo BDE: TypeScript, Playwright, ts-node y npm
- Empaquetado: pyproject.toml con setuptools y estructura `src/`
- Testing: pytest, pytest-qt y pytest-benchmark
- Linting y formateo: ruff

## Instalacion

Requisitos previos:

- Python 3.13 o superior.
- Node.js 20 LTS o superior con npm. Es necesario para instalar y ejecutar el scraper BDE incluido; TypeScript, ts-node y Playwright se instalan como dependencias npm locales.
- Entorno virtual recomendado.
- En macOS, Linux o Windows con soporte grafico para ejecutar PySide6.

### Ejecucion local recomendada

Para desarrollo y pruebas locales, usar los scripts del repositorio. Crean el entorno virtual si hace falta, instalan la aplicacion Python en editable, preparan las dependencias npm del scraper BDE y lanzan la aplicacion con `python -m bde_xbrl_editor`.

En macOS o Linux:

```bash
./run.sh
```

En Windows, desde `cmd.exe`:

```bat
run.bat
```

### Instalacion manual

Crear y activar un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

En Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Instalar el proyecto en modo editable con dependencias de desarrollo:

```bash
pip install -e ".[dev]"
```

Preparar las dependencias npm del scraper BDE incluido:

```bash
python -m bde_xbrl_editor.taxonomy_catalog.scraper --setup-only
```

## Ejecucion

Lanzar la aplicacion de escritorio:

```bash
bde-xbrl-editor
```

Tambien puede ejecutarse como modulo Python:

```bash
python -m bde_xbrl_editor
```

Actualizar el catalogo BDE con el scraper incluido:

```bash
bde-xbrl-catalog-scrape
```

El scraper genera por defecto `~/.bde_xbrl_editor/taxonomies.json`. Tambien puede indicarse una ruta concreta:

```bash
bde-xbrl-catalog-scrape --output /ruta/a/taxonomies.json
```

Flujo principal de uso:

1. Abrir una taxonomia XBRL desde `File > Open Taxonomy`.
2. Explorar conceptos, tablas, etiquetas, validaciones y metadatos desde la interfaz.
3. Crear una instancia nueva con `File > New Instance` o abrir una existente con `File > Open Instance`.
4. Editar hechos desde las tablas renderizadas.
5. Guardar la instancia con `File > Save` o `File > Save As`.
6. Ejecutar validaciones con `Validation > Validate Instance`.
7. Exportar resultados de validacion desde el panel de validacion.

## Comandos de desarrollo

Ejecutar todos los tests:

```bash
pytest
```

Ejecutar tests con cobertura:

```bash
pytest --cov=bde_xbrl_editor
```

Ejecutar lint:

```bash
ruff check .
```

Formatear el codigo:

```bash
ruff format .
```

## Distribucion y empaquetado

Hay dos formas de distribuir la aplicacion.

La distribucion Python normal (`wheel` o `sdist`) se genera desde `pyproject.toml`. Incluye el scraper BDE en TypeScript y un catalogo JSON inicial, pero no incluye `node_modules` ni los navegadores de Playwright. En este modo, la maquina donde se instale debe tener Python 3.13+ y Node.js/npm.

Despues de instalar la aplicacion, el scraper se prepara con:

```bash
python -m bde_xbrl_editor.taxonomy_catalog.scraper --setup-only
```

Este comando crea una copia de trabajo en `~/.bde_xbrl_editor/bde_taxonomies_scraper` e instala alli las dependencias npm. Los scripts `run.sh` y `run.bat` ejecutan este paso automaticamente.

Tambien puede generarse un paquete standalone/offline con PyInstaller:

```bash
pip install -e ".[dev,build]"
python scripts/build_offline_package.py
```

Este build prepara un runtime del scraper con `node_modules`, Chromium de Playwright y una copia de Node.js. El resultado queda en `dist/offline/<plataforma>/` con el ejecutable y `offline-runtime/`, y tambien se genera un `.zip` distribuible en la misma carpeta padre. Ese paquete no necesita Node.js/npm instalado en la maquina destino.

Por defecto no copia el directorio local `cache/`, porque puede ser muy grande. Si se necesita un paquete tambien offline para taxonomias ya cacheadas, usar:

```bash
python scripts/build_offline_package.py --include-cache
```

## Runner de conformidad XBRL

El proyecto incluye un runner CLI para validar el procesador contra suites de conformidad XBRL.

Ejecutar todas las suites disponibles:

```bash
python -m bde_xbrl_editor.conformance
```

Ejecutar una suite concreta:

```bash
python -m bde_xbrl_editor.conformance --suite xbrl21
python -m bde_xbrl_editor.conformance --suite dimensions
python -m bde_xbrl_editor.conformance --suite formula
python -m bde_xbrl_editor.conformance --suite table-linkbase
```

Generar un informe JSON:

```bash
python -m bde_xbrl_editor.conformance --suite xbrl21 --verbose --output-file report.json
```

Las suites bloqueantes son XBRL 2.1, Dimensions 1.0 y Formula 1.0. La suite Table Linkbase 1.0 se trata como informativa porque la version objetivo de la aplicacion implementa Table Linkbase PWD, que es la variante usada por BDE, si bien se ha intentado dar soporte a la version 1.0 también para pasar todas las pruebas de la conformance suite.

Los datos reales de conformidad se esperan bajo `conformance/`. Para uso manual del runner, puede crearse una estructura compatible con enlaces simbolicos:

```bash
mkdir -p tests/conformance/suite-data
ln -sfn "$(pwd)/conformance/XBRL-CONF-2025-07-16" tests/conformance/suite-data/xbrl-2.1
ln -sfn "$(pwd)/conformance/XBRL-XDT-CONF-2025-09-09" tests/conformance/suite-data/dimensions-1.0
ln -sfn "$(pwd)/conformance/table-linkbase-conformance-2024-12-17" tests/conformance/suite-data/table-linkbase-1.0
ln -sfn "$(pwd)/conformance/formula-conformance-2022-07-21" tests/conformance/suite-data/formula-1.0
```

Tambien se pueden ejecutar las pruebas de integracion, que preparan esos enlaces dinamicamente:

```bash
python -m pytest tests/integration/conformance/ -v -k "not slow"
```

## Estructura del proyecto

```text
.
├── docs/
│   ├── Documentacion-TFM.pdf
│   ├── xbrl-processor-prd.md
│   └── conformance-xbrl21-validator-roadmap.md
├── specs/
│   ├── 001-taxonomy-loading-cache/
│   ├── 002-xbrl-instance-creation/
│   ├── 003-table-rendering-pwd/
│   ├── 004-instance-editing/
│   ├── 005-instance-validation/
│   └── 006-conformance-suite-runner/
├── src/
│   └── bde_xbrl_editor/
│       ├── conformance/
│       ├── instance/
│       ├── table_renderer/
│       ├── taxonomy/
│       ├── taxonomy_catalog/
│       ├── ui/
│       └── validation/
├── test_data/
├── tests/
│   ├── integration/
│   └── unit/
├── pyproject.toml
├── run.bat
├── run.sh
└── README.MD
```

### Modulos principales

`taxonomy/`: descubrimiento DTS, resolucion de esquemas, cache, modelos de conceptos, etiquetas, linkbases y dimensiones.

`taxonomy_catalog/`: modelos y utilidades para cargar, filtrar, ordenar y detectar cambios en el catalogo de taxonomias BDE; incluye el wrapper Python y el scraper TypeScript/Playwright.

`instance/`: modelos de instancias XBRL, contextos, unidades, hechos, filing indicators, parser, serializer, factory, editor y validacion de tipos.

`table_renderer/`: motor de layout de tablas, modelos de cabeceras/celdas, mapeo de hechos y formateo de valores para vistas tabulares.

`validation/`: validadores estructurales, dimensionales, de relaciones, calculo y formulas; modelos de resultados y exportacion de informes.

`conformance/`: parser, executor, runner y reporters para suites de conformidad XBRL.

`ui/`: ventana principal, tema visual, dialogos y widgets PySide6 para carga, edicion, tablas, paneles de informacion y validacion.

## Funcionalidades principales

### Carga de taxonomias

- Apertura de taxonomias XBRL desde entry points locales.
- Resolucion de imports, includes y referencias a linkbases.
- Cache de estructuras de taxonomia ya cargadas.
- Procesamiento de linkbases de etiquetas estandar y genericas.
- Procesamiento de linkbases de presentacion, calculo, definicion, tablas y formulas.
- Soporte para metadatos de taxonomia, idiomas declarados y etiquetas por rol.

### Catalogo BDE

- Carga de informacion de taxonomias del Banco de Espana.
- Scraper TypeScript/Playwright incluido y ejecutable desde `bde-xbrl-catalog-scrape`.
- Agrupacion por categoria, estado y linea temporal.
- Filtrado por taxonomias vigentes y no vigentes.
- Deteccion de recursos actualizados desde la ultima revision.

### Creacion y edicion de instancias

- Wizard para crear nuevas instancias XBRL.
- Definicion de entidad, periodo, dimensiones y ubicacion de guardado.
- Apertura de instancias existentes.
- Edicion de hechos desde tablas renderizadas.
- Preservacion de hechos huerfanos cuando la instancia contiene conceptos no presentes en la taxonomia cargada.
- Guardado y guardado como XML/XBRL.

### Renderizado de tablas

- Descubrimiento de tablas definidas en la taxonomia.
- Calculo de layout para filas, columnas y ejes Z.
- Cabeceras multinivel y coordenadas dimensionales por celda.
- Mapeo de hechos de la instancia a celdas renderizadas.
- Distincion de celdas vacias, celdas con valores y duplicados.
- Preferencia de idioma para etiquetas de tabla.

### Validacion

- Validacion estructural XBRL.
- Validacion de tipos de datos de hechos.
- Validacion dimensional contra hipercubos, dimensiones y miembros permitidos.
- Validacion de calculo mediante relaciones summation-item.
- Validacion essence-alias.
- Evaluacion de assertions de Formula 1.0 con soporte XPath 2.0 mediante elementpath.
- Panel de resultados con severidades, mensajes, navegacion a celdas y exportacion.

### Arquitectura testable

- Las capas core (`taxonomy/`, `instance/`, `validation/`, `table_renderer/`) no dependen de PySide6.
- Los modelos de dominio principales se definen como dataclasses inmutables.
- Los validadores no propagan excepciones al usuario: devuelven findings o informes de validacion.
- Los valores de hechos se almacenan como `str` para evitar perdida de precision.

## Convenciones tecnicas

- Los valores de hechos XBRL se almacenan siempre como `str`; no se usan `float` para importes o decimales.
- Los QNames internos usan notacion Clark: `{namespace}local_name`.
- Los modelos de dominio son inmutables cuando representan estructuras ya construidas.
- La UI PySide6 queda aislada en `src/bde_xbrl_editor/ui/`.
- La variante de Table Linkbase prioritaria es PWD, por compatibilidad con BDE.
- Los errores de validacion se reportan como `ValidationFinding` en lugar de interrumpir el flujo.

## Entrega TFM

Documentacion: este archivo `README.MD`.

Codigo fuente: pendiente de completar con la URL del repositorio publico o privado.

```text
URL del codigo: [https://github.com/dedalosl/bde_xbrl_editor](https://github.com/dedalosl/bde_xbrl_editor)
```

Despliegue o publicacion: al tratarse de una aplicacion de escritorio, la ejecucion principal es local mediante los comandos documentados en la seccion de ejecucion. Si se publica un instalador, release o artefacto descargable, debe indicarse aqui.

```text
URL de despliegue/publicacion: PENDIENTE_DE_COMPLETAR
```

Slides de presentacion: pendiente de completar con la URL de Google Slides, PowerPoint, Canva o con el archivo de presentacion incluido en el repositorio.

```text
URL de slides: PENDIENTE_DE_COMPLETAR
```

## Licencia

Pendiente de definir.
