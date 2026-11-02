# ==============================================================
# Programa desarrollado por Manuel Ovalle
# Sistema de navegacion y control de vuelo para Crazyflie 2.1
# ==============================================================
# Este script implementa una interfaz grafica en Tkinter para operar
# un cuadricoptero Crazyflie 2.1 mediante comandos gestuales recibidos
# por UDP desde un sensor Leap Motion o mediante teclado. Incluye
# estimacion por filtro de Kalman, control de altura y rutinas de seguridad.
# ==============================================================

import os
import socket
import time
import threading
import tkinter as tk
import warnings

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Parametros de comunicacion y limites de vuelo
URI = 'radio://0/80/2M'
UDP_IP = "127.0.0.1"
UDP_PORT = 50005

VEL_XY = 0.22
TASA_ACELERACION = 0.050
TASA_FRENADO = 0.085

INCREMENTO_Z = 0.012
DECREMENTO_Z = 0.018

ALTURA_DESPEGUE = 0.35
ALTURA_MAXIMA = 0.90
ALTURA_MINIMA = 0.18
TECHO_EMERGENCIA = 1.10

DT_LOOP = 0.04
TIMEOUT_UDP = 0.12

class AterrizajeForzoso(Exception): pass
class AterrizajeControlado(Exception): pass


