# meowrhino — sitio recuperado (TFG + portfolio)

Copia **estática y editable** de **meowrhino.cargo.site**, recuperada y reconstruida
sin depender de Cargo (el sitio original quedó privado al no renovar el pago).

A diferencia de una exportación bruta de Cargo, estas páginas se reescribieron a
**HTML/CSS limpio y legible**: sin el motor JavaScript de Cargo, sin JSON incrustado
y sin plantillas. Puedes abrir cualquier `.html` y editar el texto, los enlaces o las
imágenes directamente.

## Estructura

```
index.html            selector de idioma (hola / bon dia / hello) → welcome
home_1_esp|eng|cat    portada por idioma
about_*               sobre mí
portfolio_*           portfolio (sets que apilan los proyectos)
UX-UI_* objeto_* interaccion_*   páginas de proyecto
CV_design_*           currículum
tfg.html              el TFG escrito completo
404.html              página de error
assets/
  css/
    foundation.css    base de Cargo (rejilla, tipografía, galerías) — legible
    base.css          hoja de estilos del sitio (colores, tipos)
    galleries.css     layout estático de galerías, rejilla y marquee (nuestro)
  freight/            imágenes (convertidas a WebP, optimizadas)
  files/              vídeos, audios y PDFs
  type/               fuente YoungSerif
tools/                cómo se reconstruyó (scripts + volcado de contenido)
```

Cada página: `<head>` con los 3 CSS + un `<style>` con el CSS propio de esa página,
y `<body>` con el contenido dentro de `bodycopy.page_content`. Para editar un texto,
busca la palabra en el `.html` y cámbiala.

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
- **Galerías**: sin el motor, las de tipo *slideshow* se ven como carrusel deslizable
  (scroll horizontal) en vez de pase automático; las *justify* como filas de imágenes.
- **Portada (welcome)**: cada palabra (hola/bon dia/hello) está fijada sobre su trazo
  a mano alzada, igual que el original.
- Las imágenes se optimizaron (WebP); los originales a resolución completa pueden
  re-descargarse con los scripts de `tools/`.

## Reconstruir

Ver `tools/README.md`.
