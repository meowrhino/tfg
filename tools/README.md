# Toolkit de recuperación

Cómo se reconstruyó este sitio desde meowrhino.cargo.site.

## Archivos
- `cargo_bundle.json` — volcado del HTML de las 31 páginas (capturado vía la sesión
  autenticada de Cargo; contiene el JSON de contenido del que sale todo).
- `asset_map.json` / `asset_subs.json` — mapa de URLs de Cargo → rutas locales.
- `build_assets.py` — descarga todos los recursos (imágenes, archivos) del CDN de Cargo.
- `clean_build.py` — **el generador**: lee `cargo_bundle.json` y reconstruye las
  páginas como HTML/CSS limpio en `../` , reutilizando el CSS de Cargo.

## Regenerar las páginas
```
python3 clean_build.py        # genera la carpeta clean/ (HTML limpio)
```
Después se optimizaron las imágenes a WebP (cwebp -q 82) y se reescribieron las
referencias. Los originales se obtienen con `build_assets.py`.

## Nota
`clean_build.py` es histórico: el HTML de la raíz se ha editado a mano después
(menús fijados, fondos de página, enlaces al TFG, sin CSS vacío), así que volver a
ejecutarlo **no** reproduce el sitio actual. Lo que manda es el HTML.

## Tablitas y sobres
- `drive_crawl.py` — lista una carpeta pública de Drive → `drive_main.json` / `drive_sobres.json`.
- `tablitas.py` — `tablitas/` desde Google Sheets + rtf de TextEdit (ver su cabecera).
- `sobres.py` — `sobres/` comprimidos desde la copia del Drive en el Escritorio.
