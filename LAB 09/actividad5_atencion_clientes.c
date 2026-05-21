#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

void* atender_cliente(void* arg) {
    int id = *(int*)arg;
    printf("Atendiendo cliente %d...\n", id);
    sleep(1);
    printf("Cliente %d atendido correctamente.\n", id);
    return NULL;
}

int main() {
    pthread_t hilos[3];
    int clientes[3] = {1, 2, 3};

    for (int i = 0; i < 3; i++) {
        pthread_create(&hilos[i], NULL, atender_cliente, &clientes[i]);
    }

    for (int i = 0; i < 3; i++) {
        pthread_join(hilos[i], NULL);
    }

    printf("Todos los clientes fueron atendidos.\n");
    return 0;
}
