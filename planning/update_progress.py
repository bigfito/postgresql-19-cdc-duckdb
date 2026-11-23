"""Registra y reporta el avance de PLAN.md, por fase y global.

Uso:
    python planning/update_progress.py --done F3-04 --note "qué se hizo y cómo se comprobó"
        Marca la actividad, recalcula el tablero, añade la línea a la bitácora con
        el avance y lo imprime. Admite varias actividades: --done F3-04 F3-05.
        Con --who se indica quién la hizo (por defecto, «Agente»).

    python planning/update_progress.py
        Recalcula el tablero a partir de las casillas marcadas e imprime el avance.

    python planning/update_progress.py --check
        Solo comprueba; termina con error si el tablero está desfasado.

El avance que imprime es el que hay que comunicar a la persona responsable al
terminar cada actividad: el de la fase y el global, en actividades y en porcentaje.

No necesita nada más que Python 3. Cuenta las líneas `- [x] **F3-04** ...` de cada fase.
"""
import argparse
import datetime
import pathlib
import re
import sys

PLAN = pathlib.Path(__file__).with_name("PLAN.md")
START, END = "<!-- tablero:inicio -->", "<!-- tablero:fin -->"
TASK = re.compile(r"^- \[( |x)\] \*\*(F\d+)-(\d+)\*\* ", re.M)
PHASE = re.compile(r"^### (F\d+) · (.+)$", re.M)
BOARD_ROW = re.compile(r"^\| (F\d+) \| .+? \| \d+ \| (\d+) \|", re.M)
ACTIVITY_ID = re.compile(r"F\d+-\d+")
LOG_HEAD = "| Fecha | Actividades | Quién | Avance | Nota |\n|---|---|---|---|---|\n"


def percent(done, total):
    return f"{round(100 * done / total)} %" if total else "—"


def state(done, total):
    if done == total:
        return "✅ Terminada"
    return "🔄 En curso" if done else "⏳ Pendiente"


def phase_order(phase):
    return int(phase[1:])


def count(text):
    """Devuelve los nombres de las fases y, por fase, [hechas, total]."""
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
    return names, counts


def totals(counts):
    return sum(c[0] for c in counts.values()), sum(c[1] for c in counts.values())


def build_table(names, counts):
    rows = ["| Fase | Nombre | Actividades | Hechas | Avance | Estado |", "|---|---|---:|---:|---:|---|"]
    for phase in sorted(counts, key=phase_order):
        done, total = counts[phase]
        rows.append(f"| {phase} | {names[phase]} | {total} | {done} | {percent(done, total)} | {state(done, total)} |")
    done, total = totals(counts)
    overall = "✅ Terminado" if done == total else "🔄 En curso"
    rows.append(f"| | **Global** | **{total}** | **{done}** | **{percent(done, total)}** | {overall} |")
    return "\n".join(rows)


def mark_done(text, activities):
    """Marca las actividades indicadas. Falla si alguna no existe o ya estaba marcada."""
    for activity in activities:
        pending, done = f"- [ ] **{activity}** ", f"- [x] **{activity}** "
        if text.count(pending) == 1:
            text = text.replace(pending, done)
        elif text.count(done) == 1:
            raise SystemExit(f"La actividad {activity} ya estaba marcada; no se registra dos veces.")
        else:
            raise SystemExit(f"No encuentro la actividad {activity} en el plan.")
    return text


def join_names(items):
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " y " + items[-1]


def progress_label(counts, phases):
    """Avance en una línea, para la bitácora: «F3 20 % · Global 19 %»."""
    parts = [f"{phase} {percent(*counts[phase])}" for phase in phases]
    return " · ".join(parts + [f"Global {percent(*totals(counts))}"])


def add_log_row(text, activities, who, note, label):
    if text.count(LOG_HEAD) != 1:
        raise SystemExit("No encuentro la cabecera de la bitácora en PLAN.md.")
    note = " ".join(note.split()).replace("|", "\\|")
    today = datetime.date.today().isoformat()
    row = f"| {today} | {join_names(activities)} | {who} | {label} | {note} |\n"
    return text.replace(LOG_HEAD, LOG_HEAD + row)


def report(names, counts, phases, title):
    """Imprime el avance de las fases indicadas y el global."""
    print(title)
    for phase in phases:
        done, total = counts[phase]
        print(f"  {phase} · {names[phase]}: {done} de {total} actividades ({percent(done, total)})")
    done, total = totals(counts)
    print(f"  Global: {done} de {total} actividades ({percent(done, total)})")


def parse_args():
    parser = argparse.ArgumentParser(description="Registra y reporta el avance de PLAN.md.")
    parser.add_argument("--check", action="store_true", help="solo comprueba que el tablero esté al día")
    parser.add_argument("--done", nargs="+", metavar="ACTIVIDAD", help="actividades terminadas, por ejemplo F3-04")
    parser.add_argument("--note", help="qué se hizo y cómo se comprobó; obligatoria con --done")
    parser.add_argument("--who", default="Agente", help="quién hizo el trabajo (por defecto, Agente)")
    args = parser.parse_args()
    if args.done:
        if args.check:
            parser.error("--done y --check no se usan juntos")
        if not args.note or not args.note.strip():
            parser.error("--done necesita --note")
        for activity in args.done:
            if not ACTIVITY_ID.fullmatch(activity):
                parser.error(f"«{activity}» no es un identificador de actividad, como F3-04")
    elif args.note:
        parser.error("--note solo se usa con --done")
    return args


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parse_args()
    original = PLAN.read_text(encoding="utf-8")
    if START not in original or END not in original:
        raise SystemExit("No encuentro los marcadores del tablero en PLAN.md.")

    text = mark_done(original, args.done) if args.done else original
    names, counts = count(text)
    table = build_table(names, counts)
    head, rest = text.split(START, 1)
    current, tail = rest.split(END, 1)
    in_progress = [p for p in sorted(counts, key=phase_order) if 0 < counts[p][0] < counts[p][1]]

    if args.check:
        if table not in current:
            raise SystemExit("El tablero está desfasado. Ejecuta: python planning/update_progress.py")
        report(names, counts, in_progress, "Tablero al día.")
        return

    if args.done:
        phases = sorted({a.split("-")[0] for a in args.done}, key=phase_order)
        title = f"Avance tras {join_names(args.done)}:"
    else:
        before = {phase: int(done) for phase, done in BOARD_ROW.findall(current)}
        phases = [p for p in sorted(counts, key=phase_order) if before.get(p) != counts[p][0]]
        title = "Tablero actualizado." if table not in current else "Sin cambios en el tablero."
        phases = phases or in_progress

    if table not in current:
        today = datetime.date.today().isoformat()
        text = head + f"{START}\n{table}\n\nActualizado el {today}.\n{END}" + tail
    if args.done:
        text = add_log_row(text, args.done, args.who, args.note, progress_label(counts, phases))
    if text != original:
        PLAN.write_text(text, encoding="utf-8", newline="\n")
    report(names, counts, phases, title)


if __name__ == "__main__":
    main()
