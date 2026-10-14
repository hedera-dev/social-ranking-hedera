#!/usr/bin/env python3
"""Actualiza la sección "Rendimiento propio" de dashboard/index.html a partir
de los CSV de X Analytics guardados en research/x_analytics/.

Uso:
    1. Exportar el CSV "Account overview" desde analytics.x.com.
    2. Guardarlo en research/x_analytics/ con el nombre YYYY-MM-DD_YYYY-MM-DD.csv
       (fecha de inicio y fin del período que cubre el CSV).
    3. Correr:
         python scripts/build_report.py

    Opcional, solo cuando tengas los números nuevos (no vienen en el CSV, solo
    en el resumen visual de X Analytics):
         python scripts/build_report.py \
             --seguidores-verificados 11400/144900 \
             --active-followers 63500/144900
    Se guardan en research/x_analytics/manual.json con la fecha del período y
    se siguen mostrando (con su fecha) en las corridas siguientes.

    Reporte mensual (opcional): research/x_analytics/monthly/YYYY-MM.json.
    Se muestra el más reciente.

Las variaciones se calculan sobre promedio diario contra el CSV anterior, así
que períodos de distinta duración (6 vs 9 días) siguen siendo comparables.
"""
import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = REPO_ROOT / "research" / "x_analytics"
MONTHLY_DIR = CSV_DIR / "monthly"
MANUAL_PATH = CSV_DIR / "manual.json"
REPORT_PATH = REPO_ROOT / "dashboard" / "index.html"

START_MARKER = "<!-- OWN_ACCOUNT_START -->"
END_MARKER = "<!-- OWN_ACCOUNT_END -->"

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

METRIC_FIELDS = [
    "Impresiones", "Me gusta", "Interacciones", "Guardados", "Compartidos",
    "Nuevos seguidores", "Dejar de seguir", "Respuestas", "Reposts",
    "Visitas del perfil",
]

FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$")


def parse_csv(path):
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({k: (float(v) if k in METRIC_FIELDS else v) for k, v in row.items()})
    return rows


def sums(rows):
    return {field: sum(r[field] for r in rows) for field in METRIC_FIELDS}


def period_days(start_iso, end_iso):
    return (date.fromisoformat(end_iso) - date.fromisoformat(start_iso)).days + 1


def fmt_date(iso):
    _, m, d = iso.split("-")
    return f"{int(d)} {MESES[int(m) - 1]}"


def fmt_int(n):
    return f"{int(round(n)):,}".replace(",", ".")


def delta_pct(current, previous):
    if not previous:
        return None
    return (current - previous) / previous * 100


def delta_per_day(cur, cur_days, prev, prev_days):
    if prev is None:
        return None
    return delta_pct(cur / cur_days, prev / prev_days)


def delta_badge(pct, invert=False, precise=False):
    """invert=True para métricas donde bajar es bueno."""
    if pct is None:
        return '<span class="rank">período anterior no disponible</span>'
    good = pct >= 0
    if invert:
        good = not good
    arrow = "↑" if pct >= 0 else "↓"
    cls = "green" if good else "rose"
    value = f"{abs(pct):g}" if precise else f"{abs(pct):.0f}"
    return f'<span class="delta {cls}">{arrow} {value}%</span>'


def load_periods():
    files = []
    for p in CSV_DIR.glob("*.csv"):
        m = FILENAME_RE.match(p.name)
        if not m:
            print(f"aviso: {p.name} no sigue el patrón YYYY-MM-DD_YYYY-MM-DD.csv, se ignora", file=sys.stderr)
            continue
        files.append((m.group(1), m.group(2), p))
    files.sort(key=lambda t: t[1])  # ordenar por fecha de fin
    return files


def parse_ratio_flag(value):
    if value is None:
        return None
    part, total = value.split("/")
    return [int(part), int(total)]


def load_manual():
    if MANUAL_PATH.exists():
        return json.loads(MANUAL_PATH.read_text(encoding="utf-8"))
    return {}


