#include <stdio.h>
#include <pthread.h>
#include <math.h>
#include <time.h>
#include <stdlib.h>

#define LIMITE 1000000
#define MAX_HILOS 3

typedef struct {
    long inicio;
    long fin;
    double suma_parcial;
} Rango;

void* calcular_raices(void* arg) {
    Rango* rango = (Rango*)arg;
    double suma = 0.0;

    for (long i = rango->inicio; i <= rango->fin; i++) {
        suma += sqrt((double)i);
    }

    rango->suma_parcial = suma;
    return NULL;
}

double diferencia_segundos(struct timespec inicio, struct timespec fin) {
    return (fin.tv_sec - inicio.tv_sec) + (fin.tv_nsec - inicio.tv_nsec) / 1000000000.0;
}

double ejecutar_prueba(int cantidad_hilos, double* suma_total) {
    pthread_t hilos[MAX_HILOS];
    Rango rangos[MAX_HILOS];
    struct timespec t_inicio, t_fin;

    long bloque = LIMITE / cantidad_hilos;
    long inicio = 1;

    clock_gettime(CLOCK_MONOTONIC, &t_inicio);

    for (int i = 0; i < cantidad_hilos; i++) {
        rangos[i].inicio = inicio;

        if (i == cantidad_hilos - 1) {
            rangos[i].fin = LIMITE;
        } else {
            rangos[i].fin = inicio + bloque - 1;
        }

        rangos[i].suma_parcial = 0.0;
        pthread_create(&hilos[i], NULL, calcular_raices, &rangos[i]);
        inicio = rangos[i].fin + 1;
    }

    *suma_total = 0.0;
    for (int i = 0; i < cantidad_hilos; i++) {
        pthread_join(hilos[i], NULL);
        *suma_total += rangos[i].suma_parcial;
    }

    clock_gettime(CLOCK_MONOTONIC, &t_fin);

    return diferencia_segundos(t_inicio, t_fin);
}

int main() {
    double tiempo1, tiempo2, tiempo3;
    double suma1, suma2, suma3;

    printf("===== CALCULO DE RAICES CUADRADAS =====\n");

    printf("Prueba con 1 hilo\n");
    tiempo1 = ejecutar_prueba(1, &suma1);
    printf("Tiempo de ejecucion: %.6f segundos\n", tiempo1);
    printf("Suma de control: %.2f\n\n", suma1);

    printf("Prueba con 2 hilos\n");
    tiempo2 = ejecutar_prueba(2, &suma2);
    printf("Tiempo de ejecucion: %.6f segundos\n", tiempo2);
    printf("Suma de control: %.2f\n\n", suma2);

    printf("Prueba con 3 hilos\n");
    tiempo3 = ejecutar_prueba(3, &suma3);
    printf("Tiempo de ejecucion: %.6f segundos\n", tiempo3);
    printf("Suma de control: %.2f\n\n", suma3);

    printf("===== COMPARACION =====\n");
    printf("Con 1 hilo: %.6f segundos\n", tiempo1);
    printf("Con 2 hilos: %.6f segundos\n", tiempo2);
    printf("Con 3 hilos: %.6f segundos\n", tiempo3);

    return 0;
}
