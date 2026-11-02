# ==============================================================
# Programa desarrollado por Manuel Ovalle
# Panel de control GUI y teleoperacion de robots Pololu 3Pi+
# ==============================================================
# Este script implementa una interfaz grafica en Tkinter para gestionar
# la conexion y el control gestual de uno o varios robots Pololu 3Pi+
# mediante el sensor Leap Motion. Incluye modos de operacion individual,
# enjambre, dos jugadores y rutinas de movimiento predefinidas.
# ==============================================================

import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import time
import os
import leap
import concurrent.futures
from Pololu3Pi import Pololu3Pi

# Ruta del SDK de Leap Motion
os.environ["LEAPSDK_INSTALL_LOCATION"] = "D:\\LeapSDK"

# Parametros de velocidad y zonas muertas
MAX_SPEED = 250      
DEADZONE_PITCH = 15  
DEADZONE_ROLL = 50   

class PololuController(leap.Listener):
    def __init__(self, bots):
        super().__init__()
        self.bots = bots  
        self.last_update = time.time()
        self.last_dance_time = 0
        self.is_dancing = False  
        self.mode = "PARO"     
        self.dance_target = "ENJAMBRE" 
        
        # Asignacion de indices de robots
        self.selected_robot_idx = 0              
        self.p1_idx = 0                          
        self.p2_idx = 1 if len(bots) > 1 else 0  
        
        # Pool de hilos para envios concurrentes
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(bots) if bots else 1)

    def enviar_a_todos(self, v_izq, v_der):
        # Envio simultaneo a todas las unidades conectadas
        for bot in self.bots:
            self.executor.submit(bot.set_wheel_velocities, v_izq, v_der)

    def controlar_robot(self, hand, bot):
        # Parada de emergencia individual
        if hand.grab_strength > 0.8:
            self.executor.submit(bot.set_wheel_velocities, 0, 0)
            return

        # Calculo proporcional de velocidades
        pitch_raw = hand.palm.direction.y  
        roll_raw = hand.palm.normal.x      

        base_speed = -pitch_raw * 300
        turn_speed = -roll_raw * 100  

        # Filtro de zonas muertas
        if abs(base_speed) < DEADZONE_PITCH: 
            base_speed = 0

        if abs(turn_speed) < DEADZONE_ROLL: 
            turn_speed = 0

        # Mezcla diferencial y saturacion
        v_left = base_speed + turn_speed
        v_right = base_speed - turn_speed

        v_left = max(-MAX_SPEED, min(MAX_SPEED, v_left))
        v_right = max(-MAX_SPEED, min(MAX_SPEED, v_right))

        self.executor.submit(bot.set_wheel_velocities, int(v_left), int(v_right))

    def ejecutar_baile(self):
        if self.is_dancing:
            return
            
        self.is_dancing = True
        print(f"ACTIVANDO BAILE ({self.dance_target})")
        
        # Secuencia de movimientos coreografiados
        pasos = [
            (100, -100, 0.4), (-100, 100, 0.4), (125, 125, 0.4),
            (-125, -125, 0.4), (175, -175, 0.8), (-175, 175, 0.8),
            (75, -75, 0.2), (-75, 75, 0.2), (75, -75, 0.2),
            (-75, 75, 0.2), (200, -200, 1.2)
        ]
        
        for v_izq, v_der, duracion in pasos:
            if self.dance_target == "ENJAMBRE":
                self.enviar_a_todos(v_izq, v_der)
            else:
                if len(self.bots) > self.selected_robot_idx:
                    self.executor.submit(self.bots[self.selected_robot_idx].set_wheel_velocities, v_izq, v_der)
            time.sleep(duracion)
            
        # Detencion al concluir secuencia
        if self.dance_target == "ENJAMBRE":
            self.enviar_a_todos(0, 0)
        elif len(self.bots) > self.selected_robot_idx:
            self.executor.submit(self.bots[self.selected_robot_idx].set_wheel_velocities, 0, 0)
            
        self.is_dancing = False
        self.last_dance_time = time.time()
        
    def on_tracking_event(self, event):
        if self.is_dancing or self.mode == "PARO":
            return
            
        # Limitacion de tasa de refresco a ~33 Hz
        if time.time() - self.last_update < 0.03:
            return
        self.last_update = time.time()

        # Control independiente para dos manos
        if self.mode == "DOS_JUGADORES":
            if not event.hands:
                if len(self.bots) > self.p1_idx:
                    self.executor.submit(self.bots[self.p1_idx].set_wheel_velocities, 0, 0)
                if len(self.bots) > self.p2_idx:
                    self.executor.submit(self.bots[self.p2_idx].set_wheel_velocities, 0, 0)
                return

            for hand in event.hands:
                if hand.type == leap.HandType.Left:
                    if len(self.bots) > self.p1_idx:
                        self.controlar_robot(hand, self.bots[self.p1_idx])
                elif hand.type == leap.HandType.Right:
                    if len(self.bots) > self.p2_idx:
                        self.controlar_robot(hand, self.bots[self.p2_idx])
            return

        # Detener motores si no se detecta mano
        if not event.hands:
            self.enviar_a_todos(0, 0)
            return

        hand = event.hands[0]

        # Activacion de rutina con 1 dedo levantado
        if self.mode == "BAILE":
            self.enviar_a_todos(0, 0)
            finger_states = [1 if f.is_extended else 0 for f in hand.digits]
            if sum(finger_states) == 1 and (time.time() - self.last_dance_time > 5):
                threading.Thread(target=self.ejecutar_baile, daemon=True).start()
            return

        # Control de un solo robot seleccionado
        elif self.mode == "NORMAL":
            if len(self.bots) > self.selected_robot_idx:
                self.controlar_robot(hand, self.bots[self.selected_robot_idx])

        # Control sincronizado de todos los robots
        elif self.mode == "ENJAMBRE":
            pitch_raw = hand.palm.direction.y  
            roll_raw = hand.palm.normal.x      
            base_speed = -pitch_raw * 300
            turn_speed = -roll_raw * 100  
            if abs(base_speed) < DEADZONE_PITCH: base_speed = 0
            if abs(turn_speed) < DEADZONE_ROLL: turn_speed = 0
            v_left = max(-MAX_SPEED, min(MAX_SPEED, base_speed + turn_speed))
            v_right = max(-MAX_SPEED, min(MAX_SPEED, base_speed - turn_speed))
            
            if hand.grab_strength > 0.8:
                self.enviar_a_todos(0, 0)
            else:
                self.enviar_a_todos(int(v_left), int(v_right))


