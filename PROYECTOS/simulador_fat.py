import os
import shlex
import threading
import time
import random
from typing import Dict, List, Optional


# =========================
# CONFIGURACIÓN PRINCIPAL
# =========================

DB_FILE = "fat_db.txt"       # Archivo .txt que funciona como "base de datos" FAT.
GPWD = 0                     # Global Present Working Directory: ID del directorio actual.
lock = threading.Lock()      # Lock global para evitar escrituras simultáneas en fat_db.txt.

USUARIO = "Thunder"
HOST = "UBUNTUSON4"

# ── Límites y caracteres inválidos ────────
MAX_NOMBRE = 50          # Máximo de caracteres permitidos en un nombre.
# Caracteres prohibidos: separador de campo | y separadores de ruta / \
# También bloqueamos caracteres de control y otros problemáticos.
CHARS_INVALIDOS = set('|/\\:*?"<>\t\n\r')

# Códigos ANSI para dar apariencia similar a una terminal de Ubuntu.
RESET = "\033[0m"
VERDE = "\033[92m"
AZUL = "\033[94m"
AMARILLO = "\033[93m"
ROJO = "\033[91m"
CYAN = "\033[96m"
GRIS = "\033[90m"
NEGRITA = "\033[1m"


# =========================
# FUNCIONES DE BASE DE DATOS
# =========================

def activar_colores_windows() -> None:
    """
    Intenta habilitar colores ANSI en Windows.
    En Linux no hace falta, pero esta línea no afecta la ejecución.
    """
    if os.name == "nt":
        os.system("")


def crear_registro(id_: int, nombre: str, tipo: str, padre: int, permisos: str, tamanio: str) -> Dict[str, str]:
    """
    Crea un diccionario con la estructura de un registro FAT.
    Se usa para mantener el código más ordenado y evitar repetir llaves.
    """
    return {
        "id": str(id_),
        "nombre": nombre,
        "tipo": tipo,
        "padre": str(padre),
        "permisos": permisos,
        "tamanio": str(tamanio)
    }


def serializar_registro(registro: Dict[str, str]) -> str:
    """
    Convierte un registro del programa a una línea de texto para guardarla en fat_db.txt.
    """
    return (
        f"{registro['id']}|{registro['nombre']}|{registro['tipo']}|"
        f"{registro['padre']}|{registro['permisos']}|{registro['tamanio']}"
    )


def deserializar_registro(linea: str) -> Optional[Dict[str, str]]:
    """
    Convierte una línea de fat_db.txt a un diccionario.
    Si la línea está mal formada, la ignora devolviendo None.
    """
    partes = linea.strip().split("|")

    if len(partes) != 6:
        return None

    # Validar que id y padre sean enteros válidos.
    try:
        int(partes[0])
        int(partes[3])
    except ValueError:
        return None

    return {
        "id": partes[0],
        "nombre": partes[1],
        "tipo": partes[2],
        "padre": partes[3],
        "permisos": partes[4],
        "tamanio": partes[5]
    }


def inicializar_db() -> None:
    """
    Crea fat_db.txt si no existe.
    También asegura que el directorio raíz exista con ID 0.
    """
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        raiz = crear_registro(0, "/", "DIR", -1, "rwx", "-")
        with open(DB_FILE, "w", encoding="utf-8") as archivo:
            archivo.write(serializar_registro(raiz) + "\n")


