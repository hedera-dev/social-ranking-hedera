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

Por ahora los números de LunarCrush (Camino 1) están embebidos directamente en `dashboard/index.html` (snapshot del 2026-08-05). Pendiente: portar esa recolección a scripts propios (`scripts/collect_data.py` → `scripts/build_report.py`) para poder refrescar esa parte del reporte sin editar el HTML a mano.

## Camino 3 — Rendimiento propio de @HederaCommunity (X Analytics)

La sección "Rendimiento propio" del reporte (entre los marcadores `<!-- OWN_ACCOUNT_START -->` / `<!-- OWN_ACCOUNT_END -->` en `dashboard/index.html`) sí está automatizada, vía `scripts/build_report.py`.

Flujo semanal:

1. Exportar el CSV "Account overview" desde [analytics.x.com](https://analytics.x.com) para la cuenta `@HederaCommunity`.
2. Guardarlo en `research/x_analytics/` con el nombre `YYYY-MM-DD_YYYY-MM-DD.csv` (fecha de inicio y fin del período que cubre el CSV).
3. Correr:

   ```bash
   python scripts/build_report.py \
     --seguidores-verificados 11400/144900 \
     --active-followers 63500/144900
   ```

   Los dos flags son opcionales — esos 2 números (seguidores verificados y active followers) no vienen en el CSV exportable, solo en el resumen visual de X Analytics, así que hay que pasarlos a mano cada semana si se quieren mostrar. Si en algún momento el CSV los incluye como columnas, el script los toma de ahí directamente y los flags dejan de ser necesarios.

4. El script calcula solo las variaciones (↑/↓ %) comparando contra el CSV de la semana anterior guardado en `research/x_analytics/` — no depende de los porcentajes que muestra X Analytics en pantalla. Con una sola semana de datos, esas variaciones se muestran como "semana anterior no disponible" hasta que haya al menos dos CSVs.
5. Revisar el diff de `dashboard/index.html`, hacer commit y push (Vercel redeploya solo).
