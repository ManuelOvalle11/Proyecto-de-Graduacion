import logging
import socket
import time

import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

# ==========================================
# 1. CONFIGURACIÓN DEL DRON Y RED
# ==========================================
# URI de tu dron (Verificá que sea la misma que te salía en el CFClient)
URI = 'radio://0/80/2M'

# Configuración del UDP (Escuchamos al puente del Leap Motion)
UDP_IP = "127.0.0.1"
UDP_PORT = 50005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False) # Para que el bucle no se congele esperando

# Velocidad de desplazamiento en m/s (0.2m/s es suave y seguro para empezar)
VELOCIDAD = 0.2

def main():
    # Inicializamos los drivers de la antena
    cflib.crtp.init_drivers()
    print("========================================")
    print("Conectando al Crazyflie...")
    print("========================================")

    # Conexión principal
    with SyncCrazyflie(URI) as scf:
        # MotionCommander asume el control usando el Flow deck
        with MotionCommander(scf) as mc:
            print("¡DESPEGUE EXITOSO! El dron está flotando.")
            print("Esperando gestos del Leap Motion...")
            print(">>> CIERRA EL PUÑO PARA ATERRIZAR <<<")

            volando = True
            while volando:
                try:
                    # Leemos los datos que manda el otro script de Python
                    data, addr = sock.recvfrom(1024)
                    msg = data.decode('utf-8')
                    
                    # --- 1. FRENO DE EMERGENCIA (Puño cerrado) ---
                    if msg.count("cerrado") >= 4:
                        print("¡PUÑO DETECTADO! Iniciando aterrizaje...")
                        volando = False # Esto rompe el bucle
                        break
                    
                    # --- 2. MAPEO DE CINEMÁTICA ---
                    vx = 0.0 # Velocidad en X (Adelante/Atrás)
                    vy = 0.0 # Velocidad en Y (Izquierda/Derecha)
                    
                    # Eje X (Pitch)
                    if "pitch:adelante" in msg:
                        vx = VELOCIDAD
                    elif "pitch:atras" in msg:
                        vx = -VELOCIDAD
                        
                    # Eje Y (Roll)
                    if "roll:izquierda" in msg:
                        vy = VELOCIDAD
                    elif "roll:derecha" in msg:
                        vy = -VELOCIDAD
                        
                    # Enviamos el vector de velocidad al controlador del dron
                    mc.start_linear_motion(vx, vy, 0.0)
                    
                except BlockingIOError:
                    # Si no hay datos de red nuevos en esta milésima de segundo, ignora
                    pass
                
                # Bucle a 20Hz para no saturar la radio del dron
                time.sleep(0.05) 

        # Al salir del bloque 'with MotionCommander', la librería ejecuta un aterrizaje suave automático
        print("Vuelo terminado. Dron en tierra.")

if __name__ == '__main__':
    main()