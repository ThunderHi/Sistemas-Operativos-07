import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import time
import threading


# ─────────────────────────────────────────────
#  MODELO
# ─────────────────────────────────────────────

class Proceso:
    """Representa un proceso del sistema operativo."""

    COLORES_ALTA   = ["#D85A30", "#993C1D", "#BA7517", "#854F0B"]
    COLORES_BAJA   = ["#378ADD", "#185FA5", "#1D9E75", "#0F6E56"]
    _contador_color = {1: 0, 2: 0}

    def __init__(self, nombre: str, tiempo_ms: int, prioridad: int):
        self.nombre    = nombre
        self.tiempo    = tiempo_ms          # burst total en ms
        self.prioridad = prioridad          # 1 = Alta, 2 = Baja
        self.restante  = tiempo_ms          # tiempo restante
        idx = Proceso._contador_color[prioridad] % 4
        Proceso._contador_color[prioridad] += 1
        paleta = Proceso.COLORES_ALTA if prioridad == 1 else Proceso.COLORES_BAJA
        self.color = paleta[idx]

    @classmethod
    def reset_colores(cls):
        cls._contador_color = {1: 0, 2: 0}


def construir_pasos(procesos: list, quantum: int) -> list:
    """
    Simula Round Robin con prioridad (alta primero).
    Devuelve lista de dicts: {proceso, duracion, t_inicio, t_fin}
    """
    cola = deque(sorted(procesos, key=lambda p: p.prioridad))
    pasos = []
    t = 0
    while cola:
        p = cola.popleft()
        dur = min(p.restante, quantum)
        pasos.append({"proceso": p, "duracion": dur, "t_inicio": t, "t_fin": t + dur})
        p.restante -= dur
        t += dur
        if p.restante > 0:
            cola.append(p)
    return pasos


# ─────────────────────────────────────────────
#  INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────

