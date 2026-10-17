#!/usr/bin/env bash
# Mide el tiempo de búsqueda para varias llaves, número de procesos y modos
# de reparto, repitiendo cada caso REPS veces. Guarda todo en un CSV.
#
# Uso:  ./medir.sh [repeticiones] [archivo_salida.csv]
# Variables opcionales:
#   BITS=20             tamaño del espacio de búsqueda (2^BITS llaves)
#   NPS="1 2 4 8"       números de procesos a probar
#   MODOS="bloques ciclico"
#   LLAVES="..."        llaves a probar (por defecto se calculan a partir de BITS)
set -euo pipefail
cd "$(dirname "$0")"

REPS=${1:-5}
OUT=${2:-resultados.csv}
BITS=${BITS:-20}
NPS=${NPS:-"1 2 4 8"}
MODOS=${MODOS:-"bloques ciclico"}

S=$((1 << BITS))
# Llaves elegidas según dónde caen en el reparto por bloques:
#   S/2+1000  justo después del inicio de la mitad superior -> la encuentra
#             rápido el primer proceso de esa mitad (speedup "superlineal")
#   S/2-1000  justo antes del final de la mitad inferior -> peor caso para np=2
#   123456    pequeña: siempre cae en el bloque del proceso 0 -> sin speedup
#   S-1       última llave: peor caso secuencial, speedup ~ lineal por bloques
LLAVES=${LLAVES:-"$((S / 2 + 1000)) $((S / 2 - 1000)) 123456 $((S - 1))"}

make -s bruteforce

if [ ! -f "$OUT" ]; then
  echo "np;modo;bits;llave_real;llave_encontrada;tiempo_s;llaves_probadas;rep" > "$OUT"
fi

for rep in $(seq 1 "$REPS"); do
  for llave in $LLAVES; do
    for np in $NPS; do
      for modo in $MODOS; do
        # con 1 proceso ambos modos son idénticos: solo se mide una vez
        if [ "$np" -eq 1 ] && [ "$modo" != "bloques" ]; then continue; fi
        linea=$(mpirun --oversubscribe -np "$np" ./bruteforce -q \
                  -k "$llave" -b "$BITS" -m "$modo" | grep '^CSV;' | cut -d';' -f2-)
        echo "$linea;$rep" >> "$OUT"
        echo "rep=$rep llave=$llave np=$np modo=$modo -> $(echo "$linea" | cut -d';' -f6) s"
      done
    done
  done
done
echo "Resultados en $OUT. Resumen: python3 resumen.py $OUT"
