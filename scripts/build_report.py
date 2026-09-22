#!/usr/bin/env python3
"""Actualiza la sección "Rendimiento propio" de dashboard/index.html a partir
de los CSV semanales de X Analytics guardados en research/x_analytics/.

Uso semanal:
    1. Exportar el CSV "Account overview" desde analytics.x.com.
    2. Guardarlo en research/x_analytics/ con el nombre YYYY-MM-DD_YYYY-MM-DD.csv
       (fecha de inicio y fin del período que cubre el CSV).
    3. Correr:
         python scripts/build_report.py \
             --seguidores-verificados 11400/144900 \
             --active-followers 63500/144900

    Los dos flags son opcionales (esos 2 números no vienen en el CSV, solo en
    el resumen visual de X Analytics). Si no se pasan, se conserva lo que ya
    había en el reporte. Si el CSV algún día trae columnas
    "Seguidores verificados" / "Active followers", el script las usa
    directamente y los flags dejan de ser necesarios.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = REPO_ROOT / "research" / "x_analytics"
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


def fmt_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MESES[int(m) - 1]}"


def fmt_int(n):
    return f"{int(round(n)):,}".replace(",", ".")


def delta_pct(current, previous):
    if not previous:
        return None
    return (current - previous) / previous * 100


def delta_badge(pct, invert=False):
    """invert=True para métricas donde bajar es bueno (no se usa hoy, placeholder)."""
    if pct is None:
        return '<span class="rank">semana anterior no disponible</span>'
    good = pct >= 0
    if invert:
        good = not good
    arrow = "↑" if pct >= 0 else "↓"
    cls = "green" if good else "rose"
    return f'<span class="delta {cls}">{arrow} {abs(pct):.0f}%</span>'


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
    return int(part), int(total)


def render_manual_stat(label, ratio):
    if ratio is None:
        return ""
    part, total = ratio
    pct = part / total * 100
    return f"""
      <div class="card">
        <div class="stat-num">{fmt_int(part)}</div>
        <h3>{label}</h3>
        <p>De {fmt_int(total)} seguidores totales ({pct:.0f}%). Dato manual de X Analytics (no viene en el CSV exportable).</p>
      </div>"""


def render_section(start_iso, end_iso, current_sums, previous_sums, verified_ratio, active_ratio):
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
        pct = delta_pct(cur, prev)
        secondary_rows += f"""
          <tr>
            <td>{label}</td>
            <td>{fmt_int(cur)}</td>
            <td>{delta_badge(pct, invert=invert)}</td>
          </tr>"""

    manual_cards = render_manual_stat("Seguidores verificados", verified_ratio) + \
        render_manual_stat("Active followers", active_ratio)
    manual_block = f"""
    <div class="grid-2" style="margin-top:20px;">{manual_cards}
    </div>""" if manual_cards else ""

    return f"""{START_MARKER}
  <section>
    <div class="section-head-row">
      <div>
        <h2 class="section-title">Rendimiento propio — @HederaCommunity</h2>
        <p class="section-sub">Datos nativos de X Analytics de la cuenta, semana del {fmt_date(start_iso)} al {fmt_date(end_iso)} de {end_iso[:4]}. Variación vs. semana anterior calculada por <code>scripts/build_report.py</code>, no depende del cálculo interno de X.</p>
      </div>
      <span class="pill"><span class="dot"></span>Actualizado semanalmente</span>
    </div>

    <div class="grid-3">
      <div class="card">
        <div class="stat-num">{fmt_int(impresiones)}</div>
        <h3>Impresiones {delta_badge(delta_pct(impresiones, prev_impresiones))}</h3>
        <p>Total de la semana.</p>
      </div>
      <div class="card">
        <div class="stat-num">{fmt_int(interacciones)}</div>
        <h3>Interacciones {delta_badge(delta_pct(interacciones, prev_interacciones))}</h3>
        <p>Me gusta + respuestas + reposts + guardados + compartidos.</p>
      </div>
      <div class="card">
        <div class="stat-num">{tasa:.1f}%</div>
        <h3>Tasa de interacción {delta_badge(delta_pct(tasa, prev_tasa))}</h3>
        <p>Interacciones / impresiones de la semana.</p>
      </div>
    </div>

    <div class="table-card" style="margin-top:20px;">
      <table>
        <thead>
          <tr><th>Métrica</th><th>Esta semana</th><th>vs. semana anterior</th></tr>
        </thead>
        <tbody>{secondary_rows}
          <tr class="highlight">
            <td>Nuevos seguidores (neto)</td>
            <td>{fmt_int(nuevos_neto)}</td>
            <td>{delta_badge(delta_pct(nuevos_neto, prev_nuevos_neto))}</td>
          </tr>
        </tbody>
      </table>
    </div>{manual_block}
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
    if len(periods) >= 2:
        _, _, previous_path = periods[-2]
        previous_sums = sums(parse_csv(previous_path))
        print(f"Comparando {current_path.name} vs. {previous_path.name}")
    else:
        print(f"Solo hay una semana de datos ({current_path.name}); sin comparación.")

    verified_ratio = parse_ratio_flag(args.seguidores_verificados)
    active_ratio = parse_ratio_flag(args.active_followers)

    new_section = render_section(start_iso, end_iso, current_sums, previous_sums, verified_ratio, active_ratio)

    html = REPORT_PATH.read_text(encoding="utf-8")
    if START_MARKER not in html or END_MARKER not in html:
        print(f"No se encontraron los marcadores {START_MARKER} / {END_MARKER} en {REPORT_PATH}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    html = pattern.sub(new_section.replace("\\", "\\\\"), html, count=1)
    REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"Listo: {REPORT_PATH} actualizado con la semana {start_iso} -> {end_iso}.")
    if verified_ratio is None and active_ratio is None:
        print("Nota: no se pasaron --seguidores-verificados / --active-followers, esos 2 cards no se mostraron esta corrida.")


if __name__ == "__main__":
    main()
