% ==============================================================
% Programa desarrollado por Manuel Ovalle
% Dron Racer con control por gestos via UDP
% ==============================================================
% Este script implementa un juego de esquivar obstaculos en 2D en MATLAB
% basado en una maquina de estados finitos. Recibe datos UDP de Leap Motion;
% la deteccion de puno cerrado inicia la partida y la inclinacion (roll)
% conmuta de carril en tiempo real.
% ==============================================================

clc; clear; close all;

% Configuracion del socket UDP
if ~isempty(instrfindall), delete(instrfindall); end
u = udpport("datagram", "IPV4", "LocalPort", 50005);
disp("Esperando conexión del Leap Motion...");

% Configuracion de la ventana y limites de los ejes
fig = figure('Name', 'Dron Racer', 'Color', 'k', 'MenuBar', 'none', ...
    'ToolBar', 'none', 'WindowState', 'fullscreen');
ax = axes('Parent', fig, 'Color', 'k', 'XColor', 'none', 'YColor', 'none');
axis(ax, [0 100 0 100]); hold on;

% Lineas divisorias de carriles
plot([33 33], [0 100], 'w--', 'LineWidth', 2);
plot([66 66], [0 100], 'w--', 'LineWidth', 2);

% Coordenadas centrales de carriles y creacion del jugador
carriles = [16.5, 50, 83.5];

player_x = carriles(2); 
target_x = player_x;
dron = rectangle('Position', [player_x-5, 10, 10, 10], 'FaceColor', 'c', 'EdgeColor', 'w', 'Curvature', 0.2);

% Inicializacion del obstaculo
obs_y = 100;
obs_x = carriles(randi(3));
obs = rectangle('Position', [obs_x-5, obs_y, 10, 10], 'FaceColor', 'r', 'EdgeColor', 'w');

% Textos de interfaz de juego
score_txt = text(5, 95, 'Puntos: 0', 'Color', 'w', 'FontSize', 20, 'FontWeight', 'bold');
instruccion_juego = text(5, 5, 'Gira la muneca (Roll) para cambiar de carril', 'Color', 'y', 'FontSize', 12);

% Textos de interfaz del menu principal
titulo_txt = text(50, 65, 'DRON RACER', 'Color', 'c', 'FontSize', 50, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');
start_txt = text(50, 45, 'CIERRA EL PUÑO PARA EMPEZAR', 'Color', 'y', 'FontSize', 25, 'HorizontalAlignment', 'center', 'FontWeight', 'bold');

% Variables de estado y dinamica de juego
score = 0;
velocidad_juego = 2.5; 
suavizado = 0.3;       
estado_juego = 0; % 0: Menu, 1: Jugando

% Bucle principal
while ishandle(fig)
    
    % Lectura del datagrama mas reciente del buffer UDP
    msg = "";
    while u.NumDatagramsAvailable > 0
        d = read(u, 1, "string");
        msg = strtrim(d.Data);
    end
    
    % Maquina de estados
    if estado_juego == 0
        % Estado 0: Menu de inicio
        set(dron, 'Visible', 'off');
        set(obs, 'Visible', 'off');
        set(score_txt, 'Visible', 'off');
        set(instruccion_juego, 'Visible', 'off');
        
        set(titulo_txt, 'Visible', 'on');
        set(start_txt, 'Visible', 'on');
        
        % Deteccion de gesto de puno para iniciar partida
        if msg ~= "" && count(msg, "cerrado") >= 4
            estado_juego = 1;
            
            set(titulo_txt, 'Visible', 'off');
            set(start_txt, 'Visible', 'off');
            
            set(dron, 'Visible', 'on');
            set(obs, 'Visible', 'on');
            set(score_txt, 'Visible', 'on');
            set(instruccion_juego, 'Visible', 'on');
            
            % Reinicio de parametros de partida
            score = 0;
            velocidad_juego = 2.5;
            obs_y = 100;
            obs_x = carriles(randi(3));
            player_x = carriles(2);
            target_x = carriles(2);
            set(score_txt, 'String', 'Puntos: 0');
            set(dron, 'Position', [player_x-5, 10, 10, 10]);
            
            pause(1); 
        end
        
    elseif estado_juego == 1
        % Estado 1: Juego activo
        % Seleccion de carril segun inclinacion (roll)
        if msg ~= ""
            if contains(msg, "roll:izquierda")
                target_x = carriles(1);
            elseif contains(msg, "roll:derecha")
                target_x = carriles(3);
            elseif contains(msg, "roll:centro")
                target_x = carriles(2);
            end
        end
        
        % Interpolacion lineal de posicion en X
        player_x = player_x + suavizado * (target_x - player_x);
        set(dron, 'Position', [player_x-5, 10, 10, 10]);
        
        % Actualizacion de posicion del obstaculo
        obs_y = obs_y - velocidad_juego;
        
        % Reinicio del obstaculo superado e incremento de dificultad
        if obs_y < -10
            obs_y = 100;
            obs_x = carriles(randi(3)); 
            score = score + 1;
            set(score_txt, 'String', ['Puntos: ', num2str(score)]);
            
            if velocidad_juego < 9 
                velocidad_juego = velocidad_juego + 0.2; 
            end
        end
        
        set(obs, 'Position', [obs_x-5, obs_y, 10, 10]);
        
        % Deteccion de colision por proximidad de cajas
        colision_x = abs(player_x - obs_x) < 8; 
        colision_y = abs(10 - obs_y) < 8;
        
        if colision_x && colision_y
            texto_fin = text(30, 50, '¡CHOQUE!', 'Color', 'r', 'FontSize', 40, 'FontWeight', 'bold');
            pause(1.5);
            delete(texto_fin);
            
            estado_juego = 0; 
        end
    end
    
    % Refresco grafico
    drawnow limitrate;
    pause(0.03); 
end

clear u;