class AppGUI:
    def __init__(self, root, controller, bots, ips):
        self.root = root
        self.controller = controller
        self.bots = bots
        self.ips = ips
        
        self.root.title("Panel de Control - Talleres de Actividades")
        self.root.geometry("400x600")
        self.root.configure(bg="#2b2b2b")
        
        self.style = {"bg": "#2b2b2b", "fg": "white", "font": ("Segoe UI", 12)}
        self.btn_style = {"font": ("Segoe UI", 11, "bold"), "width": 20, "pady": 4, "bg": "#4a4a4a", "fg": "white"}
        
        self.frame_menu = tk.Frame(self.root, bg="#2b2b2b")
        self.frame_modos = tk.Frame(self.root, bg="#2b2b2b")
        
        self.crear_menu_principal()
        self.crear_menu_modos()
        self.mostrar_frame(self.frame_menu)
        
    def crear_menu_principal(self):
        tk.Label(self.frame_menu, text="Panel Pololu 3Pi", font=("Segoe UI", 20, "bold"), bg="#2b2b2b", fg="white").pack(pady=25)
        tk.Label(self.frame_menu, text=f"Robots conectados: {len(self.bots)}", **self.style).pack(pady=5)
        
        btn_ingresar = tk.Button(self.frame_menu, text="Ingresar al Panel", **self.btn_style, 
                                 command=lambda: self.mostrar_frame(self.frame_modos))
        btn_ingresar.pack(pady=30)
                  
    def crear_menu_modos(self):
        tk.Label(self.frame_modos, text="Selección de Modo", font=("Segoe UI", 16, "bold"), bg="#2b2b2b", fg="white").pack(pady=(5,0))
        
        self.lbl_estado = tk.Label(self.frame_modos, text="ESTADO: PARO", font=("Segoe UI", 12, "bold"), bg="#2b2b2b", fg="#ff4444")
        self.lbl_estado.pack(pady=2)
        
        # Selector de robot activo para modo individual
        tk.Label(self.frame_modos, text="Robot activo (Normal/Baile Ind.):", font=("Segoe UI", 9), bg="#2b2b2b", fg="#aaaaaa").pack(pady=(5, 0))
        self.opciones_robots = [f"Robot {i+1} ({ip.split('.')[-1]})" for i, ip in enumerate(self.ips)]
        self.robot_var = tk.StringVar(value=self.opciones_robots[0])
        self.robot_var.trace_add("write", self.al_cambiar_selector_normal)
        
        self.selector_robot = tk.OptionMenu(self.frame_modos, self.robot_var, *self.opciones_robots)
        self.selector_robot.config(font=("Segoe UI", 9), bg="#333333", fg="white", highlightthickness=0, width=18)
        self.selector_robot.pack(pady=2)

        # Botones de seleccion de modo
        self.btn_normal = tk.Button(self.frame_modos, text="Modo Normal", **self.btn_style, command=self.activar_normal)
        self.btn_normal.pack(pady=3)

        self.btn_enjambre = tk.Button(self.frame_modos, text="Modo Enjambre", **self.btn_style, command=self.activar_enjambre)
        self.btn_enjambre.pack(pady=3)
        
        self.btn_2j = tk.Button(self.frame_modos, text="Dos Jugadores", **self.btn_style, command=self.abrir_ventana_2_jugadores)
        if len(self.bots) < 2:
            self.btn_2j.config(state="disabled")
        self.btn_2j.pack(pady=3)
        
        self.btn_baile_ind = tk.Button(self.frame_modos, text="Baile (Individual)", font=("Segoe UI", 11, "bold"), width=20, bg="#ff00ff", fg="white", command=lambda: self.activar_baile("INDIVIDUAL"))
        self.btn_baile_ind.pack(pady=3)

        self.btn_baile_enj = tk.Button(self.frame_modos, text="Baile (Enjambre)", font=("Segoe UI", 11, "bold"), width=20, bg="#8a2be2", fg="white", command=lambda: self.activar_baile("ENJAMBRE"))
        self.btn_baile_enj.pack(pady=3)
        
        self.btn_paro = tk.Button(self.frame_modos, text="Paro Total", font=("Segoe UI", 11, "bold"), width=20, pady=6, bg="#8b0000", fg="white", command=self.activar_paro)
        self.btn_paro.pack(pady=8)
        
        tk.Button(self.frame_modos, text="Volver", font=("Segoe UI", 10), bg="#333333", fg="white", width=15, pady=2,
                  command=lambda: self.mostrar_frame(self.frame_menu)).pack(pady=5)
                  
    def al_cambiar_selector_normal(self, *args):
        seleccion = self.robot_var.get()
        self.controller.selected_robot_idx = self.opciones_robots.index(seleccion)
        if self.controller.mode == "NORMAL":
            self.lbl_estado.config(text=f"ESTADO: CONTROL {seleccion}", fg="#00ff00")

    def mostrar_frame(self, frame):
        self.frame_menu.pack_forget()
        self.frame_modos.pack_forget()
        frame.pack(expand=True, fill="both")
        
    def activar_normal(self):
        self.controller.mode = "NORMAL"
        self.controller.enviar_a_todos(0, 0)
        self.lbl_estado.config(text=f"ESTADO: CONTROL {self.robot_var.get()}", fg="#00ff00")
        
    def activar_enjambre(self):
        self.controller.mode = "ENJAMBRE"
        self.lbl_estado.config(text="ESTADO: ENJAMBRE ACTIVO", fg="#00bfff") 

    def activar_baile(self, target):
        self.controller.mode = "BAILE"
        self.controller.dance_target = target
        self.controller.enviar_a_todos(0, 0)
        self.lbl_estado.config(text=f"ESTADO: BAILE {target} (Esperando...)", fg="#ff00ff") 

    def activar_paro(self):
        self.controller.mode = "PARO"
        self.controller.enviar_a_todos(0, 0)
        self.lbl_estado.config(text="ESTADO: PARO TOTAL", fg="#ff4444") 

    def abrir_ventana_2_jugadores(self):
        # Configuracion de asignacion de robots por mano
        ventana_2j = tk.Toplevel(self.root)
        ventana_2j.title("Configurar 2 Jugadores")
        ventana_2j.geometry("300x250")
        ventana_2j.configure(bg="#2b2b2b")
        ventana_2j.grab_set() 
        
        tk.Label(ventana_2j, text="Asignar Robots", font=("Segoe UI", 12, "bold"), bg="#2b2b2b", fg="white").pack(pady=10)
        
        tk.Label(ventana_2j, text="Mano Izquierda (Jugador 1):", bg="#2b2b2b", fg="white").pack()
        var_p1 = tk.StringVar(value=self.opciones_robots[0])
        menu_p1 = tk.OptionMenu(ventana_2j, var_p1, *self.opciones_robots)
        menu_p1.config(bg="#4a4a4a", fg="white", highlightthickness=0)
        menu_p1.pack(pady=2)
        
        tk.Label(ventana_2j, text="Mano Derecha (Jugador 2):", bg="#2b2b2b", fg="white").pack(pady=(5,0))
        var_p2 = tk.StringVar(value=self.opciones_robots[1] if len(self.opciones_robots) > 1 else self.opciones_robots[0])
        menu_p2 = tk.OptionMenu(ventana_2j, var_p2, *self.opciones_robots)
        menu_p2.config(bg="#4a4a4a", fg="white", highlightthickness=0)
        menu_p2.pack(pady=2)
        
        def iniciar_2j():
            self.controller.p1_idx = self.opciones_robots.index(var_p1.get())
            self.controller.p2_idx = self.opciones_robots.index(var_p2.get())
            self.controller.mode = "DOS_JUGADORES"
            self.controller.enviar_a_todos(0, 0)
            self.lbl_estado.config(text="ESTADO: DOS JUGADORES ACTIVOS", fg="#ffa500")
            ventana_2j.destroy()
            
        tk.Button(ventana_2j, text="Iniciar Juego", bg="#006400", fg="white", font=("Segoe UI", 10, "bold"), width=15, command=iniciar_2j).pack(pady=15)


