#!/usr/bin/env python3
"""Genera las gráficas del informe a partir de resultados.csv.

Uso: python3 graficas.py [resultados.csv] [carpeta_salida]
Produce img/speedup.png, img/llaves_probadas.png, img/reparto.png e imprime
la tabla de speedup predicho vs. medido para el reparto por bloques.
"""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "resultados.csv"
outdir = Path(sys.argv[2] if len(sys.argv) > 2 else "img")
outdir.mkdir(exist_ok=True)

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
COLOR = {"bloques": BLUE, "ciclico": ORANGE}
NOMBRE = {"bloques": "Bloques", "ciclico": "Cíclico"}

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "figure.facecolor": "white",
    "axes.titlesize": 11, "axes.titlecolor": INK, "axes.titleweight": "bold",
})

tiempos = defaultdict(list)
probadas = defaultdict(list)
bits = None
with open(path, newline="") as f:
    for row in csv.DictReader(f, delimiter=";"):
        c = (int(row["llave_real"]), row["modo"], int(row["np"]))
        tiempos[c].append(float(row["tiempo_s"]))
        probadas[c].append(int(row["llaves_probadas"]))
        bits = int(row["bits"])

S = 1 << bits
t = {c: statistics.mean(v) for c, v in tiempos.items()}
w = {c: statistics.mean(v) for c, v in probadas.items()}
llaves = sorted({c[0] for c in t})
nps = sorted({c[2] for c in t})
# con 1 proceso los dos modos son idénticos: se usa la misma base
for k in llaves:
    t[(k, "ciclico", 1)] = t[(k, "bloques", 1)]
    w[(k, "ciclico", 1)] = w[(k, "bloques", 1)]

def describir(k):
    if k == S - 1:
        return "última llave"
    if k < S // max(nps):
        return "pequeña"
    return "justo antes de S/2" if k < S // 2 else "justo después de S/2"


# 1) Speedup vs. procesos, un panel por llave
fig, axes = plt.subplots(2, 2, figsize=(10, 7.2), sharex=True, sharey=True)
for ax, k in zip(axes.flat, llaves):
    ax.plot(nps, nps, color=MUTED, lw=1.5, ls="--", zorder=1)
    finales = {}
    for modo in ("bloques", "ciclico"):
        sp = [t[(k, "bloques", 1)] / t[(k, modo, p)] for p in nps]
        ax.plot(nps, sp, color=COLOR[modo], lw=2, marker="o", ms=8,
                markeredgecolor="white", markeredgewidth=2, zorder=3)
        finales[modo] = sp[-1]
    # etiqueta directa al final de cada línea; si quedan cerca, se separan
    alto = max(finales, key=finales.get)
    cerca = max(finales.values()) / min(finales.values()) < 1.6
    for modo, v in finales.items():
        dy = (9 if modo == alto else -9) if cerca else 0
        ax.annotate(f"{NOMBRE[modo]} {v:.2f}×", (nps[-1], v), xytext=(8, dy),
                    textcoords="offset points", color=INK, fontsize=9, va="center")
    ax.set_title(f"Llave {k:,} ({describir(k)})".replace(",", " "), loc="left")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(nps, [str(p) for p in nps])
    ax.set_xlim(0.85, nps[-1] * 2.6)
    ax.set_yticks([0.5, 1, 2, 4, 8, 100, 500], ["0.5", "1", "2", "4", "8", "100", "500"])
    ax.minorticks_off()
for ax in axes[1]:
    ax.set_xlabel("Procesos MPI")
for ax in axes[:, 0]:
    ax.set_ylabel("Speedup  T₁ / Tₚ  (escala log)")
handles = [plt.Line2D([], [], color=COLOR[m], lw=2, marker="o", ms=7) for m in COLOR]
handles.append(plt.Line2D([], [], color=MUTED, lw=1.5, ls="--"))
fig.legend(handles, ["Reparto por bloques", "Reparto cíclico", "Speedup ideal"],
           loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.995))
