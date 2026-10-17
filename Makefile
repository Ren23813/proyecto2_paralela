CC      = mpicc
CFLAGS  = -O2 -Wall -Icompat
LDLIBS  = -lcrypto

all: bruteforce bruteforce_original

bruteforce: bruteforce.c compat/rpc/des_crypt.h
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

# Código entregado por el docente, sin modificar (solo usa el header de compatibilidad)
bruteforce_original: bruteforce_.c compat/rpc/des_crypt.h
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

clean:
	rm -f bruteforce bruteforce_original

.PHONY: all clean