def main():
    root = tk.Tk()
    root.withdraw()

    # Dialogo de seleccion de cantidad de robots
    num_bots = simpledialog.askinteger("Configuración", 
                                       "¿Cuántos Pololus vas a usar? (1 a 5)", 
                                       minvalue=1, maxvalue=5, parent=root)
    if not num_bots:
        root.destroy()
        return

    # Ingreso de direcciones IP
    robot_ips = []
    for i in range(num_bots):
        xx = simpledialog.askstring("Configuración de IPs", 
                                    f"Robot {i+1} de {num_bots}\n\nLa IP base es 192.168.50.1XX\n\nIngresa ÚNICAMENTE los últimos dígitos (ej. 14):", 
                                    parent=root)
        if xx is None or xx.strip() == "":
            root.destroy()
            return
        
        robot_ips.append(f"192.168.50.1{xx.strip()}")

    print("\n========================================")
    print("Iniciando Enlace con los Robots")
    print("========================================")
    
    # Establecimiento de conexion con cada robot
    bots_conectados = []
    ips_conectadas = []
    
    for ip in robot_ips:
        print(f"Intentando conectar al Pololu en {ip}...")
        bot = Pololu3Pi()
        try:
            bot.connect(ip=ip)
            bots_conectados.append(bot)
            ips_conectadas.append(ip)
            print(f"Pololu en {ip} conectado exitosamente.")
        except Exception as e:
            messagebox.showwarning("Error de conexión", f"No se pudo conectar con el robot en {ip}.")
            print(f"Error al conectar con {ip}: {e}")

    if not bots_conectados:
        messagebox.showerror("Error crítico", "No se pudo conectar a ningún robot.")
        root.destroy()
        return

    # Inicializacion de Leap Motion y subprocesos
    controller = PololuController(bots_conectados)
    connection = leap.Connection()
    connection.add_listener(controller)
    
    def correr_leap():
        with connection.open():
            while True:
                time.sleep(1)

    hilo_leap = threading.Thread(target=correr_leap, daemon=True)
    hilo_leap.start()
    
    root.deiconify()
    app = AppGUI(root, controller, bots_conectados, ips_conectadas)
    
    # Manejo de cierre de ventana y parada segura
    def al_cerrar():
        print("Apagando motores y cerrando el programa...")
        for b in bots_conectados:
            try:
                b.force_stop()
                b.disconnect()
            except:
                pass
        controller.executor.shutdown(wait=False)
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", al_cerrar)
    root.mainloop()

if __name__ == "__main__":
    main()