def leer_registros() -> List[Dict[str, str]]:
    """
    Lee todos los registros almacenados en fat_db.txt.
    Devuelve una lista de diccionarios.
    """
    registros = []

    if not os.path.exists(DB_FILE):
        inicializar_db()

    with open(DB_FILE, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            registro = deserializar_registro(linea)
            if registro is not None:
                registros.append(registro)

    return registros


def escribir_registros(registros: List[Dict[str, str]]) -> None:
    """
    Sobrescribe fat_db.txt con la lista actualizada de registros.
    Esta función debe llamarse dentro de un lock cuando haya hilos.
    """
    with open(DB_FILE, "w", encoding="utf-8") as archivo:
        for registro in registros:
            archivo.write(serializar_registro(registro) + "\n")


def obtener_siguiente_id(registros: List[Dict[str, str]]) -> int:
    """
    Calcula el siguiente ID disponible.
    Se toma el ID mayor y se suma 1.
    """
    if not registros:
        return 0

    ids = [int(r["id"]) for r in registros]
    return max(ids) + 1


def buscar_por_id(registros: List[Dict[str, str]], id_: int) -> Optional[Dict[str, str]]:
    """
    Busca un archivo o directorio usando su ID.
    """
    for registro in registros:
        if int(registro["id"]) == id_:
            return registro
    return None


def buscar_en_directorio(registros: List[Dict[str, str]], nombre: str, padre: int) -> Optional[Dict[str, str]]:
    """
    Busca un archivo o directorio por nombre dentro del directorio actual.
    Esto evita confundir archivos con el mismo nombre ubicados en carpetas distintas.
    """
    for registro in registros:
        if registro["nombre"] == nombre and int(registro["padre"]) == padre:
            return registro
    return None


def obtener_contenido(registros: List[Dict[str, str]], padre: int) -> List[Dict[str, str]]:
    """
    Devuelve todos los elementos cuyo padre es el directorio actual.
    """
    return [r for r in registros if int(r["padre"]) == padre]


def obtener_ruta_actual() -> str:
    """
    Construye la ruta actual a partir del ID guardado en GPWD.
    Ejemplo: /DIR3/Tareas
    """
    global GPWD

    registros = leer_registros()

    if GPWD == 0:
        return "/"

    partes = []
    actual = GPWD

    while actual != 0:
        registro = buscar_por_id(registros, actual)

        if registro is None:
            return "/"

        partes.append(registro["nombre"])
        actual = int(registro["padre"])

    partes.reverse()
    return "/" + "/".join(partes)


def obtener_prompt() -> str:
    """
    Genera un prompt estilo Ubuntu:
    Thunder@UBUNTUSO4:/ruta$
    """
    ruta = obtener_ruta_actual()
    return f"{VERDE}{USUARIO}@{HOST}{RESET}:{AZUL}{ruta}{RESET}$ "


def validar_permisos(permisos: str) -> bool:
    """
    Valida permisos en formato de tres caracteres:
    r = lectura, w = escritura, x = ejecución, - = permiso desactivado.

    Formatos válidos:
    rwx, rw-, r--, -w-, --x, ---
    """
    if len(permisos) != 3:
        return False

    return (
        permisos[0] in ("r", "-") and
        permisos[1] in ("w", "-") and
        permisos[2] in ("x", "-")
    )


def validar_nombre(nombre: str) -> Optional[str]:
    """
    Valida que un nombre de archivo o directorio sea seguro y usable.
    Devuelve None si es válido, o un mensaje de error si no lo es.
    """
    if not nombre or nombre.strip() == "":
        return "El nombre no puede estar vacío."
    if nombre in (".", ".."):
        return f"'{nombre}' es un nombre reservado."
    if len(nombre) > MAX_NOMBRE:
        return f"El nombre es demasiado largo (máximo {MAX_NOMBRE} caracteres)."
    chars_encontrados = CHARS_INVALIDOS.intersection(set(nombre))
    if chars_encontrados:
        mostrar = " ".join(sorted(chars_encontrados))
        return f"El nombre contiene caracteres inválidos: {mostrar}"
    return None


def tiene_permiso_escritura(registro: Dict[str, str]) -> bool:
    """
    Verifica si un registro tiene permiso de escritura.
    Se usa para personalizar mejor el simulador.
    """
    return len(registro["permisos"]) >= 2 and registro["permisos"][1] == "w"


# =========================
# COMANDOS DEL SIMULADOR
# =========================

def cmd_mkdir(nombre: str) -> None:
    """
    mkdir <nombre>
    Crea un directorio dentro del directorio actual.
    """
    global GPWD

    # FIX 2 & 3: validación centralizada de nombre.
    error = validar_nombre(nombre)
    if error:
        print(f"{ROJO}Error:{RESET} {error}")
        return

    with lock:
        registros = leer_registros()

        actual = buscar_por_id(registros, GPWD)
        if actual is None or actual["tipo"] != "DIR":
            print(f"{ROJO}Error:{RESET} el directorio actual no existe.")
            return

        if not tiene_permiso_escritura(actual):
            print(f"{ROJO}Error:{RESET} no hay permiso de escritura en el directorio actual.")
            return

        if buscar_en_directorio(registros, nombre, GPWD) is not None:
            print(f"{ROJO}Error:{RESET} ya existe un archivo o directorio llamado '{nombre}'.")
            return

        nuevo_id = obtener_siguiente_id(registros)
        nuevo_dir = crear_registro(nuevo_id, nombre, "DIR", GPWD, "rwx", "-")

        registros.append(nuevo_dir)
        escribir_registros(registros)

    print(f"Directorio '{nombre}' creado correctamente.")


def cmd_touch(nombre: str, padre_personalizado: Optional[int] = None, silencioso: bool = False) -> None:
    """
    touch <nombre>
    Crea un archivo vacío dentro del directorio actual.

    padre_personalizado se usa en la prueba con hilos para que todos creen archivos
    en el mismo directorio aunque GPWD cambie después.
    """
    global GPWD

    padre = GPWD if padre_personalizado is None else padre_personalizado

    # FIX 2 & 3: validación centralizada de nombre.
    error = validar_nombre(nombre)
    if error:
        print(f"{ROJO}Error:{RESET} {error}")
        return

    with lock:
        registros = leer_registros()

        actual = buscar_por_id(registros, padre)
        if actual is None or actual["tipo"] != "DIR":
            print(f"{ROJO}Error:{RESET} el directorio destino no existe.")
            return

        if not tiene_permiso_escritura(actual):
            print(f"{ROJO}Error:{RESET} no hay permiso de escritura en el directorio destino.")
            return

        nombre_final = generar_nombre_unico(registros, nombre, padre)

        nuevo_id = obtener_siguiente_id(registros)
        nuevo_archivo = crear_registro(nuevo_id, nombre_final, "FILE", padre, "rw-", "0")

        registros.append(nuevo_archivo)
        escribir_registros(registros)

    if not silencioso:
        if nombre_final == nombre:
            print(f"Archivo '{nombre}' creado correctamente.")
        else:
            print(f"Archivo '{nombre_final}' creado correctamente. El nombre fue ajustado para evitar duplicados.")


def generar_nombre_unico(registros: List[Dict[str, str]], nombre: str, padre: int) -> str:
    """
    Si un nombre ya existe en el directorio, genera uno parecido:
    archivo.txt -> archivo_2.txt
    hilo_1.txt -> hilo_1_2.txt

    Esto ayuda bastante cuando test_hilos se ejecuta más de una vez.
    """
    if buscar_en_directorio(registros, nombre, padre) is None:
        return nombre

    if "." in nombre:
        base, extension = nombre.rsplit(".", 1)
        extension = "." + extension
    else:
        base, extension = nombre, ""

    contador = 2

    while True:
        candidato = f"{base}_{contador}{extension}"
        if buscar_en_directorio(registros, candidato, padre) is None:
            return candidato
        contador += 1


def cmd_ls() -> None:
    """
    ls
    Muestra los nombres de archivos y directorios del directorio actual.
    """
    global GPWD

    registros = leer_registros()
    contenido = obtener_contenido(registros, GPWD)

    if not contenido:
        print("(directorio vacío)")
        return

    for registro in contenido:
        if registro["tipo"] == "DIR":
            print(f"{AZUL}{registro['nombre']}{RESET}")
        else:
            print(registro["nombre"])


def cmd_ls_l() -> None:
    """
    ls -l
    Muestra información detallada del contenido actual:
    ID, tipo, permisos, tamaño y nombre.
    """
    global GPWD

    registros = leer_registros()
    contenido = obtener_contenido(registros, GPWD)

    if not contenido:
        print("(directorio vacío)")
        return

    print(f"{'ID':<5} | {'TIPO':<5} | {'PERMISOS':<9} | {'TAMAÑO':<7} | NOMBRE")
    print("-" * 58)

    for registro in contenido:
        nombre = registro["nombre"]

        if registro["tipo"] == "DIR":
            nombre = f"{AZUL}{nombre}{RESET}"

        print(
            f"{registro['id']:<5} | "
            f"{registro['tipo']:<5} | "
            f"{registro['permisos']:<9} | "
            f"{registro['tamanio']:<7} | "
            f"{nombre}"
        )


def cmd_cd(destino: str) -> None:
    """
    cd <directorio>
    Cambia el directorio actual usando la variable global GPWD.
    También acepta:
    cd ..
    cd /
    """
    global GPWD

    registros = leer_registros()

    if destino == "/":
        GPWD = 0
        print("Directorio actual cambiado a: /")
        return

    if destino == "..":
        actual = buscar_por_id(registros, GPWD)

        if actual is None:
            GPWD = 0
            print("Directorio actual cambiado a: /")
            return

        padre = int(actual["padre"])

        if padre == -1:
            print("Ya estás en el directorio raíz.")
        else:
            GPWD = padre
            print(f"Directorio actual cambiado a: {obtener_ruta_actual()}")

        return

    encontrado = buscar_en_directorio(registros, destino, GPWD)

    if encontrado is None or encontrado["tipo"] != "DIR":
        # Distinguir "no existe" de "existe pero es un archivo".
        # es confuso si el archivo sí existe con ese nombre en el directorio.
        if encontrado is not None and encontrado["tipo"] == "FILE":
            print(f"{ROJO}Error:{RESET} '{destino}' es un archivo, no un directorio.")
        else:
            print(f"{ROJO}Error:{RESET} directorio '{destino}' no encontrado.")
        return

    GPWD = int(encontrado["id"])
    print(f"Directorio actual cambiado a: {obtener_ruta_actual()}")


def cmd_chmod(permisos: str, nombre: str) -> None:
    """
    chmod <permisos> <nombre>
    Cambia los permisos de un archivo o directorio.
    """
    global GPWD

    if not validar_permisos(permisos):
        print(f"{ROJO}Permisos inválidos.{RESET}")
        print("Usa exactamente 3 caracteres en este orden: r w x")
        print("Ejemplos válidos: rwx, rw-, r--, -w-, --x, ---")
        return

    with lock:
        registros = leer_registros()
        encontrado = buscar_en_directorio(registros, nombre, GPWD)

        if encontrado is None:
            print(f"{ROJO}Error:{RESET} '{nombre}' no encontrado.")
            return

        encontrado["permisos"] = permisos
        escribir_registros(registros)

    print(f"Permisos de '{nombre}' cambiados a {permisos}.")


def cmd_rm(nombre: str) -> None:
    """
    rm <archivo>
    Elimina un archivo del directorio actual.
    Por seguridad, este comando no elimina directorios.
    """
    global GPWD

    with lock:
        registros = leer_registros()
        encontrado = buscar_en_directorio(registros, nombre, GPWD)

        if encontrado is None:
            print(f"{ROJO}Error:{RESET} archivo '{nombre}' no encontrado.")
            return

        if encontrado["tipo"] != "FILE":
            print(f"{ROJO}Error:{RESET} '{nombre}' es un directorio. Este rm solo elimina archivos.")
            return
        """
        este guard evita que GPWD quede apuntando a un ID que ya no existe en fat_db.txt,
        lo que causaría que ls y otros comandos devuelvan resultados vacíos sin ningún mensaje de error.
        """
        if int(encontrado["id"]) == GPWD:
            print(f"{ROJO}Error:{RESET} no se puede eliminar el directorio actual.")
            return

        registros.remove(encontrado)
        escribir_registros(registros)

    print(f"Archivo '{nombre}' eliminado correctamente.")


def cmd_pwd() -> None:
    """
    pwd
    Muestra la ruta actual.
    """
    print(obtener_ruta_actual())


def cmd_tree(padre: Optional[int] = None, prefijo: str = "") -> None:
    """
    tree
    Muestra la estructura de directorios y archivos desde la ruta actual.
    Es un comando extra para diferenciar este proyecto.
    """
    global GPWD

    if padre is None:
        padre = GPWD
        print(f"{AZUL}.{RESET}")

    registros = leer_registros()
    contenido = obtener_contenido(registros, padre)

    for indice, registro in enumerate(contenido):
        es_ultimo = indice == len(contenido) - 1
        conector = "└── " if es_ultimo else "├── "
        nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")

        nombre = registro["nombre"]
        if registro["tipo"] == "DIR":
            print(prefijo + conector + f"{AZUL}{nombre}{RESET}")
            cmd_tree(int(registro["id"]), nuevo_prefijo)
        else:
            print(prefijo + conector + nombre)


def cmd_neofetch() -> None:
    ruta = obtener_ruta_actual()

    LOGO = [
        " _____ ",
        "|_   _|",
        "  | |  ",
        "  | |  ",
        "  |_|  ",
    ]

    INFO = [
        f"{VERDE}{USUARIO}@{HOST}{RESET}",
        f"{GRIS}-------------------{RESET}",
        f"{AZUL}OS{RESET}     Thunder FAT Simulator",
        f"{AZUL}Shell{RESET}  Python Terminal",
        f"{AZUL}Dir{RESET}    {ruta}",
        f"{AZUL}DB{RESET}     {DB_FILE}",
    ]

    print()
    for i in range(max(len(LOGO), len(INFO))):
        lado_logo = LOGO[i] if i < len(LOGO) else " " * 7
        lado_info = INFO[i] if i < len(INFO) else ""
        print(f"  {AMARILLO}{lado_logo}{RESET}   {lado_info}")
    print()


def cmd_help() -> None:
    """
    help
    Muestra los comandos disponibles.
    """
    print(f"""
{NEGRITA}Comandos disponibles:{RESET}
  mkdir <directorio>        Crea un directorio.
  cd <directorio>           Entra a un directorio.
  cd ..                     Regresa al directorio anterior.
  cd /                      Regresa a la raíz.
  touch <archivo>           Crea un archivo vacío.
  ls                        Lista el contenido.
  ls -l                     Lista con detalle.
  chmod <permisos> <nombre> Cambia permisos. Ejemplo: chmod r-- nota.txt
  rm <archivo>              Elimina un archivo.
  pwd                       Muestra la ruta actual.
  tree                      Muestra el árbol desde el directorio actual.
  test_hilos [cantidad]     Crea archivos usando hilos y Lock.
  neofetch                  Muestra una pantalla estilo Ubuntu personalizada.
  clear                     Limpia la pantalla.
  help                      Muestra esta ayuda.
  exit                      Sale del simulador.
""")


# =========================
# HILOS Y CONCURRENCIA
# =========================

def crear_archivo_hilo(numero: int, padre: int) -> None:
    """
    Función ejecutada por cada hilo.
    Cada hilo intenta crear un archivo al mismo tiempo.
    El Lock usado dentro de cmd_touch evita condiciones de carrera.
    """
    nombre = f"hilo_{numero}.txt"

    print(f"Hilo {numero} creando archivo {nombre}")

    # Pausa pequeña y aleatoria para simular que los hilos se ejecutan en momentos distintos.
    time.sleep(random.uniform(0.05, 0.25))

    cmd_touch(nombre, padre_personalizado=padre, silencioso=True)


def cmd_test_hilos(cantidad: int = 5) -> None:
    """
    test_hilos [cantidad]
    Lanza varios hilos que crean archivos en el mismo directorio.
    """
    global GPWD

    if cantidad <= 0:
        print(f"{ROJO}Error:{RESET} la cantidad de hilos debe ser mayor que 0.")
        return

    if cantidad > 20:
        print(f"{ROJO}Error:{RESET} por seguridad usa máximo 20 hilos.")
        return

    directorio_objetivo = GPWD
    hilos = []

    print("Iniciando prueba concurrente con hilos...")

    for i in range(1, cantidad + 1):
        hilo = threading.Thread(target=crear_archivo_hilo, args=(i, directorio_objetivo))
        hilos.append(hilo)

    # Se inician todos los hilos.
    for hilo in hilos:
        hilo.start()

    # join() espera a que cada hilo termine antes de continuar el programa.
    for hilo in hilos:
        hilo.join()

    print("Todos los hilos finalizaron correctamente.")


# =========================
# INTERFAZ PRINCIPAL
# =========================

def mostrar_banner() -> None:
    """
    Muestra la pantalla inicial personalizada.
    """
    print(f"""{CYAN}
╔══════════════════════════════════════════════╗
║        SIMULADOR FAT EN PYTHON               ║
╚══════════════════════════════════════════════╝
{RESET}Sistema FAT inicializado correctamente.
Directorio actual: {obtener_ruta_actual()}
Escribe {AMARILLO}help{RESET} para ver los comandos disponibles.
""")


def procesar_comando(entrada: str) -> bool:
    """
    Recibe una línea escrita por el usuario, la separa en partes y ejecuta el comando.
    Devuelve False cuando el usuario desea salir.
    """
    if not entrada.strip():
        return True

    try:
        partes = shlex.split(entrada)
    except ValueError:
        print(f"{ROJO}Error:{RESET} revisa las comillas del comando.")
        return True

    comando = partes[0]

    if comando == "exit":
        print("Saliendo del simulador FAT...")
        return False

    elif comando == "help":
        cmd_help()

    elif comando == "clear":
        os.system("cls" if os.name == "nt" else "clear")

    elif comando == "neofetch":
        cmd_neofetch()

    elif comando == "pwd":
        cmd_pwd()

    elif comando == "tree":
        cmd_tree()

    elif comando == "mkdir":
        if len(partes) != 2:
            print("Uso correcto: mkdir <nombre_directorio>")
        else:
            cmd_mkdir(partes[1])

    elif comando == "cd":
        if len(partes) != 2:
            print("Uso correcto: cd <directorio>  o  cd ..")
        else:
            cmd_cd(partes[1])

    elif comando == "touch":
        if len(partes) != 2:
            print("Uso correcto: touch <nombre_archivo>")
        else:
            cmd_touch(partes[1])

    elif comando == "ls":
        if len(partes) == 1:
            cmd_ls()
        elif len(partes) == 2 and partes[1] == "-l":
            cmd_ls_l()
        else:
            print("Uso correcto: ls  o  ls -l")

    elif comando == "chmod":
        if len(partes) != 3:
            print("Uso correcto: chmod <permisos> <nombre>")
            print("Ejemplo: chmod r-- a.txt")
        else:
            cmd_chmod(partes[1], partes[2])

    elif comando == "rm":
        if len(partes) != 2:
            print("Uso correcto: rm <nombre_archivo>")
        else:
            cmd_rm(partes[1])

    elif comando == "test_hilos":
        if len(partes) == 1:
            cmd_test_hilos()
        elif len(partes) == 2 and partes[1].isdigit():
            cantidad = int(partes[1])
            if cantidad < 1:
                print(f"{ROJO}Error:{RESET} la cantidad debe ser al menos 1.")
            else:
                cmd_test_hilos(cantidad)
        else:
            print("Uso correcto: test_hilos  o  test_hilos <cantidad>")

    else:
        print(f"{ROJO}Comando no reconocido:{RESET} {comando}")
        print("Escribe 'help' para ver los comandos disponibles.")

    return True


def main() -> None:
    """
    Punto de entrada del programa.
    Inicializa la base FAT y mantiene el ciclo interactivo del shell.
    """
    activar_colores_windows()
    inicializar_db()
    mostrar_banner()

    activo = True

    while activo:
        try:
            entrada = input(obtener_prompt())
            activo = procesar_comando(entrada)
        except KeyboardInterrupt:
            print("\nUsa 'exit' para salir correctamente.")
        except EOFError:
            print("\nSaliendo del simulador FAT...")
            break


if __name__ == "__main__":
    main()
