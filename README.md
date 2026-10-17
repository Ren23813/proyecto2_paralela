# Proyecto 2 – Fuerza bruta DES con MPI

## Requisitos (Ubuntu / WSL)

```bash
sudo apt install build-essential openmpi-bin libopenmpi-dev libssl-dev
```

## ¿Por qué no compila `bruteforce_.c` tal cual?

`bruteforce_.c` usa `ecb_crypt()` y `des_setparity()` de `<rpc/des_crypt.h>`.
glibc eliminó ese header a partir de la versión 2.32 (Ubuntu 24.04 trae 2.39),
así que el error no viene de WSL sino de la versión de la biblioteca de C.

[compat/rpc/des_crypt.h](compat/rpc/des_crypt.h) reimplementa esas dos funciones
con la misma firma usando DES de OpenSSL. Compilando con `-Icompat -lcrypto`, el
código original compila sin cambios.

## Compilar

```bash
make            # genera ./bruteforce (corregido) y ./bruteforce_original
```

## Ejecutar

```bash
mpirun -np 4 ./bruteforce -k 123456 -b 20          # busca en 2^20 llaves
mpirun -np 4 ./bruteforce -k 123456 -b 20 -m ciclico
mpirun -np 1 ./bruteforce -k 123456 -b 20 -o cifrado.bin   # guarda el texto cifrado
```

| Opción | Significado | Default |
|---|---|---|
| `-k` | llave privada con la que se cifra el texto | (obligatoria) |
| `-f` | archivo con el texto plano | `texto.txt` |
| `-s` | frase clave que valida el descifrado | `llamada Deep Crack` |
| `-b` | tamaño del espacio de búsqueda (2^b llaves, 1..56) | 56 |
| `-m` | reparto: `bloques` (como el original) o `ciclico` | `bloques` |
| `-o` | archivo donde guardar el texto cifrado | – |
| `-q` | solo imprime la línea `CSV;...` | – |

`texto.txt` tiene 356 palabras.

## Mediciones

```bash
./medir.sh 5 resultados.csv        # 5 repeticiones de cada caso
python3 resumen.py resultados.csv  # promedios, speedup y eficiencia
```

Se puede cambiar el experimento con variables de entorno, p. ej.
`BITS=22 NPS="1 2 4 8 16" LLAVES="1000 2097151" ./medir.sh 3`.

## Bugs del código original corregidos en `bruteforce.c`

1. `ecb_crypt(..., 16, ...)`: solo cifraba/descifraba los primeros 16 bytes;
   el resto del texto quedaba en claro.
2. La frase de búsqueda `" los mismos del proyecto 1 "` no aparece en el texto
   (allí está entre paréntesis), así que `tryKey` nunca daba positivo.
3. `0xFE << i*8` es un `int`: para `i >= 4` el corrimiento es comportamiento
   indefinido. Se usa `0xFEL`.
4. `the_key = 2^54`: con reparto por bloques y espacio 2^56, un solo proceso
   tendría que probar ~1.8·10^16 llaves antes de llegar a ella.
5. Si la llave no estaba en el espacio, el proceso 0 quedaba bloqueado para
   siempre en `MPI_Wait`.
6. El ciclo `i < myupper` con `myupper = ... - 1` se saltaba la última llave de
   cada rango.
