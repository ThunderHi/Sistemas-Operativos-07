import time

LIMITE = 1_000_000
NOMBRE_ARCHIVO = "numeros_1000000.csv"

inicio = time.time()

with open(NOMBRE_ARCHIVO, "w", encoding="utf-8") as archivo:
    for numero in range(1, LIMITE + 1):
        archivo.write(f"{numero};{numero}\n")

fin = time.time()

print("===== GENERACION DE ARCHIVO =====")
print(f"Archivo generado: {NOMBRE_ARCHIVO}")
print(f"Cantidad de filas: {LIMITE}")
print(f"Formato utilizado: numero;numero")
print(f"Tiempo de ejecucion: {fin - inicio:.3f} segundos")
