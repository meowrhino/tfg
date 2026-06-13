# Toolkit de recuperación

Cómo se reconstruyó este sitio desde meowrhino.cargo.site.

## Archivos
- `cargo_bundle.json` — volcado del HTML de las 31 páginas (capturado vía la sesión
  autenticada de Cargo; contiene el JSON de contenido del que sale todo).
- `asset_map.json` / `asset_subs.json` — mapa de URLs de Cargo → rutas locales.
- `build_assets.py` — descarga todos los recursos (imágenes, archivos) del CDN de Cargo.
- `gen_localizer.py` — (de la versión con motor; no usado en la limpia).
- `clean_build.py` — **el generador**: lee `cargo_bundle.json` y reconstruye las
  páginas como HTML/CSS limpio en `../` , reutilizando el CSS de Cargo.

## Regenerar las páginas
```
python3 clean_build.py        # genera la carpeta clean/ (HTML limpio)
```
Después se optimizaron las imágenes a WebP (cwebp -q 82) y se reescribieron las
referencias. Los originales se obtienen con `build_assets.py`.

## Nota
La versión "con motor de Cargo" (fiel al 100%, pero pesada y opaca) también es
reproducible con `build_pages.py`; se descartó a favor de esta versión limpia.
