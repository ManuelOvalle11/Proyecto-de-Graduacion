# ==============================================================
# Programa desarrollado por Manuel Ovalle
# Puente de comunicacion UDP para Leap Motion
# ==============================================================
# Este script captura los datos de seguimiento del sensor Leap Motion
# y transmite por UDP los estados de los dedos, la orientacion (pitch, roll)
# y la altura de la mano a una tasa constante de 30 FPS.
# ==============================================================

import socket
import time
import math
import leap

# Configuracion de conexion UDP
UDP_IP = "127.0.0.1" 
UDP_PORT = 50005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class TesisListener(leap.Listener):
    def __init__(self):
        super().__init__()
        # Control de frecuencia de envio
        self.last_frame_time = time.time()
        self.target_fps = 30
        self.frame_delay = 1.0 / self.target_fps

    def on_tracking_event(self, event):
        current_time = time.time()
        
        # Limitar tasa de refresco a los FPS definidos
        if (current_time - self.last_frame_time) < self.frame_delay:
            return
            
        self.last_frame_time = current_time

        if event.hands:
            hand = event.hands[0] 
            
            # Estado de los dedos (abierto/cerrado)
            finger_states = []
            for i, finger in enumerate(hand.digits):
                if i == 0: 
                    # El pulgar se evalua por distancia a la palma
                    tx, ty, tz = finger.distal.next_joint.x, finger.distal.next_joint.y, finger.distal.next_joint.z
                    px, py, pz = hand.palm.position.x, hand.palm.position.y, hand.palm.position.z
                    distancia_palma = math.sqrt((tx-px)**2 + (ty-py)**2 + (tz-pz)**2)
                    finger_states.append(1 if distancia_palma > 60 else 0)
                else:
                    # Resto de dedos segun extension
                    finger_states.append(1 if finger.is_extended else 0)
            
            nombres = ["pulgar", "indice", "medio", "anular", "menique"]
            estados = ["abierto" if s == 1 else "cerrado" for s in finger_states]
            msg_dedos = ";".join([f"{n}:{e}" for n, e in zip(nombres, estados)])
            
            # Inclinacion (pitch y roll)
            pitch_val = hand.palm.direction.y
            if pitch_val < -0.3:       msg_pitch = "pitch:adelante"
            elif pitch_val > 0.3:      msg_pitch = "pitch:atras"
            else:                      msg_pitch = "pitch:centro"
                
            roll_val = hand.palm.normal.x
            if roll_val > 0.3:         msg_roll = "roll:izquierda"
            elif roll_val < -0.3:      msg_roll = "roll:derecha"
            else:                      msg_roll = "roll:centro"

            # Altura en eje Y (mm)
            altura_y = hand.palm.position.y
            if altura_y > 250:         msg_altura = "altura:arriba"
            elif altura_y < 150:       msg_altura = "altura:abajo"
            else:                      msg_altura = "altura:centro"
            
            # Envio de datos por UDP
            payload = f"{msg_dedos}|{msg_roll}|{msg_pitch}|{msg_altura}"
            sock.sendto(payload.encode(), (UDP_IP, UDP_PORT))
            
            print(f"Y={altura_y:.0f}mm -> Enviando: {payload}")

def main():
    print("========================================")
    print("Iniciando puente Leap Motion -> POLOLU Y DRON (Con Altura)")
    print(f"Transmitiendo en {UDP_IP}:{UDP_PORT} a 30 FPS")
    print("========================================")
    
    # Inicializar conexion con el sensor
    my_listener = TesisListener()
    connection = leap.Connection()
    connection.add_listener(my_listener)
    
    with connection.open():
        while True:
            time.sleep(1) 

if __name__ == "__main__":
    main()
