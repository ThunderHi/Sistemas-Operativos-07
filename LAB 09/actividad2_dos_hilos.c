#include <stdio.h>
#include <pthread.h>

void* imprimir_numeros(void* arg) {
    for (int i = 1; i <= 5; i++) {
        printf("Numero: %d\n", i);
    }
    return NULL;
}

void* imprimir_letras(void* arg) {
    for (char c = 'A'; c <= 'E'; c++) {
        printf("Letra: %c\n", c);
    }
    return NULL;
}

int main() {
    pthread_t h1, h2;

    pthread_create(&h1, NULL, imprimir_numeros, NULL);
    pthread_create(&h2, NULL, imprimir_letras, NULL);

    pthread_join(h1, NULL);
    pthread_join(h2, NULL);

    printf("Tareas finalizadas.\n");
    return 0;
}
