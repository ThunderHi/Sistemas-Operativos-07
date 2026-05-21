#include <stdio.h>
#include <pthread.h>

void* mensaje(void* arg) {
    printf("Soy un hilo creado en C\n");
    return NULL;
}

int main() {
    pthread_t hilo;

    pthread_create(&hilo, NULL, mensaje, NULL);
    pthread_join(hilo, NULL);

    printf("Fin del programa principal\n");
    return 0;
}
