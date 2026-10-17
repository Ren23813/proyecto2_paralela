#!/usr/bin/env python3
"""Promedia las mediciones de medir.sh y calcula speedup y eficiencia.

Uso: python3 resumen.py [resultados.csv]

El speedup de cada caso se calcula contra el tiempo promedio con 1 proceso
para la misma llave: S = T1 / Tp, eficiencia E = S / p.
"""
import csv
import statistics
import sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "resultados.csv"

tiempos = defaultdict(list)
probadas = defaultdict(list)
with open(path, newline="") as f:
    for row in csv.DictReader(f, delimiter=";"):
        clave = (int(row["llave_real"]), row["modo"], int(row["np"]))
        tiempos[clave].append(float(row["tiempo_s"]))
        probadas[clave].append(int(row["llaves_probadas"]))

# con 1 proceso el modo no importa: sirve de base para ambos
base = {llave: statistics.mean(t) for (llave, modo, np), t in tiempos.items() if np == 1}

print("| Llave | Modo | Procesos | Reps | Tiempo prom. (s) | Desv. est. (s) "
      "| Llaves probadas | Speedup | Eficiencia |")
print("|---:|---|---:|---:|---:|---:|---:|---:|---:|")
for llave, modo, np in sorted(tiempos, key=lambda c: (c[0], c[1] != "bloques", c[2])):
    t = tiempos[(llave, modo, np)]
    prom = statistics.mean(t)
    desv = statistics.stdev(t) if len(t) > 1 else 0.0
    llaves = statistics.mean(probadas[(llave, modo, np)])
    if llave in base and prom > 0:
        s = base[llave] / prom
        sp, ef = f"{s:.2f}", f"{s / np:.2f}"
    else:
        sp = ef = "-"
    print(f"| {llave} | {modo} | {np} | {len(t)} | {prom:.4f} | {desv:.4f} "
          f"| {llaves:.0f} | {sp} | {ef} |")
