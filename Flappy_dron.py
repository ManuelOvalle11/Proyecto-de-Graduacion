import pygame
import leap
import random
import sys

# Configuracion general
WIDTH, HEIGHT = 1000, 600
FPS = 60

# Paleta de colores
SKY_BLUE = (135, 206, 235)
PIPE_COLOR = (34, 139, 34)
TEXT_COLOR = (255, 255, 255)
ALERT_COLOR = (255, 50, 50)
MENU_COLOR = (40, 40, 80)
BIRD_COLOR = (255, 215, 0)
P1_COLOR = (0, 150, 255)
P2_COLOR = (255, 50, 50)
DEAD_COLOR = (100, 100, 100)

# Limites de lectura en eje Y (Leap Motion)
LEAP_Y_MIN = 100.0  
LEAP_Y_MAX = 400.0  

class LeapController(leap.Listener):
    def __init__(self):
        super().__init__()
        self.hands_data = []

    def on_tracking_event(self, event):
        hands = []
        for hand in event.hands:
            hands.append({
                'x': hand.palm.position.x,
                'y': hand.palm.position.y
            })
        # Ordenar manos de izquierda a derecha en X
        self.hands_data = sorted(hands, key=lambda h: h['x'])

def map_leap_to_screen(leap_x, leap_y, player_id):
    # Mapeo de altura Y a coordenadas de pantalla
    ratio_y = max(0.0, min(1.0, (leap_y - LEAP_Y_MIN) / (LEAP_Y_MAX - LEAP_Y_MIN)))
    screen_y = HEIGHT - (ratio_y * HEIGHT)
    
    # Asignacion de posicion base segun jugador
    if player_id == 1:
        base_screen_x = WIDTH // 3 - 30
        base_leap_x = -100.0
    elif player_id == 2:
        base_screen_x = WIDTH // 3 + 30
        base_leap_x = 100.0
    else:
        base_screen_x = WIDTH // 3
        base_leap_x = 0.0

    # Desplazamiento horizontal escalado
    screen_x = base_screen_x + (leap_x - base_leap_x) * 1.5
    screen_x = max(20, min(WIDTH - 20, screen_x))
    
    return screen_x, screen_y

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Flappy Leap - Caos 2D Justo")
    clock = pygame.time.Clock()
    
    font_small = pygame.font.SysFont("Arial", 28, bold=True)
    font_med = pygame.font.SysFont("Arial", 40, bold=True)
    font_big = pygame.font.SysFont("Arial", 55, bold=True)

    # Conexion con Leap Motion
    listener = LeapController()
    connection = leap.Connection()
    connection.add_listener(listener)

    state = "MENU"
    mode = 1

    # Estado y posicion de los jugadores
    radius = 20
    p1_pos = [WIDTH // 3, HEIGHT // 2]
    p2_pos = [WIDTH // 3 + 30, HEIGHT // 2]
    p1_alive = False
    p2_alive = False

    # Parametros de obstaculos
    pipe_width = 80
    pipe_gap = 220 
    base_velocity = 5.0
    pipe_velocity = base_velocity
    pipes = []

    score = 0
    base_spawn_time = 1500
    spawn_time = base_spawn_time
    
    SPAWNPIPE = pygame.USEREVENT

    def reset_game(selected_mode):
        nonlocal score, p1_pos, p2_pos, p1_alive, p2_alive, pipes, pipe_velocity, spawn_time
        score = 0
        pipes.clear()
        
        # Reiniciar posiciones segun modo de juego
        if selected_mode == 1:
            p1_pos = [WIDTH // 3, HEIGHT // 2]
        else:
            p1_pos = [WIDTH // 3 - 30, HEIGHT // 2]
            p2_pos = [WIDTH // 3 + 30, HEIGHT // 2]
            
        p1_alive = True
        p2_alive = (selected_mode == 2) 
        pipe_velocity = base_velocity
        spawn_time = base_spawn_time
        pygame.time.set_timer(SPAWNPIPE, spawn_time)

    with connection.open():
        while True:
            # Manejo de eventos de entrada y ventana
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # Seleccion de modo en menu
                if state == "MENU":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_1:
                            mode = 1
                            reset_game(mode)
                            state = "PLAYING"
                        elif event.key == pygame.K_2:
                            mode = 2
                            reset_game(mode)
                            state = "PLAYING"

                # Reiniciar al menu tras perder
                elif state == "GAMEOVER":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            state = "MENU"
                            pygame.time.set_timer(SPAWNPIPE, 0)

                # Generacion periodica de tubos
                elif state == "PLAYING" and event.type == SPAWNPIPE:
                    if (mode == 1 and len(listener.hands_data) >= 1) or (mode == 2 and len(listener.hands_data) == 2):
                        pipe_height = random.randint(100, HEIGHT - 100 - pipe_gap)
                        pipes.append(pygame.Rect(WIDTH, pipe_height + pipe_gap, pipe_width, HEIGHT - pipe_height - pipe_gap)) 
                        pipes.append(pygame.Rect(WIDTH, 0, pipe_width, pipe_height)) 

            # Logica de juego
            if state == "PLAYING":
                num_hands = len(listener.hands_data)
                
                # Pausar si no se detectan las manos requeridas
                is_paused = False
                if mode == 1 and num_hands == 0:
                    is_paused = True
                elif mode == 2 and num_hands < 2:
                    is_paused = True

                if not is_paused:
                    # Suavizado de movimiento de jugadores
                    if p1_alive and num_hands >= 1:
                        p_id = 1 if mode == 2 else 0
                        target_x, target_y = map_leap_to_screen(listener.hands_data[0]['x'], listener.hands_data[0]['y'], p_id)
                        p1_pos[0] += (target_x - p1_pos[0]) * 0.15
                        p1_pos[1] += (target_y - p1_pos[1]) * 0.15

                    if mode == 2 and p2_alive and num_hands >= 2:
                        target_x, target_y = map_leap_to_screen(listener.hands_data[1]['x'], listener.hands_data[1]['y'], 2)
                        p2_pos[0] += (target_x - p2_pos[0]) * 0.15
                        p2_pos[1] += (target_y - p2_pos[1]) * 0.15

                    # Movimiento y eliminacion de obstaculos fuera de pantalla
                    for pipe in pipes:
                        pipe.x -= int(pipe_velocity)
                    
                    if pipes and pipes[0].right < 0:
                        pipes.pop(0) 
                        pipes.pop(0) 
                        score += 1
                        
                        # Incremento progresivo de dificultad
                        pipe_velocity = min(16.0, pipe_velocity + 0.5)
                        spawn_time = max(500, spawn_time - 50)
                        pygame.time.set_timer(SPAWNPIPE, spawn_time)

                    # Deteccion de colisiones (obstaculos y bordes)
                    if p1_alive:
                        p1_rect = pygame.Rect(p1_pos[0] - radius, p1_pos[1] - radius, radius*2, radius*2)
                        if any(p1_rect.colliderect(p) for p in pipes) or p1_pos[1] <= 0 or p1_pos[1] >= HEIGHT:
                            p1_alive = False

                    if mode == 2 and p2_alive:
                        p2_rect = pygame.Rect(p2_pos[0] - radius, p2_pos[1] - radius, radius*2, radius*2)
                        if any(p2_rect.colliderect(p) for p in pipes) or p2_pos[1] <= 0 or p2_pos[1] >= HEIGHT:
                            p2_alive = False

                    if not p1_alive and not p2_alive:
                        state = "GAMEOVER"

            # Renderizado
            if state == "MENU":
                screen.fill(MENU_COLOR)
                title = font_big.render("FLAPPY LEAP", True, BIRD_COLOR)
                op1 = font_med.render("Presiona [1] - Un Jugador", True, P1_COLOR)
                op2 = font_med.render("Presiona [2] - Dos Jugadores", True, P2_COLOR)
                
                screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3 - 50))
                screen.blit(op1, (WIDTH//2 - op1.get_width()//2, HEIGHT//2))
                screen.blit(op2, (WIDTH//2 - op2.get_width()//2, HEIGHT//2 + 70))

            elif state == "PLAYING" or state == "GAMEOVER":
                screen.fill(SKY_BLUE)

                for pipe in pipes:
                    pygame.draw.rect(screen, PIPE_COLOR, pipe)

                # Dibujar jugadores eliminados en la base
                if mode == 2 and not p2_alive:
                    pygame.draw.circle(screen, DEAD_COLOR, (int(p2_pos[0]), HEIGHT - radius), radius)
                if not p1_alive:
                    pygame.draw.circle(screen, DEAD_COLOR, (int(p1_pos[0]), HEIGHT - radius), radius)

                # Dibujar jugadores activos
                if mode == 2 and p2_alive:
                    pygame.draw.circle(screen, P2_COLOR, (int(p2_pos[0]), int(p2_pos[1])), radius)
                if p1_alive:
                    pygame.draw.circle(screen, P1_COLOR, (int(p1_pos[0]), int(p1_pos[1])), radius)

                # Marcador
                score_text = font_small.render(f"Puntos: {score} | Vel: {pipe_velocity:.1f}", True, TEXT_COLOR)
                screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 10))

                # Avisos de deteccion de manos
                if state == "PLAYING":
                    if mode == 1 and len(listener.hands_data) == 0:
                        warn = font_med.render("PON TU MANO PARA INICIAR", True, ALERT_COLOR)
                        screen.blit(warn, (WIDTH//2 - warn.get_width()//2, HEIGHT//2))
                    elif mode == 2 and len(listener.hands_data) < 2:
                        warn = font_med.render("AMBOS JUGADORES PONGAN LAS MANOS", True, ALERT_COLOR)
                        screen.blit(warn, (WIDTH//2 - warn.get_width()//2, HEIGHT//2))

                elif state == "GAMEOVER":
                    msg = font_big.render("¡DRONES DESTRUIDOS!", True, ALERT_COLOR)
                    msg2 = font_med.render("Presiona ESPACIO para ir al menú", True, TEXT_COLOR)
                    screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 40))
                    screen.blit(msg2, (WIDTH//2 - msg2.get_width()//2, HEIGHT//2 + 30))

            pygame.display.update()
            clock.tick(FPS)

if __name__ == "__main__":
    main()
