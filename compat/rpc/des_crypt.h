/*
 * compat/rpc/des_crypt.h
 *
 * glibc >= 2.32 eliminó <rpc/des_crypt.h> junto con ecb_crypt() y
 * des_setparity(). Ubuntu 24.04 trae glibc 2.39, por lo que bruteforce_.c
 * no compila tal cual como está. Este header reimplementa esas dos funciones encima
 * de la API DES de OpenSSL (libcrypto), con la misma firma que la original.
 *
 * Uso: compilar con  -Icompat ... -lcrypto
 * Así "#include <rpc/des_crypt.h>" encuentra este archivo y el código
 * original no necesita cambios.
 */
#ifndef COMPAT_RPC_DES_CRYPT_H
#define COMPAT_RPC_DES_CRYPT_H

/* La API DES de bajo nivel está marcada "deprecated" en OpenSSL 3, pero
 * sigue disponible. Esto solo silencia las advertencias del compilador. */
#define OPENSSL_SUPPRESS_DEPRECATED
#include <openssl/des.h>

/* OpenSSL ya define DES_ENCRYPT (1) y DES_DECRYPT (0); ecb_crypt los
 * recibe tal cual, así que el código que los usa funciona sin cambios. */

#define DESERR_NONE      0
#define DESERR_NOHWDEVICE 1
#define DESERR_HWERROR   2
#define DESERR_BADPARAM  3

/* Ajusta el bit menos significativo de cada byte para paridad impar. */
static inline void des_setparity(char *key){
  DES_set_odd_parity((DES_cblock *)key);
}

/* Cifra/descifra "len" bytes de "buf" en modo ECB (bloques de 8 bytes
 * independientes) usando la llave de 8 bytes "key". Opera in-place. */
static inline int ecb_crypt(char *key, char *buf, unsigned len, unsigned mode){
  DES_key_schedule ks;
  if(len % 8 != 0)
    return DESERR_BADPARAM;
  DES_set_key_unchecked((const_DES_cblock *)key, &ks);
  for(unsigned i = 0; i < len; i += 8)
    DES_ecb_encrypt((const_DES_cblock *)(buf + i), (DES_cblock *)(buf + i),
                    &ks, (mode & 1) ? DES_ENCRYPT : DES_DECRYPT);
  return DESERR_NONE;
}

#endif
