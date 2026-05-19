% ==============================================================
% DRON RACER - Máquina de Estados (Arranque por Puño)
% ==============================================================
clc; clear; close all;

% Limpiamos el puerto UDP
if ~isempty(instrfindall), delete(instrfindall); end
u = udpport("datagram", "IPV4", "LocalPort", 50005);
disp("Esperando conexión del Leap Motion...");

% --- CONFIGURACIÓN DE LA PANTALLA ---
fig = figure('Name', 'Dron Racer', 'Color', 'k', 'MenuBar', 'none', ...
    'ToolBar', 'none', 'WindowState', 'fullscreen');
ax = axes('Parent', fig, 'Color', 'k', 'XColor', 'none', 'YColor', 'none');
axis(ax, [0 100 0 100]); hold on;

% --- DIBUJAR LOS CARRILES ---
plot([33 33], [0 100], 'w--', 'LineWidth', 2);
plot([66 66], [0 100], 'w--', 'LineWidth', 2);

% --- ELEMENTOS GRÁFICOS ---
carriles = [16.5, 50, 83.5];

player_x = carriles(2); 
target_x = player_x;
dron = rectangle('Position', [player_x-5, 10, 10, 10], 'FaceColor', 'c', 'EdgeColor', 'w', 'Curvature', 0.2);

obs_y = 100;
obs_x = carriles(randi(3));
obs = rectangle('Position', [obs_x-5, obs_y, 10, 10], 'FaceColor', 'r', 'EdgeColor', 'w');

% --- UI DEL JUEGO ---
score_txt = text(5, 95, 'Puntos: 0', 'Color', 'w', 'FontSize', 20, 'FontWeight', 'bold');
instruccion_juego = text(5, 5, 'Gira la muneca (Roll) para cambiar de carril', 'Color', 'y', 'FontSize', 12);

% --- UI DEL MENÚ PRINCIPAL ---
titulo_txt = text(50, 65, 'DRON RACER', 'Color', 'c', 'FontSize', 50, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');
start_txt = text(50, 45, 'CIERRA EL PUÑO PARA EMPEZAR', 'Color', 'y', 'FontSize', 25, 'HorizontalAlignment', 'center', 'FontWeight', 'bold');

% --- VARIABLES DE JUEGO Y ESTADO ---
score = 0;
velocidad_juego = 2.5; 
suavizado = 0.3;       
estado_juego = 0; % 0 = Menú de Inicio, 1 = Jugando

% Bucle principal
while ishandle(fig)
    
    % 1. LEER EL LEAP MOTION (Limpiar el buffer)
    msg = "";
    while u.NumDatagramsAvailable > 0
        d = read(u, 1, "string");
        msg = strtrim(d.Data);
    end
    
    % 2. MÁQUINA DE ESTADOS
    if estado_juego == 0
        % ==========================================
        % ESTADO 0: MENÚ DE INICIO
        % ==========================================
        % Esconder elementos del juego
        set(dron, 'Visible', 'off');
        set(obs, 'Visible', 'off');
        set(score_txt, 'Visible', 'off');
        set(instruccion_juego, 'Visible', 'off');
        
        % Mostrar elementos del menú
        set(titulo_txt, 'Visible', 'on');
        set(start_txt, 'Visible', 'on');
        
        % Detección de Puño: Si lee la palabra "cerrado" 4 o más veces
        if msg ~= "" && count(msg, "cerrado") >= 4
            % ¡Transición al juego!
            estado_juego = 1;
            
            % Esconder el menú
            set(titulo_txt, 'Visible', 'off');
            set(start_txt, 'Visible', 'off');
            
            % Mostrar el juego
            set(dron, 'Visible', 'on');
            set(obs, 'Visible', 'on');
            set(score_txt, 'Visible', 'on');
            set(instruccion_juego, 'Visible', 'on');
            
            % Resetear variables físicas
            score = 0;
            velocidad_juego = 2.5;
            obs_y = 100;
            obs_x = carriles(randi(3));
            player_x = carriles(2);
            target_x = carriles(2);
            set(score_txt, 'String', 'Puntos: 0');
            set(dron, 'Position', [player_x-5, 10, 10, 10]);
            
            % Pausa dramática antes de que caiga el primer cuadro
            pause(1); 
        end
        
    elseif estado_juego == 1
        % ==========================================
        % ESTADO 1: JUGANDO
        % ==========================================
        % Lógica de Control (Cambio de carril por Roll)
        if msg ~= ""
            if contains(msg, "roll:izquierda")
                target_x = carriles(1);
            elseif contains(msg, "roll:derecha")
                target_x = carriles(3);
            elseif contains(msg, "roll:centro")
                target_x = carriles(2);
            end
        end
        
        % Mover el dron suavemente
        player_x = player_x + suavizado * (target_x - player_x);
        set(dron, 'Position', [player_x-5, 10, 10, 10]);
        
        % Físicas de los obstáculos
        obs_y = obs_y - velocidad_juego;
        
        % Si esquivaste el obstáculo
        if obs_y < -10
            obs_y = 100;
            obs_x = carriles(randi(3)); 
            score = score + 1;
            set(score_txt, 'String', ['Puntos: ', num2str(score)]);
            
            % Aumentar la dificultad
            if velocidad_juego < 9 
                velocidad_juego = velocidad_juego + 0.2; 
            end
        end
        
        set(obs, 'Position', [obs_x-5, obs_y, 10, 10]);
        
        % Detección de colisiones
        colision_x = abs(player_x - obs_x) < 8; 
        colision_y = abs(10 - obs_y) < 8;
        
        if colision_x && colision_y
            texto_fin = text(30, 50, '¡CHOQUE!', 'Color', 'r', 'FontSize', 40, 'FontWeight', 'bold');
            pause(1.5);
            delete(texto_fin);
            
            % Regresar al menú principal
            estado_juego = 0; 
        end
    end
    
    % Refrescar pantalla a ~30 FPS
    drawnow limitrate;
    pause(0.03); 
end

clear u;