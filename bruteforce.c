/*
 * bruteforce.c - Búsqueda por fuerza bruta de una llave DES con MPI.
 *
 * Versión corregida de bruteforce_.c. Mantiene la misma estructura
 * (decrypt, encrypt, tryKey, reparto del espacio de llaves con MPI) pero:
 *   - cifra/descifra el texto completo (el original solo procesaba 16 bytes),
 *   - corrige el desbordamiento de (0xFE << i*8) en la expansión de la llave,
 *   - lee el texto y la frase clave desde argumentos en vez de tenerlos fijos,
 *   - permite acotar el espacio de búsqueda a 2^bits llaves para poder medir,
 *   - ofrece reparto por bloques (original) o cíclico,
 *   - termina correctamente aunque la llave no esté en el espacio,
 *   - mide el tiempo con MPI_Wtime y reporta una línea CSV para análisis.
 *
 * Compilar:  make
 * Ejecutar:  mpirun -np 4 ./bruteforce -k 123456 [-f texto.txt]
 *                   [-s "frase clave"] [-b bits] [-m bloques|ciclico]
 *                   [-o cifrado.bin] [-q]
 */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <unistd.h>
#include <rpc/des_crypt.h>   /* resuelto por compat/rpc/des_crypt.h */

#define TAG_FOUND 1


/* Convierte una llave de 56 bits en los 8 bytes que espera DES: toma 7 bits
 * por byte y deja libre el bit menos significativo de cada byte para la
 * paridad, que luego ajusta des_setparity. */
static long expand_key(long key){
  long k = 0;
  for(int i=0; i<8; ++i){
    key <<= 1;
    k += (key & (0xFEL << i*8));
  }
  return k;
}

void decrypt(long key, char *ciph, int len){
  long k = expand_key(key);
  des_setparity((char *)&k);
  ecb_crypt((char *)&k, (char *) ciph, len, DES_DECRYPT);
}

void encrypt(long key, char *ciph, int len){
  long k = expand_key(key);
  des_setparity((char *)&k);
  ecb_crypt((char *)&k, (char *) ciph, len, DES_ENCRYPT);
}


char *search = "llamada Deep Crack";
int tryKey(long key, char *ciph, int len){
  char temp[len+1];
  memcpy(temp, ciph, len);
  temp[len]=0;
  decrypt(key, temp, len);
  return strstr((char *)temp, search) != NULL;
}


/* Lee el archivo completo y lo rellena con ceros hasta un múltiplo de 8,
 * porque DES cifra bloques de 8 bytes. Devuelve la longitud rellenada. */
static char *read_padded(const char *path, int *padded_len){
  FILE *f = fopen(path, "rb");
  if(!f){
    perror(path);
    return NULL;
  }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  rewind(f);
  int plen = (int)((n + 7) / 8 * 8);
  char *buf = calloc(plen + 1, 1);
  if(fread(buf, 1, n, f) != (size_t)n){
    perror(path);
    fclose(f);
    free(buf);
    return NULL;
  }
  fclose(f);
  *padded_len = plen;
  return buf;
}

static void usage(const char *prog){
  fprintf(stderr,
    "Uso: mpirun -np N %s -k LLAVE [-f texto.txt] [-s \"frase\"] [-b bits]\n"
    "                 [-m bloques|ciclico] [-o cifrado.bin] [-q]\n"
    "  -k  llave privada con la que se cifra el texto (0 <= k < 2^bits)\n"
    "  -f  archivo con el texto plano (default: texto.txt)\n"
    "  -s  frase clave que valida el descifrado (default: \"%s\")\n"
    "  -b  tamaño del espacio de búsqueda en bits, 1..56 (default: 56)\n"
    "  -m  reparto de llaves entre procesos (default: bloques)\n"
    "  -o  guarda el texto cifrado en este archivo\n"
    "  -q  modo silencioso: solo imprime la línea CSV\n", prog, search);
}


