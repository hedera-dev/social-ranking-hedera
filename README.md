# Social Ranking — Hedera

Reporte estático de social ranking de Hedera frente a otros proyectos cripto (LunarCrush), con hallazgos cualitativos y recomendaciones para el equipo del programa de embajadores.

## Estructura

```
dashboard/index.html   -> reporte (página única, sin build step)
vercel.json            -> redirige "/" a "/dashboard/index.html"
```

## Deploy

Este es un sitio estático de un solo archivo HTML (sin dependencias ni build). Para desplegar en Vercel:

```bash
vercel --prod
```

O conectando el repo de GitHub directamente desde el dashboard de Vercel (framework preset: "Other").

## Actualizar datos

Por ahora los números están embebidos directamente en `dashboard/index.html` (snapshot LunarCrush del 2026-08-05). Pendiente: portar la recolección de datos a scripts propios (`scripts/collect_data.py` → `scripts/build_report.py`) para poder refrescar el reporte sin editar el HTML a mano.
