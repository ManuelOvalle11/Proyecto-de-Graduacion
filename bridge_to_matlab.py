import socket
import time
import math
import leap

# ==========================================
# CONFIGURACIÓN DEL PUENTE UDP
# ==========================================
UDP_IP = "127.0.0.1" 
UDP_PORT = 50005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class TesisListener(leap.Listener):
    def __init__(self):
        super().__init__()
        # Variables para el control de FPS real
        self.last_frame_time = time.time()
        self.target_fps = 30  # 30 FPS es el equilibrio perfecto entre fluidez y rendimiento
        self.frame_delay = 1.0 / self.target_fps

    def on_tracking_event(self, event):
        current_time = time.time()
        
        # --- EL VERDADERO ANTI-LAG ---
        # Si no ha pasado el tiempo suficiente desde el último frame, ignoramos la lectura.
        if (current_time - self.last_frame_time) < self.frame_delay:
            return
            
        self.last_frame_time = current_time

        if event.hands:
            hand = event.hands[0] 
            
            # ------------------------------------------------
            # 1. EVALUACIÓN DE LOS DEDOS
            # ------------------------------------------------
            finger_states = []
            for i, finger in enumerate(hand.digits):
                if i == 0: 
                    tx, ty, tz = finger.distal.next_joint.x, finger.distal.next_joint.y, finger.distal.next_joint.z
                    px, py, pz = hand.palm.position.x, hand.palm.position.y, hand.palm.position.z
                    distancia_palma = math.sqrt((tx-px)**2 + (ty-py)**2 + (tz-pz)**2)
                    
                    finger_states.append(1 if distancia_palma > 60 else 0)
                else:
                    finger_states.append(1 if finger.is_extended else 0)
            
            nombres = ["pulgar", "indice", "medio", "anular", "menique"]
            estados = ["abierto" if s == 1 else "cerrado" for s in finger_states]
            msg_dedos = ";".join([f"{n}:{e}" for n, e in zip(nombres, estados)])
            
            # ------------------------------------------------
            # 2. EVALUACIÓN DE LA ORIENTACIÓN
            # ------------------------------------------------
            pitch_val = hand.palm.direction.y
            if pitch_val < -0.3:       msg_pitch = "pitch:adelante"
            elif pitch_val > 0.3:      msg_pitch = "pitch:atras"
            else:                      msg_pitch = "pitch:centro"
                
            roll_val = hand.palm.normal.x
            if roll_val > 0.3:         msg_roll = "roll:izquierda"
            elif roll_val < -0.3:      msg_roll = "roll:derecha"
            else:                      msg_roll = "roll:centro"
            
            # ------------------------------------------------
            # 3. ENVÍO DE DATOS OPTIMIZADO (1 solo paquete)
            # ------------------------------------------------
            # Unimos todo separado por el símbolo |
            payload = f"{msg_dedos}|{msg_roll}|{msg_pitch}"
            
            sock.sendto(payload.encode(), (UDP_IP, UDP_PORT))
            
            # Imprimir en consola es una operación pesada en Python. 
            # Si ves lag, comentá esta línea.
            print(f"Enviando: {payload}")

def main():
    print("========================================")
    print("Iniciando puente Leap Motion -> MATLAB")
    print(f"Transmitiendo en {UDP_IP}:{UDP_PORT} a 30 FPS reales")
    print("========================================")
    
    my_listener = TesisListener()
    connection = leap.Connection()
    connection.add_listener(my_listener)
    
    with connection.open():
        while True:
            # Este sleep ahora solo sirve para mantener el programa principal vivo
            # sin consumir el 100% de la CPU.
            time.sleep(1) 

if __name__ == "__main__":
    main()