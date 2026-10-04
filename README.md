# meowrhino — sitio recuperado (TFG + portfolio)

Copia **estática y editable** de **meowrhino.cargo.site**, recuperada y reconstruida
sin depender de Cargo (el sitio original quedó privado al no renovar el pago).

A diferencia de una exportación bruta de Cargo, estas páginas se reescribieron a
**HTML/CSS limpio y legible**: sin el motor JavaScript de Cargo, sin JSON incrustado
y sin plantillas. Puedes abrir cualquier `.html` y editar el texto, los enlaces o las
imágenes directamente.

## Estructura

```
index.html            portada: selector de idioma (hola / bon dia / hello)
home_1_esp|eng|cat    portada por idioma
about_*               sobre mí
portfolio_*           portfolio (sets que apilan los proyectos)
UX-UI_* objeto_* interaccion_*   páginas de proyecto
CV_design_*           currículum
tfg.html              el TFG escrito completo
tablitas/             las tablitas, fuera de Google (ver abajo)
sobres/               los 112 sobres, comprimidos, con visor (sobres/#nombre)
404.html              página de error
assets/
  css/
    foundation.css    base de Cargo (rejilla, tipografía, galerías) — legible
    base.css          hoja de estilos del sitio (colores, tipos)
    galleries.css     layout estático de galerías, rejilla, marquee y menús fijados (nuestro)
  freight/            imágenes (convertidas a WebP, optimizadas)
  files/              vídeos, audios y PDFs
  type/               fuente YoungSerif
tools/                cómo se reconstruyó (scripts + volcado de contenido)
```

Cada página: `<head>` con los 3 CSS + un `<style>` con el CSS propio de esa página,
y `<body>` con el contenido dentro de `bodycopy.page_content`. Para editar un texto,
busca la palabra en el `.html` y cámbiala.

## Navegación

- portada (`index.html`) → `home_1_*` por idioma, con selector de idioma abajo y enlace al TFG.
- `portfolio_*` y cada proyecto llevan abajo el menú «inicio · todo · UX/UI · objeto · interacción».
- `tfg.html` lleva fija abajo a la derecha «inicio · tablitas · sobres».
- En Cargo esos menús eran páginas «fijadas»; aquí están copiadas dentro de cada página
  (`<div class="page pinned-overlay|pinned-fixed">`), así que si cambias uno, cámbialo en todas.

## Editar

- **Texto / enlaces**: edita directamente el HTML de la página.
- **Estilos globales**: `assets/css/base.css`.
- **Estilo de una página concreta**: el bloque `<style>` al final de su `<head>`
  (va con selectores `[local-style="…"]`).
- **Imágenes**: sustituye el archivo en `assets/freight/` (mismo nombre) o cambia el `src`.

## Desplegar en GitHub Pages

Ya está activo. Si lo recreas: **Settings → Pages → Source: Deploy from a branch →
`main` / `/ (root)`**. Sale en `https://<usuario>.github.io/<repo>/`.

## Notas

- Los **embeds y enlaces externos** (YouTube, Spotify, Wikipedia…) necesitan internet.
- **Galerías**: reconstruidas desde la config real de Cargo — *freeform* con los anchos
  exactos por imagen, *justify* en filas, y *slideshow* como carrusel deslizable con
  flechas y autoplay (`assets/gallery.js`). La tipografía usa el tamaño raíz exacto de
  Cargo (`html{font-size:13.1328px}`), así que cuerpo/títulos/espaciados coinciden.
- **Portada (welcome)**: cada palabra (hola/bon dia/hello) está fijada sobre su trazo
  a mano alzada, igual que el original.
- Las imágenes se optimizaron (WebP); los originales a resolución completa pueden
  re-descargarse con los scripts de `tools/`.

## Tablitas

`tablitas/` guarda todas las tablitas del TFG sin depender de Google:

- `tablitas/<canción>/` — cada Google Sheet copiado tal cual (export HTML de Google
  + `.xlsx` descargable), 36 en total: tablitas google, extended, aún no terminadas,
  anotadas por hacer y los registros.
- `tablitas/textedit/` — las tablitas originales de TextEdit (`.rtf`) y su versión `.html`.
- `tablitas/generador.html` — el generador: un Sheets a medida de cómo se usaron las tablitas.
  Capas alineadas por línea (texto, notas, acordes), secciones, temas con color («pintar»),
  repeticiones, grados armónicos automáticos según la tonalidad, sílabas y esquema de rima por
  sección. Guarda en el navegador y en archivo: «guardar archivo» descarga un `.tablita.html`
  que es el propio generador con la tablita dentro (se abre sin internet y se sigue editando).
  Tests: abrir `generador.html#test` y mirar la consola.
- `tablitas/nuevas/` — mete aquí los `.html` que salgan del generador y vuelve a
  generar el índice: `python3 tools/tablitas.py` (con `--drive` re-descarga de Google).

## Reconstruir

Ver `tools/README.md`.