fig.suptitle(f"Speedup según la llave y el reparto (espacio de 2^{bits} llaves, "
             f"promedio de {len(next(iter(tiempos.values())))} corridas)",
             y=0.945, color=INK, fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig(outdir / "speedup.png", dpi=150)
plt.close(fig)


# 2) Trabajo total (llaves probadas) para la llave pequeña
k = min(llaves)
fig, ax = plt.subplots(figsize=(7.5, 4.2))
x = range(len(nps))
bw = 0.38
for j, modo in enumerate(("bloques", "ciclico")):
    vals = [w[(k, modo, p)] for p in nps]
    xs = [i + (j - 0.5) * (bw + 0.02) for i in x]
    ax.bar(xs, vals, width=bw, color=COLOR[modo], label=NOMBRE[modo])
    for xi, v in zip(xs, vals):
        ax.annotate(f"{v / 1000:.0f} k", (xi, v), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.axhline(k + 1, color=INK2, lw=1, ls="--",
           label=f"Llaves necesarias ({k + 1:,})".replace(",", " "))
ax.set_xticks(list(x), [str(p) for p in nps])
ax.set_xlabel("Procesos MPI")
ax.set_ylabel("Llaves probadas (todos los procesos)")
ax.set_title(f"Trabajo realizado para encontrar la llave {k:,}".replace(",", " "), loc="left")
ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f} k")
ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(outdir / "llaves_probadas.png", dpi=150)
plt.close(fig)


# 3) Diagrama del reparto con 4 procesos y la posición de cada llave
P = 4
proc_color = [BLUE, ORANGE, AQUA, YELLOW]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 4.4),
                             gridspec_kw={"height_ratios": [1.5, 1]})
blk = S // P
for p in range(P):
    a1.barh(0, blk - S * 0.003, left=p * blk, height=0.5, color=proc_color[p])
    a1.text(p * blk + blk / 2, 0, f"P{p}\n[{p}·S/4, {p + 1}·S/4)", ha="center",
            va="center", color="white", fontsize=9, fontweight="bold")
for i, kk in enumerate(llaves):
    a1.axvline(kk, ymin=0.12, ymax=0.88, color=INK, lw=1.2)
    a1.annotate(f"{kk:,}".replace(",", " "), (kk, 0.42 if i % 2 else -0.42),
                ha="center", va="center", fontsize=8.5, color=INK,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=MUTED, lw=0.6))
a1.set_xlim(0, S)
a1.set_ylim(-0.6, 0.6)
a1.set_yticks([])
a1.set_xticks([0, S // 4, S // 2, 3 * S // 4, S], ["0", "S/4", "S/2", "3S/4", "S"])
a1.grid(False)
a1.spines["left"].set_visible(False)
a1.set_title("Reparto por bloques (np = 4): cada proceso recorre un rango contiguo", loc="left")

n = 24
for i in range(n):
    a2.barh(0, 0.92, left=i, height=0.6, color=proc_color[i % P])
    a2.text(i + 0.46, 0, str(i), ha="center", va="center", color="white",
            fontsize=8, fontweight="bold")
a2.text(n + 0.3, 0, "…", va="center", fontsize=14, color=INK2)
a2.set_xlim(0, n + 1.2)
a2.set_ylim(-0.6, 0.6)
a2.axis("off")
a2.set_title("Reparto cíclico (np = 4): primeras llaves; la llave i la prueba P(i mod 4)",
             loc="left")
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in proc_color]
fig.legend(handles, [f"P{p}" for p in range(P)], loc="lower center", ncol=P,
           frameon=False, bbox_to_anchor=(0.5, 0.0))
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(outdir / "reparto.png", dpi=150)
plt.close(fig)


# Tabla: speedup predicho por el modelo vs. medido (bloques)
print("| Llave | Procesos | Bloque | Posición dentro del bloque | "
      "Speedup predicho | Speedup medido |")
print("|---:|---:|---:|---:|---:|---:|")
for k in llaves:
    for p in nps[1:]:
        size = S // p
        b = min(k // size, p - 1)
        offset = k - b * size
        pred = (k + 1) / (offset + 1)
        med = t[(k, "bloques", 1)] / t[(k, "bloques", p)]
        print(f"| {k} | {p} | P{b} | {offset} | {pred:.2f} | {med:.2f} |")
