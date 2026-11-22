"""Recalcula el tablero de avance de PLAN.md a partir de las casillas marcadas.

Uso:
    python planning/update_progress.py           reescribe el tablero
    python planning/update_progress.py --check   solo comprueba; termina con error si el tablero está desfasado

No necesita nada más que Python 3. Cuenta las líneas `- [x] **F3-04** ...` de cada fase.
"""
import datetime
import pathlib
import re
import sys

PLAN = pathlib.Path(__file__).with_name("PLAN.md")
START, END = "<!-- tablero:inicio -->", "<!-- tablero:fin -->"
TASK = re.compile(r"^- \[( |x)\] \*\*(F\d+)-(\d+)\*\* ", re.M)
PHASE = re.compile(r"^### (F\d+) · (.+)$", re.M)


def percent(done, total):
    return f"{round(100 * done / total)} %" if total else "—"


def state(done, total):
    if done == total:
        return "✅ Terminada"
    return "🔄 En curso" if done else "⏳ Pendiente"


def build_table(text):
    names = dict(PHASE.findall(text))
    counts = {phase: [0, 0] for phase in names}
    seen = set()
    for mark, phase, number in TASK.findall(text):
        if phase not in counts:
            raise SystemExit(f"La actividad {phase}-{number} no pertenece a ninguna fase declarada.")
        if (phase, number) in seen:
            raise SystemExit(f"El identificador {phase}-{number} está repetido.")
        seen.add((phase, number))
        counts[phase][1] += 1
        counts[phase][0] += mark == "x"
    rows = ["| Fase | Nombre | Actividades | Hechas | Avance | Estado |", "|---|---|---:|---:|---:|---|"]
    for phase in sorted(counts, key=lambda p: int(p[1:])):
        done, total = counts[phase]
        rows.append(f"| {phase} | {names[phase]} | {total} | {done} | {percent(done, total)} | {state(done, total)} |")
    done = sum(c[0] for c in counts.values())
    total = sum(c[1] for c in counts.values())
    overall = "✅ Terminado" if done == total else "🔄 En curso"
    rows.append(f"| | **Global** | **{total}** | **{done}** | **{percent(done, total)}** | {overall} |")
    return "\n".join(rows), done, total


def main():
    text = PLAN.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("No encuentro los marcadores del tablero en PLAN.md.")
    head, rest = text.split(START, 1)
    current, tail = rest.split(END, 1)
    table, done, total = build_table(text)
    if "--check" in sys.argv:
        if table not in current:
            raise SystemExit("El tablero está desfasado. Ejecuta: python planning/update_progress.py")
        print(f"Tablero al día: {done} de {total} actividades ({percent(done, total)}).")
        return
    if table in current:
        print(f"Sin cambios: {done} de {total} actividades ({percent(done, total)}).")
        return
    today = datetime.date.today().isoformat()
    new = f"{START}\n{table}\n\nActualizado el {today}.\n{END}"
    PLAN.write_text(head + new + tail, encoding="utf-8", newline="\n")
    print(f"Tablero actualizado: {done} de {total} actividades ({percent(done, total)}).")


if __name__ == "__main__":
    main()