class App(tk.Tk):

    PX_POR_MS = 1.4          # píxeles por milisegundo en el canvas
    ALTO_BARRA = 56          # alto del bloque de proceso en el Gantt
    Y_BARRA    = 28          # y donde empieza la barra
    ALTO_CANVAS = 110        # alto total del canvas Gantt

    def __init__(self):
        super().__init__()
        self.title("Simulador CPU — Round Robin con Prioridades")
        self.configure(bg="#F5F4F0")
        self.resizable(True, True)
        self.minsize(860, 640)

        self._procesos: list[Proceso] = []
        self._contador_proc = 0
        self._pasos: list  = []
        self._paso_actual  = 0
        self._pixel_offset = 0
        self._animando     = False
        self._pausado      = False
        self._hilo_anim    = None
        self._velocidad_ms = 180   # delay entre pasos en ms

        self._build_ui()
        self._cargar_demo()

    # ── construcción de la UI ──────────────────

    def _build_ui(self):
        # Panel izquierdo (controles)
        left = tk.Frame(self, bg="#F5F4F0", width=280)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 8), pady=16)
        left.pack_propagate(False)

        # Panel derecho (Gantt + estadísticas)
        right = tk.Frame(self, bg="#F5F4F0")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 16), pady=16)

        self._build_left(left)
        self._build_right(right)

    def _lbl_seccion(self, parent, texto):
        tk.Label(parent, text=texto.upper(), bg="#F5F4F0",
                 fg="#888780", font=("Helvetica", 8, "bold"),
                 anchor="w").pack(fill=tk.X, pady=(12, 4))

    def _build_left(self, parent):
        # ── Agregar proceso ──
        self._lbl_seccion(parent, "Agregar proceso")

        fila = tk.Frame(parent, bg="#F5F4F0")
        fila.pack(fill=tk.X)

        tk.Label(fila, text="Tiempo (ms)", bg="#F5F4F0",
                 fg="#5F5E5A", font=("Helvetica", 10)).grid(row=0, column=0, sticky="w")
        self._var_tiempo = tk.IntVar(value=80)
        tk.Spinbox(fila, from_=5, to=500, increment=5,
                   textvariable=self._var_tiempo, width=7,
                   font=("Courier", 11)).grid(row=0, column=1, padx=(6, 0))

        tk.Label(fila, text="Prioridad", bg="#F5F4F0",
                 fg="#5F5E5A", font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self._var_prio = tk.IntVar(value=1)
        frame_radio = tk.Frame(fila, bg="#F5F4F0")
        frame_radio.grid(row=1, column=1, sticky="w", padx=(6, 0))
        tk.Radiobutton(frame_radio, text="Alta (1)", variable=self._var_prio, value=1,
                       bg="#F5F4F0", fg="#D85A30", font=("Helvetica", 10),
                       activebackground="#F5F4F0").pack(side=tk.LEFT)
        tk.Radiobutton(frame_radio, text="Baja (2)", variable=self._var_prio, value=2,
                       bg="#F5F4F0", fg="#185FA5", font=("Helvetica", 10),
                       activebackground="#F5F4F0").pack(side=tk.LEFT)

        tk.Button(parent, text="+ Agregar proceso", command=self._agregar_proceso,
                  bg="#2C2C2A", fg="white", relief=tk.FLAT,
                  font=("Helvetica", 11), padx=10, pady=5,
                  cursor="hand2").pack(fill=tk.X, pady=(10, 0))

        # ── Lista de procesos ──
        self._lbl_seccion(parent, "Procesos en cola")

        frame_lista = tk.Frame(parent, bg="#F5F4F0")
        frame_lista.pack(fill=tk.BOTH, expand=True)

        self._listbox_frame = tk.Frame(frame_lista, bg="#F5F4F0")
        self._listbox_frame.pack(fill=tk.BOTH, expand=True)
        self._render_lista()

        tk.Button(parent, text="Eliminar seleccionado", command=self._eliminar_proceso,
                  bg="#F5F4F0", fg="#993C1D", relief=tk.FLAT,
                  font=("Helvetica", 10), cursor="hand2",
                  bd=1).pack(fill=tk.X, pady=(4, 0))

        # ── Quantum ──
        self._lbl_seccion(parent, "Quantum Round Robin")

        self._var_quantum = tk.IntVar(value=15)
        fq = tk.Frame(parent, bg="#F5F4F0")
        fq.pack(fill=tk.X)
        tk.Scale(fq, from_=5, to=50, orient=tk.HORIZONTAL,
                 variable=self._var_quantum, bg="#F5F4F0",
                 highlightthickness=0, troughcolor="#D3D1C7",
                 activebackground="#378ADD", label="ms",
                 font=("Helvetica", 9)).pack(fill=tk.X)
        tk.Label(parent, text="Rango real: 5ms – 50ms (Linux usa ~4ms a 100ms)",
                 bg="#F5F4F0", fg="#888780", font=("Helvetica", 8),
                 wraplength=250, justify=tk.LEFT).pack(anchor="w")

        # ── Velocidad ──
        self._lbl_seccion(parent, "Velocidad de animación")
        self._var_vel = tk.IntVar(value=180)
        tk.Scale(parent, from_=30, to=500, orient=tk.HORIZONTAL,
                 variable=self._var_vel, bg="#F5F4F0",
                 highlightthickness=0, troughcolor="#D3D1C7",
                 label="ms/paso (menor = más rápido)",
                 font=("Helvetica", 9),
                 command=lambda v: None).pack(fill=tk.X)

        # ── Botones de control ──
        self._lbl_seccion(parent, "Control")
        fbt = tk.Frame(parent, bg="#F5F4F0")
        fbt.pack(fill=tk.X, pady=(0, 8))

        self._btn_simular = tk.Button(fbt, text="▶  Simular", command=self._iniciar_sim,
                                      bg="#185FA5", fg="white", relief=tk.FLAT,
                                      font=("Helvetica", 11, "bold"), padx=8, pady=6,
                                      cursor="hand2")
        self._btn_simular.pack(fill=tk.X, pady=(0, 4))

        self._btn_pausa = tk.Button(fbt, text="⏸  Pausar", command=self._toggle_pausa,
                                    state=tk.DISABLED, bg="#F5F4F0", fg="#2C2C2A",
                                    relief=tk.FLAT, font=("Helvetica", 10),
                                    padx=8, pady=5, cursor="hand2", bd=1)
        self._btn_pausa.pack(fill=tk.X, pady=(0, 4))

        self._btn_paso = tk.Button(fbt, text="⏭  Paso a paso", command=self._un_paso,
                                   state=tk.DISABLED, bg="#F5F4F0", fg="#2C2C2A",
                                   relief=tk.FLAT, font=("Helvetica", 10),
                                   padx=8, pady=5, cursor="hand2", bd=1)
        self._btn_paso.pack(fill=tk.X, pady=(0, 4))

        tk.Button(fbt, text="↺  Reiniciar", command=self._reiniciar,
                  bg="#F5F4F0", fg="#2C2C2A", relief=tk.FLAT,
                  font=("Helvetica", 10), padx=8, pady=5,
                  cursor="hand2", bd=1).pack(fill=tk.X)

    def _build_right(self, parent):
        # ── Diagrama Gantt ──
        tk.Label(parent, text="DIAGRAMA DE GANTT — VISUALIZACIÓN POR PÍXELES",
                 bg="#F5F4F0", fg="#888780",
                 font=("Helvetica", 8, "bold")).pack(anchor="w")

        # Leyenda
        self._frame_leyenda = tk.Frame(parent, bg="#F5F4F0")
        self._frame_leyenda.pack(fill=tk.X, pady=(4, 6))

        # Canvas Gantt con scrollbar horizontal
        canvas_frame = tk.Frame(parent, bg="#FFFFFF",
                                highlightthickness=1,
                                highlightbackground="#D3D1C7",
                                relief=tk.FLAT)
        canvas_frame.pack(fill=tk.X)

        self._canvas = tk.Canvas(canvas_frame, height=self.ALTO_CANVAS,
                                 bg="#FFFFFF", highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                                 command=self._canvas.xview)
        self._canvas.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self._canvas.pack(fill=tk.X)

        # Info de timeline
        self._var_timeline = tk.StringVar(value="Presiona Simular para iniciar...")
        tk.Label(parent, textvariable=self._var_timeline,
                 bg="#F5F4F0", fg="#888780",
                 font=("Courier", 9), anchor="w").pack(fill=tk.X, pady=(4, 0))

        # ── Estadísticas ──
        self._lbl_seccion(parent, "Estadísticas de ejecución")
        self._frame_stats = tk.Frame(parent, bg="#F5F4F0")
        self._frame_stats.pack(fill=tk.X)

        # ── Log ──
        self._lbl_seccion(parent, "Log de eventos")
        log_frame = tk.Frame(parent, bg="#FFFFFF",
                             highlightthickness=1,
                             highlightbackground="#D3D1C7")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._log_text = tk.Text(log_frame, height=8, state=tk.DISABLED,
                                 bg="#FAFAF8", fg="#5F5E5A",
                                 font=("Courier", 9), relief=tk.FLAT,
                                 wrap=tk.WORD, padx=8, pady=6)
        log_scroll = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True)

    # ── Gestión de procesos ────────────────────

    def _agregar_proceso(self):
        try:
            t = self._var_tiempo.get()
        except tk.TclError:
            messagebox.showerror("Error", "El tiempo debe ser un número entero.")
            return
        if not (5 <= t <= 500):
            messagebox.showerror("Error", "Tiempo debe estar entre 5 y 500 ms.")
            return
        if len(self._procesos) >= 8:
            messagebox.showwarning("Límite", "Máximo 8 procesos por simulación.")
            return
        self._contador_proc += 1
        p = Proceso(f"P{self._contador_proc}", t, self._var_prio.get())
        self._procesos.append(p)
        self._render_lista()
        self._render_leyenda()
        prio_str = "Alta" if p.prioridad == 1 else "Baja"
        self._log(f"Agregado {p.nombre}: {t}ms, prioridad {prio_str}")

    def _eliminar_proceso(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        p = self._procesos[idx]
        self._procesos.pop(idx)
        self._render_lista()
        self._render_leyenda()
        self._log(f"Eliminado {p.nombre}")

    def _render_lista(self):
        for w in self._listbox_frame.winfo_children():
            w.destroy()

        frame = tk.Frame(self._listbox_frame, bg="#FFFFFF",
                         highlightthickness=1,
                         highlightbackground="#D3D1C7")
        frame.pack(fill=tk.BOTH, expand=True)

        self._listbox = tk.Listbox(frame, selectmode=tk.SINGLE,
                                   bg="#FFFFFF", fg="#2C2C2A",
                                   font=("Courier", 10),
                                   relief=tk.FLAT, height=7,
                                   selectbackground="#B5D4F4",
                                   selectforeground="#2C2C2A",
                                   activestyle="none")
        for p in self._procesos:
            prio_str = "Alta" if p.prioridad == 1 else "Baja "
            self._listbox.insert(tk.END, f"  {p.nombre}   {p.tiempo}ms   [{prio_str}]")

        scroll_lb = tk.Scrollbar(frame, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scroll_lb.set)
        scroll_lb.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(fill=tk.BOTH, expand=True)

    def _render_leyenda(self):
        for w in self._frame_leyenda.winfo_children():
            w.destroy()
        for p in self._procesos:
            item = tk.Frame(self._frame_leyenda, bg="#F5F4F0")
            item.pack(side=tk.LEFT, padx=(0, 12))
            tk.Canvas(item, width=12, height=12, bg=p.color,
                      highlightthickness=0).pack(side=tk.LEFT, padx=(0, 4))
            prio = "Alta" if p.prioridad == 1 else "Baja"
            tk.Label(item, text=f"{p.nombre} ({prio}, {p.tiempo}ms)",
                     bg="#F5F4F0", fg="#5F5E5A",
                     font=("Helvetica", 9)).pack(side=tk.LEFT)

    # ── Simulación ────────────────────────────

    def _iniciar_sim(self):
        if not self._procesos:
            messagebox.showwarning("Sin procesos", "Agrega al menos un proceso.")
            return
        if self._animando:
            return

        quantum = self._var_quantum.get()

        # Reset tiempos restantes
        for p in self._procesos:
            p.restante = p.tiempo

        self._pasos = construir_pasos(self._procesos, quantum)
        self._paso_actual  = 0
        self._pixel_offset = 0
        self._pausado      = False
        self._animando     = True

        # Calcular ancho total del canvas
        total_ms  = sum(s["duracion"] for s in self._pasos)
        ancho_px  = max(800, int(total_ms * self.PX_POR_MS) + 60)
        self._canvas.configure(scrollregion=(0, 0, ancho_px, self.ALTO_CANVAS))
        self._canvas.delete("all")

        # Fondo sutil
        self._canvas.create_rectangle(0, self.Y_BARRA, ancho_px,
                                       self.Y_BARRA + self.ALTO_BARRA,
                                       fill="#F1EFE8", outline="")

        self._btn_simular.configure(state=tk.DISABLED)
        self._btn_pausa.configure(state=tk.NORMAL)
        self._btn_paso.configure(state=tk.NORMAL)

        self._limpiar_stats()
        self._log(f"Iniciando: {len(self._procesos)} procesos, quantum {quantum}ms, "
                  f"total ~{total_ms}ms, {len(self._pasos)} ráfagas")

        self._animar()

    def _animar(self):
        if not self._animando:
            return
        if self._pausado:
            self.after(100, self._animar)
            return
        if self._paso_actual >= len(self._pasos):
            self._finalizar()
            return

        self._dibujar_paso()
        delay = self._var_vel.get()
        self.after(delay, self._animar)

    def _dibujar_paso(self):
        if self._paso_actual >= len(self._pasos):
            return
        s   = self._pasos[self._paso_actual]
        p   = s["proceso"]
        dur = s["duracion"]
        w   = max(2, int(dur * self.PX_POR_MS))
        x0  = self._pixel_offset
        y0  = self.Y_BARRA
        x1  = x0 + w
        y1  = y0 + self.ALTO_BARRA

        # Bloque de color
        self._canvas.create_rectangle(x0, y0, x1, y1,
                                       fill=p.color, outline="#FFFFFF", width=1)

        # Etiqueta del proceso
        if w > 20:
            self._canvas.create_text(x0 + w // 2, y0 + self.ALTO_BARRA // 2,
                                      text=p.nombre, fill="white",
                                      font=("Courier", 10, "bold"))

        # Tick de tiempo inicio
        t_ini = s["t_inicio"]
        if self._paso_actual % 3 == 0 or self._paso_actual == 0:
            self._canvas.create_text(x0 + 2, y0 - 8,
                                      text=f"{t_ini}ms", fill="#888780",
                                      font=("Courier", 8), anchor="w")
        # Línea tick
        self._canvas.create_line(x0, y0 - 4, x0, y0, fill="#D3D1C7", width=1)

        # Scroll automático para seguir la animación
        self._canvas.xview_moveto(max(0, (x1 - 400) / 
                                   max(1, self._canvas.winfo_width())))

        self._var_timeline.set(
            f"Ejecutando: {p.nombre}  —  {t_ini}ms → {s['t_fin']}ms  "
            f"(burst: {dur}ms, prioridad {'Alta' if p.prioridad==1 else 'Baja'})"
        )

        self._pixel_offset += w
        self._paso_actual  += 1

    def _un_paso(self):
        """Avanza un solo paso manualmente."""
        if self._paso_actual < len(self._pasos):
            self._dibujar_paso()
        if self._paso_actual >= len(self._pasos):
            self._finalizar()

    def _toggle_pausa(self):
        self._pausado = not self._pausado
        self._btn_pausa.configure(
            text="▶  Continuar" if self._pausado else "⏸  Pausar"
        )

    def _finalizar(self):
        self._animando = False
        self._pausado  = False
        self._btn_simular.configure(state=tk.NORMAL)
        self._btn_pausa.configure(state=tk.DISABLED, text="⏸  Pausar")
        self._btn_paso.configure(state=tk.DISABLED)

        # Marcar tiempo final
        if self._pasos:
            total_ms = self._pasos[-1]["t_fin"]
            self._canvas.create_text(self._pixel_offset + 4,
                                      self.Y_BARRA - 8,
                                      text=f"{total_ms}ms",
                                      fill="#888780",
                                      font=("Courier", 8), anchor="w")
        self._var_timeline.set(
            f"Completado — {len(self._pasos)} ráfagas, "
            f"tiempo total: {self._pasos[-1]['t_fin']}ms"
        )
        self._mostrar_stats()
        self._log(f"Simulación completada. "
                  f"Tiempo total: {self._pasos[-1]['t_fin']}ms, "
                  f"{len(self._pasos)} ráfagas.")
        for p in self._procesos:
            rafagas = sum(1 for s in self._pasos if s["proceso"] is p)
            self._log(f"  {p.nombre}: {p.tiempo}ms ejecutados en {rafagas} ráfaga(s)")

    def _reiniciar(self):
        self._animando = False
        self._pausado  = False
        self._pasos    = []
        self._paso_actual  = 0
        self._pixel_offset = 0
        self._procesos = []
        self._contador_proc = 0
        Proceso.reset_colores()

        self._canvas.delete("all")
        self._render_lista()
        self._render_leyenda()
        self._limpiar_stats()
        self._var_timeline.set("Presiona Simular para iniciar...")
        self._btn_simular.configure(state=tk.NORMAL)
        self._btn_pausa.configure(state=tk.DISABLED, text="⏸  Pausar")
        self._btn_paso.configure(state=tk.DISABLED)
        self._log("─── Reiniciado ───")

    # ── Estadísticas ──────────────────────────

    def _limpiar_stats(self):
        for w in self._frame_stats.winfo_children():
            w.destroy()

    def _mostrar_stats(self):
        self._limpiar_stats()
        total_ms = self._pasos[-1]["t_fin"] if self._pasos else 0
        quantum  = self._var_quantum.get()
        throughput = f"{len(self._procesos) / (total_ms / 1000):.2f}" if total_ms else "—"

        datos = [
            ("Tiempo total CPU",  f"{total_ms} ms"),
            ("Ráfagas ejecutadas", str(len(self._pasos))),
            ("Quantum usado",     f"{quantum} ms"),
            ("Procesos/seg",      throughput),
        ]
        high_ms = sum(p.tiempo for p in self._procesos if p.prioridad == 1)
        low_ms  = sum(p.tiempo for p in self._procesos if p.prioridad == 2)
        if high_ms: datos.append(("CPU prioridad Alta", f"{high_ms} ms"))
        if low_ms:  datos.append(("CPU prioridad Baja", f"{low_ms} ms"))

        for i, (lbl, val) in enumerate(datos):
            card = tk.Frame(self._frame_stats, bg="#F1EFE8",
                            padx=10, pady=8)
            card.grid(row=0, column=i, padx=(0, 8), sticky="nsew")
            self._frame_stats.columnconfigure(i, weight=1)
            tk.Label(card, text=val, bg="#F1EFE8", fg="#2C2C2A",
                     font=("Courier", 14, "bold")).pack(anchor="w")
            tk.Label(card, text=lbl, bg="#F1EFE8", fg="#888780",
                     font=("Helvetica", 8)).pack(anchor="w")

    # ── Log ───────────────────────────────────

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert("1.0", f"[{ts}] {msg}\n")
        self._log_text.configure(state=tk.DISABLED)

    # ── Demo inicial ──────────────────────────

    def _cargar_demo(self):
        demos = [
            (90, 1),   # P1 — Alta, 90ms
            (60, 2),   # P2 — Baja, 60ms
            (45, 1),   # P3 — Alta, 45ms
        ]
        for t, pr in demos:
            self._contador_proc += 1
            p = Proceso(f"P{self._contador_proc}", t, pr)
            self._procesos.append(p)
        self._render_lista()
        self._render_leyenda()
        self._log("Demo cargado: P1 (Alta, 90ms), P2 (Baja, 60ms), P3 (Alta, 45ms)")
        self._log("Ajusta los procesos y presiona Simular.")


# ─────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()