def render_manual_stat(label, ratio, as_of):
    if not ratio:
        return ""
    part, total = ratio
    pct = part / total * 100
    return f"""
      <div class="card">
        <div class="stat-num">{fmt_int(part)}</div>
        <h3>{label}</h3>
        <p>De {fmt_int(total)} seguidores totales ({pct:.0f}%). Dato manual de X Analytics al {fmt_date(as_of)} (no viene en el CSV exportable).</p>
      </div>"""


def load_monthly():
    files = sorted(MONTHLY_DIR.glob("*.json")) if MONTHLY_DIR.exists() else []
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def render_monthly(m):
    if not m:
        return ""
    rows = ""
    for item in m["metrics"]:
        rows += f"""
          <tr>
            <td>{item["label"]}</td>
            <td>{item["value"]}</td>
            <td>{delta_badge(item["delta"], precise=True)}</td>
          </tr>"""
    for item in m.get("totals", []):
        rows += f"""
          <tr>
            <td>{item["label"]}</td>
            <td>{item["value"]}</td>
            <td><span class="rank">—</span></td>
          </tr>"""
    takeaway = f'\n    <p class="notice"><strong>Conclusión del reporte:</strong> {m["takeaway"]}</p>' if m.get("takeaway") else ""
    return f"""

    <h3 class="section-title" style="font-size:20px;margin:40px 0 8px;">Resumen mensual — {m["label"]}</h3>
    <p class="section-sub" style="margin-bottom:16px;">{m["source"]}</p>
    <div class="table-card">
      <table>
        <thead>
          <tr><th>Métrica</th><th>{m["label"]}</th><th>vs. mes anterior (según X)</th></tr>
        </thead>
        <tbody>{rows}
        </tbody>
      </table>
    </div>{takeaway}"""


