import time
import leap
from Pololu3Pi import Pololu3Pi

# ==========================================
# CONFIGURACIÓN
# ==========================================
ROBOT_IP = "192.168.50.115"
MAX_SPEED = 90      # Velocidad máxima segura (0 a 100)
DEADZONE = 15       # Zona muerta para que el robot no tiemble si tu mano no está perfectamente plana

class PololuController(leap.Listener):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.last_update = time.time()

    def on_tracking_event(self, event):
        # ⚠️ IMPORTANTE: El Leap Motion lee a más de 100 FPS. 
        # Si le mandamos 100 órdenes por segundo al ESP32 por Wi-Fi, lo vamos a trabar.
        # Limitamos la transmisión a 10 veces por segundo (10 Hz).
        if time.time() - self.last_update < 0.1:
            return
        self.last_update = time.time()

        # Si el sensor no detecta ninguna mano, el robot se detiene por seguridad
        if not event.hands:
            self.bot.set_wheel_velocities(0, 0)
            return

        hand = event.hands[0]

        # ------------------------------------------------
        # 1. BOTÓN DE PÁNICO (Freno de emergencia)
        # ------------------------------------------------
        if hand.grab_strength > 0.8:
            self.bot.set_wheel_velocities(0, 0)
            print("🛑 FRENO DE EMERGENCIA (Puño cerrado)")
            return

        # ------------------------------------------------
        # 2. LECTURA Y CONTROL PROPORCIONAL
        # ------------------------------------------------
        # Extraemos los vectores crudos
        pitch_raw = hand.palm.direction.y  # Dedos abajo es negativo
        roll_raw = hand.palm.normal.x      # Muñeca a la derecha es positivo

        # Escalamos el rango del sensor (-0.5 a 0.5) al rango de los motores (-100 a 100)
        # Multiplicamos por 200 para hacer la conversión directa
        base_speed = -pitch_raw * 200
        turn_speed = roll_raw * 200

        # Mezcla Diferencial
        v_left = base_speed + turn_speed
        v_right = base_speed - turn_speed

        # Saturación (Clamp): Evitamos mandar velocidades mayores a MAX_SPEED
        v_left = max(-MAX_SPEED, min(MAX_SPEED, v_left))
        v_right = max(-MAX_SPEED, min(MAX_SPEED, v_right))

        # Zona Muerta: Si las velocidades calculadas son muy bajas, las forzamos a cero
        if abs(v_left) < DEADZONE and abs(v_right) < DEADZONE:
            v_left, v_right = 0, 0

        # Enviamos la orden física al Pololu
        self.bot.set_wheel_velocities(int(v_left), int(v_right))
        
        # Monitor para que veas qué está pasando
        print(f"Motores -> Izq: {int(v_left):4d} | Der: {int(v_right):4d}")

def main():
    print("========================================")
    print("Iniciando Enlace: Leap Motion -> Pololu")
    print("========================================")
    
    bot = Pololu3Pi()
    print(f"🔌 Conectando al Pololu en {ROBOT_IP}...")
    bot.connect(ip=ROBOT_IP)
    print("✅ Pololu conectado exitosamente.\n")

    my_listener = PololuController(bot)
    connection = leap.Connection()
    connection.add_listener(my_listener)
    
    print("✋ Sensor Leap Motion activo.")
    print("   - Inclina hacia adelante/atrás para avanzar/retroceder.")
    print("   - Gira la muñeca para cruzar.")
    print("   - ✊ CIERRA EL PUÑO para frenar.")
    print("   - (Presiona Ctrl+C en esta ventana para salir)")

    try:
        with connection.open():
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nSaliendo del programa...")
    finally:
        # Corte seguro de energía
        print("Apagando motores y cerrando conexión...")
        bot.force_stop()
        bot.disconnect()

if __name__ == "__main__":
    main()