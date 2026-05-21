#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>
#include <pthread.h>
#include <stdlib.h>

void* imprimir_letras(void* arg) {
    for (char c = 'A'; c <= 'E'; c++) {
        printf("Hilo: %c\n", c);
        usleep(100000);
    }
    return NULL;
}

int main() {
    pid_t pid;
    pthread_t hilo;

    printf("PROGRAMA PRINCIPAL\n");
    printf("PID del proceso padre: %d\n\n", getpid());
    fflush(stdout);

    pid = fork();

    if (pid < 0) {
        perror("Error al crear el proceso hijo");
        return 1;
    }

    if (pid == 0) {
        for (int i = 1; i <= 5; i++) {
            printf("Proceso hijo: %d\n", i);
            usleep(100000);
        }
        exit(0);
    } else {
        if (pthread_create(&hilo, NULL, imprimir_letras, NULL) != 0) {
            perror("Error al crear el hilo");
            return 1;
        }

        wait(NULL);
        pthread_join(hilo, NULL);

        printf("\nProceso padre: el proceso hijo y el hilo terminaron.\n");
        printf("Proceso padre: finalizando programa.\n");
    }

    return 0;
}