def render_section(cur_range, prev_range, current_sums, previous_sums, manual, monthly):
    start_iso, end_iso = cur_range
    cur_days = period_days(*cur_range)
    prev_days = period_days(*prev_range) if prev_range else None

    impresiones = current_sums["Impresiones"]
    interacciones = current_sums["Interacciones"]
    nuevos_neto = current_sums["Nuevos seguidores"] - current_sums["Dejar de seguir"]
    tasa = interacciones / impresiones * 100 if impresiones else 0

    prev_impresiones = previous_sums["Impresiones"] if previous_sums else None
    prev_interacciones = previous_sums["Interacciones"] if previous_sums else None
    prev_nuevos_neto = (previous_sums["Nuevos seguidores"] - previous_sums["Dejar de seguir"]) if previous_sums else None
    prev_tasa = (prev_interacciones / prev_impresiones * 100) if prev_impresiones else None

    secondary_rows = ""
    secondary_labels = [
        ("Nuevos seguidores", "Nuevos seguidores (bruto)", False),
        ("Dejar de seguir", "Dejar de seguir", True),  # bajar es bueno acá
        ("Me gusta", "Me gusta", False),
        ("Respuestas", "Respuestas", False),
        ("Reposts", "Reposts", False),
        ("Visitas del perfil", "Visitas del perfil", False),
        ("Guardados", "Guardados", False),
        ("Compartidos", "Compartidos", False),
    ]
    for field, label, invert in secondary_labels:
        cur = current_sums[field]
        prev = previous_sums[field] if previous_sums else None
        pct = delta_per_day(cur, cur_days, prev, prev_days)
        secondary_rows += f"""
          <tr>
            <td>{label}</td>
            <td>{fmt_int(cur)}</td>
            <td>{delta_badge(pct, invert=invert)}</td>
          </tr>"""

    as_of = manual.get("as_of")
    manual_cards = render_manual_stat("Seguidores verificados", manual.get("seguidores_verificados"), as_of) + \
        render_manual_stat("Active followers", manual.get("active_followers"), as_of)
    manual_block = f"""
    <div class="grid-2" style="margin-top:20px;">{manual_cards}
    </div>""" if manual_cards else ""

    if prev_range:
        comparison = f"Variaciones vs. el período anterior ({fmt_date(prev_range[0])} al {fmt_date(prev_range[1])}, {prev_days} días), calculadas por <code>scripts/build_report.py</code> sobre promedio diario — no dependen del cálculo interno de X."
    else:
        comparison = "Sin período anterior para comparar todavía."

    return f"""{START_MARKER}
  <section>
    <div class="section-head-row">
      <div>
        <h2 class="section-title">Rendimiento propio — @HederaCommunity</h2>
        <p class="section-sub">Datos nativos de X Analytics de la cuenta, del {fmt_date(start_iso)} al {fmt_date(end_iso)} de {end_iso[:4]} ({cur_days} días). {comparison}</p>
      </div>
      <span class="pill"><span class="dot"></span>Actualizado periódicamente</span>
    </div>

    <div class="grid-3">
      <div class="card">
        <div class="stat-num">{fmt_int(impresiones)}</div>
        <h3>Impresiones {delta_badge(delta_per_day(impresiones, cur_days, prev_impresiones, prev_days))}</h3>
        <p>Total del período.</p>
      </div>
      <div class="card">
        <div class="stat-num">{fmt_int(interacciones)}</div>
        <h3>Interacciones {delta_badge(delta_per_day(interacciones, cur_days, prev_interacciones, prev_days))}</h3>
        <p>Me gusta + respuestas + reposts + guardados + compartidos.</p>
      </div>
      <div class="card">
        <div class="stat-num">{tasa:.1f}%</div>
        <h3>Tasa de interacción {delta_badge(delta_pct(tasa, prev_tasa))}</h3>
        <p>Interacciones / impresiones del período.</p>
      </div>
    </div>

    <div class="table-card" style="margin-top:20px;">
      <table>
        <thead>
          <tr><th>Métrica</th><th>Este período</th><th>vs. período anterior</th></tr>
        </thead>
        <tbody>{secondary_rows}
          <tr class="highlight">
            <td>Nuevos seguidores (neto)</td>
            <td>{fmt_int(nuevos_neto)}</td>
            <td>{delta_badge(delta_per_day(nuevos_neto, cur_days, prev_nuevos_neto, prev_days))}</td>
          </tr>
        </tbody>
      </table>
    </div>{manual_block}{render_monthly(monthly)}
  </section>
  {END_MARKER}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seguidores-verificados", metavar="PARTE/TOTAL", help='ej. "11400/144900"')
    parser.add_argument("--active-followers", metavar="PARTE/TOTAL", help='ej. "63500/144900"')
    args = parser.parse_args()

    periods = load_periods()
    if not periods:
        print(f"No hay CSVs válidos en {CSV_DIR}", file=sys.stderr)
        sys.exit(1)

    start_iso, end_iso, current_path = periods[-1]
    current_sums = sums(parse_csv(current_path))

    previous_sums = None
    prev_range = None
    if len(periods) >= 2:
        prev_start, prev_end, previous_path = periods[-2]
        previous_sums = sums(parse_csv(previous_path))
        prev_range = (prev_start, prev_end)
        print(f"Comparando {current_path.name} vs. {previous_path.name}")
    else:
        print(f"Solo hay un período de datos ({current_path.name}); sin comparación.")

    manual = load_manual()
    verified = parse_ratio_flag(args.seguidores_verificados)
    active = parse_ratio_flag(args.active_followers)
    if verified or active:
        if verified:
            manual["seguidores_verificados"] = verified
        if active:
            manual["active_followers"] = active
        manual["as_of"] = end_iso
        MANUAL_PATH.write_text(json.dumps(manual, indent=2) + "\n", encoding="utf-8")

    new_section = render_section((start_iso, end_iso), prev_range, current_sums, previous_sums, manual, load_monthly())

    html = REPORT_PATH.read_text(encoding="utf-8")
    if START_MARKER not in html or END_MARKER not in html:
        print(f"No se encontraron los marcadores {START_MARKER} / {END_MARKER} en {REPORT_PATH}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    html = pattern.sub(lambda _: new_section, html, count=1)
    REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"Listo: {REPORT_PATH} actualizado con el período {start_iso} -> {end_iso}.")


if __name__ == "__main__":
    main()
