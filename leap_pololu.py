# ==============================================================
# Programa actualizado por Manuel Ovalle
# Control teleoperado de robot Pololu 3Pi+ con Leap Motion
# ==============================================================
# Este script establece comunicacion con un robot movil Pololu 3Pi+
# via WiFi y mapea los gestos de la mano detectados por el Leap Motion
# a un esquema de traccion diferencial. El pitch controla la velocidad
# longitudinal, el roll el giro, y el puno cerrado actua como parada de emergencia.
# ==============================================================

import time
import os
import leap
from Pololu3Pi import Pololu3Pi

# Ruta de instalacion del SDK de Leap Motion
os.environ["LEAPSDK_INSTALL_LOCATION"] = "D:\\LeapSDK"

# Parametros de red y dinamica
ROBOT_IP = "192.168.50.114"
MAX_SPEED = 400
DEADZONE_PITCH = 15
DEADZONE_ROLL = 50

class PololuController(leap.Listener):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.last_update = time.time()

    def on_tracking_event(self, event):
        # Limitar tasa de envio a periodos de 100 ms
        if time.time() - self.last_update < 0.1:
            return
        self.last_update = time.time()

        # Detener motores si no hay manos detectadas
        if not event.hands:
            self.bot.set_wheel_velocities(0, 0)
            return

        hand = event.hands[0]

        # Parada de emergencia por puno cerrado
        if hand.grab_strength > 0.8:
            self.bot.set_wheel_velocities(0, 0)
            print("FRENO DE EMERGENCIA (Puno cerrado)")
            return

        # Lectura de inclinacion
        pitch_raw = hand.palm.direction.y  
        roll_raw = hand.palm.normal.x      

        base_speed = -pitch_raw * 500
        turn_speed = -roll_raw * 140  

        # Filtro de zona muerta
        if abs(base_speed) < DEADZONE_PITCH:
            base_speed = 0
            
        if abs(turn_speed) < DEADZONE_ROLL:
            turn_speed = 0

        # Cinematica diferencial
        v_left = base_speed + turn_speed
        v_right = base_speed - turn_speed

        # Saturacion a limites de velocidad
        v_left = max(-MAX_SPEED, min(MAX_SPEED, v_left))
        v_right = max(-MAX_SPEED, min(MAX_SPEED, v_right))

        # Envio de comandos a los motores
        self.bot.set_wheel_velocities(int(v_left), int(v_right))
        print(f"Motores -> Izq: {int(v_left):4d} | Der: {int(v_right):4d}")

def main():
    print("========================================")
    print("Iniciando Enlace: Leap Motion -> Pololu")
    print("========================================")
    
    # Conexion con el robot
    bot = Pololu3Pi()
    print(f"Conectando al Pololu en {ROBOT_IP}...")
    bot.connect(ip=ROBOT_IP)
    print("Pololu conectado exitosamente.\n")

    # Inicializar listener del sensor
    my_listener = PololuController(bot)
    connection = leap.Connection()
    connection.add_listener(my_listener)
    
    print("Sensor Leap Motion activo.")
    print(" - Pitch: avanzar / retroceder")
    print(" - Roll: giro diferencial")
    print(" - Puno cerrado: freno")
    print(" - Ctrl+C para finalizar")

    try:
        with connection.open():
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nSaliendo del programa...")
    finally:
        # Cierre seguro y detencion de actuadores
        print("Apagando motores y cerrando conexion...")
        bot.force_stop()
        bot.disconnect()

if __name__ == "__main__":
    main()