int main(int argc, char *argv[]){
  int N, id;
  long the_key = -1;
  int bits = 56;
  int cyclic = 0, quiet = 0;
  char *path = "texto.txt", *out_path = NULL;
  MPI_Status st;
  MPI_Request req;

  MPI_Init(&argc, &argv);
  MPI_Comm comm = MPI_COMM_WORLD;
  MPI_Comm_size(comm, &N);
  MPI_Comm_rank(comm, &id);

  int opt;
  while((opt = getopt(argc, argv, "k:f:s:b:m:o:q")) != -1){
    switch(opt){
      case 'k': the_key = atol(optarg); break;
      case 'f': path = optarg; break;
      case 's': search = optarg; break;
      case 'b': bits = atoi(optarg); break;
      case 'm': cyclic = (strcmp(optarg, "ciclico") == 0); break;
      case 'o': out_path = optarg; break;
      case 'q': quiet = 1; break;
      default:
        if(id == 0) usage(argv[0]);
        MPI_Finalize();
        return 1;
    }
  }
  long upper = 1L << bits;   /* el original usaba siempre 2^56 */
  if(the_key < 0 || the_key >= upper || bits < 1 || bits > 56){
    if(id == 0) usage(argv[0]);
    MPI_Finalize();
    return 1;
  }

  /* Solo el proceso 0 conoce el texto plano y la llave: cifra y reparte
   * únicamente el texto cifrado, como ocurriría en memoria distribuida. */
  int ciphlen = 0;
  char *cipher = NULL;
  if(id == 0){
    cipher = read_padded(path, &ciphlen);
    if(!cipher)
      MPI_Abort(comm, 1);
    encrypt(the_key, cipher, ciphlen);
    if(out_path){
      FILE *f = fopen(out_path, "wb");
      if(f){
        fwrite(cipher, 1, ciphlen, f);
        fclose(f);
      }
    }
  }
  MPI_Bcast(&ciphlen, 1, MPI_INT, 0, comm);
  if(id != 0)
    cipher = calloc(ciphlen + 1, 1);
  MPI_Bcast(cipher, ciphlen, MPI_CHAR, 0, comm);

  /* Reparto del espacio [0, upper):
   *  bloques: cada proceso recorre un rango contiguo (como el original).
   *  ciclico: el proceso id prueba id, id+N, id+2N, ... */
  long mylower, myupper, step;
  if(cyclic){
    mylower = id;
    myupper = upper;
    step = N;
  } else {
    long range_per_node = upper / N;
    mylower = range_per_node * id;
    myupper = (id == N-1) ? upper : range_per_node * (id+1);
    step = 1;
  }
  if(!quiet)
    printf("Proceso %d: llaves [%ld, %ld) paso %ld\n", id, mylower, myupper, step);

  long found = -1, mine = -1, tried = 0;
  int ready = 0;
  MPI_Irecv(&found, 1, MPI_LONG, MPI_ANY_SOURCE, TAG_FOUND, comm, &req);

  MPI_Barrier(comm);
  double t0 = MPI_Wtime();

  for(long i = mylower; i < myupper; i += step){
    MPI_Test(&req, &ready, MPI_STATUS_IGNORE);
    if(ready)
      break;

    tried++;
    if(tryKey(i, cipher, ciphlen)){
      mine = i;
      if(!quiet)
        printf("Proceso %d encontró la llave\n", id);
      for(int node=0; node<N; node++){
        MPI_Send(&mine, 1, MPI_LONG, node, TAG_FOUND, comm);
      }
      break;
    }
  }

  /* Un proceso que agota su rango sin encontrar nada espera aquí a los demás.
   * Así el programa termina también cuando la llave no está en el espacio
   * (en el original, el proceso 0 se quedaba bloqueado en MPI_Wait). */
  long key = -1, total_tried = 0;
  MPI_Allreduce(&mine, &key, 1, MPI_LONG, MPI_MAX, comm);
  double elapsed = MPI_Wtime() - t0;
  MPI_Reduce(&tried, &total_tried, 1, MPI_LONG, MPI_SUM, 0, comm);

  if(key >= 0){
    MPI_Wait(&req, &st);        /* el aviso siempre llega a todos */
  } else {
    MPI_Cancel(&req);
    MPI_Wait(&req, &st);
  }

  if(id == 0){
    if(!quiet){
      if(key >= 0){
        decrypt(key, cipher, ciphlen);
        printf("Llave = %ld\n\n%s\n", key, cipher);
      } else {
        printf("No se encontró ninguna llave en [0, 2^%d)\n", bits);
      }
      printf("Tiempo de búsqueda: %.6f s, llaves probadas: %ld\n",
             elapsed, total_tried);
    }
    /* np;modo;bits;llave_real;llave_encontrada;tiempo_s;llaves_probadas */
    printf("CSV;%d;%s;%d;%ld;%ld;%.6f;%ld\n", N, cyclic ? "ciclico" : "bloques",
           bits, the_key, key, elapsed, total_tried);
  }

  free(cipher);
  MPI_Finalize();
  return 0;
}