class InterfazAvanzadaDron:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Vuelo - Tesis")
        self.root.geometry("450x550")
        self.root.configure(bg="#2b2b2b")

        self.volando = False
        self.freno_emergencia = False
        self.modo_vuelo = None
        self.altura_dron = 0.0

        # Mapeo de teclas para modo manual
        self.teclas_presionadas = {'w': False, 'a': False, 's': False, 'd': False}
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.bind('<KeyRelease>', self.on_key_release)

        # Elementos de interfaz grafica
        tk.Label(root, text="SISTEMA DE NAVEGACIÓN", font=("Arial", 14, "bold"), bg="#2b2b2b", fg="white").pack(pady=(10, 5))

        self.lbl_estado = tk.Label(root, text="Estado: EN TIERRA", font=("Arial", 12), bg="#2b2b2b", fg="#00ff00")
        self.lbl_estado.pack(pady=(0, 5))

        # Panel de telemetria
        frame_telemetria = tk.Frame(root, bg="#1e1e1e", bd=2, relief="groove")
        frame_telemetria.pack(fill="x", padx=30, pady=10)

        self.lbl_bateria = tk.Label(frame_telemetria, text="Batería: --%", font=("Arial", 11, "bold"), bg="#1e1e1e", fg="#00ff00")
        self.lbl_bateria.grid(row=0, column=0, columnspan=2, pady=(10, 5))

        self.lbl_pitch = tk.Label(frame_telemetria, text="Pitch (Adelante/Atrás): CENTRO", font=("Arial", 10), bg="#1e1e1e", fg="#aaaaaa")
        self.lbl_pitch.grid(row=1, column=0, sticky="w", padx=15, pady=2)

        self.lbl_roll = tk.Label(frame_telemetria, text="Roll (Izquierda/Derecha): CENTRO", font=("Arial", 10), bg="#1e1e1e", fg="#aaaaaa")
        self.lbl_roll.grid(row=2, column=0, sticky="w", padx=15, pady=2)

        self.lbl_altura = tk.Label(frame_telemetria, text="Nivel de Vuelo: MEDIO", font=("Arial", 10), bg="#1e1e1e", fg="#aaaaaa")
        self.lbl_altura.grid(row=3, column=0, sticky="w", padx=15, pady=2)

        self.lbl_puño = tk.Label(frame_telemetria, text="Mano: ABIERTA", font=("Arial", 10, "bold"), bg="#1e1e1e", fg="#aaaaaa")
        self.lbl_puño.grid(row=4, column=0, sticky="w", padx=15, pady=(2, 10))

        # Controles de inicio de modos de vuelo
        self.btn_modo_z = tk.Button(root, text="VUELO SOLO EJE Z", bg="#2196F3", fg="white",
                                    font=("Arial", 12, "bold"), command=self.iniciar_z)
        self.btn_modo_z.pack(fill="x", padx=40, pady=4)

        self.btn_modo_libre = tk.Button(root, text="VUELO MODO LIBRE (X, Y, Z)", bg="#9C27B0", fg="white",
                                        font=("Arial", 12, "bold"), command=self.iniciar_libre)
        self.btn_modo_libre.pack(fill="x", padx=40, pady=4)

        self.btn_modo_teclado = tk.Button(root, text="MODO PRUEBAS (TECLADO)", bg="#FF9800", fg="white",
                                          font=("Arial", 12, "bold"), command=self.iniciar_teclado)
        self.btn_modo_teclado.pack(fill="x", padx=40, pady=4)

        self.btn_stop = tk.Button(root, text="PARO DE EMERGENCIA [ESPACIO]", bg="#F44336", fg="white",
                                  font=("Arial", 14, "bold"), command=self.detener_vuelo, state="disabled")
        self.btn_stop.pack(fill="x", padx=40, pady=15)

    def on_key_press(self, event):
        tecla = event.keysym.lower()
        if tecla in self.teclas_presionadas:
            self.teclas_presionadas[tecla] = True
        elif event.keysym == "space" and self.volando:
            self.detener_vuelo()

    def on_key_release(self, event):
        tecla = event.keysym.lower()
        if tecla in self.teclas_presionadas:
            self.teclas_presionadas[tecla] = False

    def iniciar_z(self):
        self.modo_vuelo = 'Z_ONLY'
        self.lbl_estado.config(text="Estado: VOLANDO (Solo Altura)", fg="#2196F3")
        self.preparar_interfaz_vuelo()

    def iniciar_libre(self):
        self.modo_vuelo = 'LIBRE'
        self.lbl_estado.config(text="Estado: VOLANDO (Modo Libre)", fg="#9C27B0")
        self.preparar_interfaz_vuelo()

    def iniciar_teclado(self):
        self.modo_vuelo = 'TECLADO'
        self.lbl_estado.config(text="Estado: VOLANDO (Teclado)", fg="#FF9800")
        self.preparar_interfaz_vuelo()

    def preparar_interfaz_vuelo(self):
        self.btn_modo_z.config(state="disabled")
        self.btn_modo_libre.config(state="disabled")
        self.btn_modo_teclado.config(state="disabled")
        self.btn_stop.config(state="normal")

        self.root.focus_set()
        self.volando = True
        self.freno_emergencia = False
        threading.Thread(target=self.rutina_vuelo, daemon=True).start()

    def detener_vuelo(self):
        self.freno_emergencia = True
        self.lbl_estado.config(text="Estado: EMERGENCIA ACTIVADA", fg="#F44336")
        self.btn_stop.config(state="disabled")

    def _actualizar_altura(self, timestamp, data, logconf):
        self.altura_dron = data['stateEstimate.z']

    def _actualizar_bateria(self, timestamp, data, logconf):
        vbat = data['pm.vbat']
        porcentaje = max(0, min(100, int((vbat - 2.8) / (4.2 - 2.8) * 100)))
        color = "#00ff00" if porcentaje > 30 else ("#ffa500" if porcentaje > 15 else "#ff4444")
        self.root.after(0, self.lbl_bateria.config, {'text': f"Batería: {porcentaje}% ({vbat:.2f}V)", 'fg': color})

    def _actualizar_telemetria_ui(self, pitch, roll, altura, puño):
        alt_txt = "ALTO" if altura == "arriba" else "BAJO" if altura == "abajo" else "MEDIO"
        self.lbl_pitch.config(text=f"Pitch (Adelante/Atrás): {pitch.upper()}", fg="white" if pitch != "centro" else "#aaaaaa")
        self.lbl_roll.config(text=f"Roll (Izquierda/Derecha): {roll.upper()}", fg="white" if roll != "centro" else "#aaaaaa")
        self.lbl_altura.config(text=f"Nivel de Vuelo: {alt_txt}", fg="white" if alt_txt != "MEDIO" else "#aaaaaa")

        if puño:
            self.lbl_puño.config(text="Mano: CERRADA (Aterrizaje)", fg="#F44336")
        else:
            self.lbl_puño.config(text="Mano: ABIERTA", fg="#aaaaaa")

    def purgar_socket_udp(self, sock):
        sock.setblocking(False)
        while True:
            try:
                sock.recvfrom(1024)
            except BlockingIOError:
                break

    def reiniciar_estimador_kalman(self, scf, tiempo_espera=1.6):
        # Reiniciar estimacion de estados del dron en reposo
        try:
            scf.cf.param.set_value('kalman.resetEstimation', '1')
            time.sleep(0.1)
            scf.cf.param.set_value('kalman.resetEstimation', '0')
            time.sleep(tiempo_espera)
        except KeyError:
            raise RuntimeError("Perdida de conexion de radio al calibrar Kalman.")

    def _suavizar_inercia(self, actual, objetivo):
        # Transicion suave de consignas de velocidad horizontal
        if (actual > 0.03 and objetivo < -0.03) or (actual < -0.03 and objetivo > 0.03):
            return 0.0

        tasa = TASA_FRENADO if objetivo == 0.0 else TASA_ACELERACION

        if actual < objetivo:
            nuevo = min(actual + tasa, objetivo)
        elif actual > objetivo:
            nuevo = max(actual - tasa, objetivo)
        else:
            nuevo = actual

        if abs(nuevo) < 0.01 and objetivo == 0.0:
            return 0.0

        return nuevo

    def _despegue_seguro_anti_cohete(self, scf):
        # Validacion previa de lectura de altura en superficie
        if abs(self.altura_dron) > 0.06:
            scf.cf.commander.send_stop_setpoint()
            raise RuntimeError(f"Despegue cancelado: lectura en suelo anomala ({self.altura_dron:.2f}m).")

        pasos_rampa = 16
        altura_inicial = 0.12

        # Rampa ascendente controlada
        for i in range(1, pasos_rampa + 1):
            if self.freno_emergencia or not self.volando:
                scf.cf.commander.send_stop_setpoint()
                raise AterrizajeForzoso()

            # Corte por aceleracion vertical excesiva
            if self.altura_dron > 0.65 or self.altura_dron < -0.08:
                scf.cf.commander.send_stop_setpoint()
                raise RuntimeError(f"Corte por anomalia en despegue ({self.altura_dron:.2f}m).")

            z_cmd = altura_inicial + (ALTURA_DESPEGUE - altura_inicial) * (i / pasos_rampa)
            scf.cf.commander.send_hover_setpoint(0.0, 0.0, 0.0, z_cmd)
            time.sleep(0.05)

        # Verificacion de estabilidad en estacionario
        for _ in range(10):
            if self.freno_emergencia or not self.volando:
                scf.cf.commander.send_stop_setpoint()
                raise AterrizajeForzoso()

            if self.altura_dron > 0.70 or self.altura_dron < 0.02:
                scf.cf.commander.send_stop_setpoint()
                raise RuntimeError(f"Fallo de lectura en sensor de distancia ({self.altura_dron:.2f}m).")

            scf.cf.commander.send_hover_setpoint(0.0, 0.0, 0.0, ALTURA_DESPEGUE)
            time.sleep(0.05)

    def rutina_vuelo(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))

        os.makedirs('./cache', exist_ok=True)
        cf_instancia = Crazyflie(rw_cache='./cache')

        try:
            with SyncCrazyflie(URI, cf=cf_instancia) as scf:
                # Suscripcion a variables de telemetria
                log_alt = LogConfig(name='Height', period_in_ms=40)
                log_alt.add_variable('stateEstimate.z', 'float')
                scf.cf.log.add_config(log_alt)
                log_alt.data_received_cb.add_callback(self._actualizar_altura)
                log_alt.start()

                log_bat = LogConfig(name='Battery', period_in_ms=1000)
                log_bat.add_variable('pm.vbat', 'float')
                scf.cf.log.add_config(log_bat)
                log_bat.data_received_cb.add_callback(self._actualizar_bateria)
                log_bat.start()

                # Comprobacion de presencia de modulo Flow Deck
                try:
                    if str(scf.cf.param.get_value('deck.bcFlow2')) == '0':
                        raise RuntimeError("Flow Deck v2 no detectado.")
                except KeyError:
                    pass

                self.purgar_socket_udp(sock)

                # Espera de recepcion de paquetes gestuales
                if self.modo_vuelo != 'TECLADO':
                    mano_detectada = False
                    while self.volando and not mano_detectada and not self.freno_emergencia:
                        if not scf.is_link_open():
                            raise RuntimeError("Enlace de radio perdido.")
                        try:
                            data, addr = sock.recvfrom(1024)
                            if data:
                                mano_detectada = True
                        except BlockingIOError:
                            pass
                        time.sleep(0.05)

                if self.freno_emergencia or not self.volando:
                    log_alt.stop()
                    log_bat.stop()
                    return

                # Inicializacion de estimador y despegue
                self.reiniciar_estimador_kalman(scf, tiempo_espera=1.5)
                self._despegue_seguro_anti_cohete(scf)
                self.purgar_socket_udp(sock)

                altura_objetivo = ALTURA_DESPEGUE
                vx_actual, vy_actual = 0.0, 0.0

                ultimo_msg_valido = None
                tiempo_ultimo_msg = time.time()

                # Bucle principal de navegacion
                while self.volando:
                    if self.freno_emergencia:
                        scf.cf.commander.send_stop_setpoint()
                        self.volando = False
                        raise AterrizajeForzoso()

                    if not scf.is_link_open():
                        self.volando = False
                        break

                    # Proteccion contra superacion de altura maxima
                    if self.altura_dron > TECHO_EMERGENCIA:
                        scf.cf.commander.send_stop_setpoint()
                        self.volando = False
                        raise RuntimeError(f"Altura de seguridad excedida ({self.altura_dron:.2f}m).")

                    # Extraccion del mensaje mas reciente del buffer
                    msg_reciente = None
                    puño_detectado = False

                    try:
                        while True:
                            data, addr = sock.recvfrom(1024)
                            msg = data.decode('utf-8').lower()
                            if msg.count("cerrado") >= 4:
                                puño_detectado = True
                            msg_reciente = msg
                    except BlockingIOError:
                        pass

                    ahora = time.time()
                    if msg_reciente is not None:
                        ultimo_msg_valido = msg_reciente
                        tiempo_ultimo_msg = ahora

                    msg_activo = ultimo_msg_valido if (ahora - tiempo_ultimo_msg) <= TIMEOUT_UDP else None

                    # Actualizacion de estado en interfaz
                    if msg_reciente and '|' in msg_reciente:
                        partes = msg_reciente.split('|')
                        if len(partes) >= 4:
                            r_val = partes[1].split(':')[1]
                            p_val = partes[2].split(':')[1]
                            a_val = partes[3].split(':')[1]
                            self.root.after(0, self._actualizar_telemetria_ui, p_val, r_val, a_val, puño_detectado)

                    # Secuencia de aterrizaje al detectar puno cerrado
                    if puño_detectado:
                        for _ in range(10):
                            scf.cf.commander.send_hover_setpoint(0.0, 0.0, 0.0, 0.08)
                            time.sleep(0.05)
                        scf.cf.commander.send_stop_setpoint()
                        self.volando = False
                        raise AterrizajeControlado()

                    # Control incremental de consigna de altura
                    if msg_reciente:
                        if "altura:arriba" in msg_reciente:
                            altura_objetivo = min(altura_objetivo + INCREMENTO_Z, ALTURA_MAXIMA)
                        elif "altura:abajo" in msg_reciente:
                            altura_objetivo = max(altura_objetivo - DECREMENTO_Z, ALTURA_MINIMA)

                    vx_target, vy_target = 0.0, 0.0

                    # Evaluacion de velocidades segun modo activo
                    if self.modo_vuelo == 'TECLADO':
                        if self.teclas_presionadas['w']: vx_target = VEL_XY
                        elif self.teclas_presionadas['s']: vx_target = -VEL_XY
                        if self.teclas_presionadas['a']: vy_target = VEL_XY
                        elif self.teclas_presionadas['d']: vy_target = -VEL_XY

                    elif msg_activo and self.modo_vuelo == 'LIBRE':
                        if "pitch:adelante" in msg_activo: vx_target = VEL_XY
                        elif "pitch:atras" in msg_activo: vx_target = -VEL_XY
                        if "roll:izquierda" in msg_activo: vy_target = VEL_XY
                        elif "roll:derecha" in msg_activo: vy_target = -VEL_XY

                    if self.modo_vuelo == 'Z_ONLY':
                        vx_actual, vy_actual = 0.0, 0.0
                    else:
                        vx_actual = self._suavizar_inercia(vx_actual, vx_target)
                        vy_actual = self._suavizar_inercia(vy_actual, vy_target)

                    # Envio periodico de consignas de vuelo
                    scf.cf.commander.send_hover_setpoint(vx_actual, vy_actual, 0.0, altura_objetivo)
                    time.sleep(DT_LOOP)

                log_alt.stop()
                log_bat.stop()

        except (AterrizajeForzoso, AterrizajeControlado):
            try:
                log_alt.stop()
                log_bat.stop()
            except Exception:
                pass
        except Exception as e:
            print(f"Error de vuelo: {e}")
        finally:
            sock.close()
            self.volando = False
            self.freno_emergencia = False
            try:
                self.root.after(0, self.restaurar_ui)
            except Exception:
                pass

    def restaurar_ui(self):
        self.lbl_estado.config(text="Estado: EN TIERRA", fg="#00ff00")
        self.btn_modo_z.config(state="normal")
        self.btn_modo_libre.config(state="normal")
        self.btn_modo_teclado.config(state="normal")
        self.btn_stop.config(state="disabled")
        self._actualizar_telemetria_ui("centro", "centro", "centro", False)


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    ventana = tk.Tk()
    app = InterfazAvanzadaDron(ventana)
    ventana.mainloop()
