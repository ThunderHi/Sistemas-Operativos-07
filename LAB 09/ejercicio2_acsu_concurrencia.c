#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

#define NUM_CUENTAS 10000
#define CUENTA_OBJETIVO 100
#define NUM_HILOS 10

typedef struct {
    int id;
    int saldo;
} Cuenta;

Cuenta ACSU[NUM_CUENTAS];
pthread_mutex_t mutex;

void inicializar_cuentas() {
    for (int i = 0; i < NUM_CUENTAS; i++) {
        ACSU[i].id = i;
        ACSU[i].saldo = 0;
    }
    ACSU[CUENTA_OBJETIVO].saldo = 2;
}

void* sumar_sin_mutex(void* arg) {
    int saldo_temporal;

    saldo_temporal = ACSU[CUENTA_OBJETIVO].saldo;
    usleep(1000);
    saldo_temporal = saldo_temporal + 1;
    ACSU[CUENTA_OBJETIVO].saldo = saldo_temporal;

    return NULL;
}

void* sumar_con_mutex(void* arg) {
    pthread_mutex_lock(&mutex);

    int saldo_temporal = ACSU[CUENTA_OBJETIVO].saldo;
    usleep(1000);
    saldo_temporal = saldo_temporal + 1;
    ACSU[CUENTA_OBJETIVO].saldo = saldo_temporal;

    pthread_mutex_unlock(&mutex);
    return NULL;
}

void ejecutar_prueba_sin_mutex() {
    pthread_t hilos[NUM_HILOS];

    inicializar_cuentas();

    for (int i = 0; i < NUM_HILOS; i++) {
        pthread_create(&hilos[i], NULL, sumar_sin_mutex, NULL);
    }

    for (int i = 0; i < NUM_HILOS; i++) {
        pthread_join(hilos[i], NULL);
    }

    printf("Sin mutex -> saldo final de cuenta 100: %d\n", ACSU[CUENTA_OBJETIVO].saldo);
}

void ejecutar_prueba_con_mutex() {
    pthread_t hilos[NUM_HILOS];

    inicializar_cuentas();
    pthread_mutex_init(&mutex, NULL);

    for (int i = 0; i < NUM_HILOS; i++) {
        pthread_create(&hilos[i], NULL, sumar_con_mutex, NULL);
    }

    for (int i = 0; i < NUM_HILOS; i++) {
        pthread_join(hilos[i], NULL);
    }

    pthread_mutex_destroy(&mutex);

    printf("Con mutex -> saldo final de cuenta 100: %d\n", ACSU[CUENTA_OBJETIVO].saldo);
}

int main() {
    int esperado = 2 + NUM_HILOS;

    printf("===== SIMULACION ACSU =====\n");
    printf("Cuenta objetivo: %d\n", CUENTA_OBJETIVO);
    printf("Saldo inicial: 2\n");
    printf("Cantidad de hilos: %d\n", NUM_HILOS);
    printf("Resultado esperado: %d\n\n", esperado);

    ejecutar_prueba_sin_mutex();
    ejecutar_prueba_con_mutex();

    return 0;
}
