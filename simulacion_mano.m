% ==============================================================
% Programa actualizado por Manuel Ovalle
% Mano simulada 3D que replica movimientos de la mano real
% ==============================================================
% Este script visualiza una mano simulada en 3D que responde en tiempo real
% a los gestos y orientaciones detectados por el sensor Leap Motion.
% La comunicacion se realiza mediante UDP, recibiendo comandos desde Python.
% Los gestos controlan la apertura de los dedos y la orientacion de la palma
% (rotacion en roll y pitch). Incluye representacion de palma, antebrazo y dedos.
% ==============================================================

clc; clear; close all;

% Configuracion del socket UDP
u = udpport("datagram", "IPV4", "LocalPort", 50005);
disp("Esperando gestos desde Leap Motion...");

% Configuracion de ventana y escena
fig = figure( ...
    'Color','w', ...
    'MenuBar','none', ...
    'ToolBar','none', ...
    'NumberTitle','off', ...
    'Name','Mano 3D', ...
    'WindowState','fullscreen');

fig.CloseRequestFcn = @(~,~) cerrar(fig,u);

ax  = axes('Parent', fig, 'Units','normalized', 'Position',[0 0 1 1]);
set(ax, 'Color', 'k');
view(ax, 100, 0);
axis(ax, [-100 100 -100 100 -150 100]);
axis(ax, 'manual');
axis(ax, 'off');

% Iluminacion y sombreado
light(ax); 
camlight(ax, 'headlight'); 
lighting gouraud;
material dull

% Fijar controles de camara
set(fig, 'WindowScrollWheelFcn','', ...
         'WindowButtonDownFcn','', ...
         'WindowButtonMotionFcn','', ...
         'WindowButtonUpFcn','');
set(ax, 'CameraPositionMode','manual', ...
        'CameraTargetMode','manual', ...
        'CameraUpVectorMode','manual', ...
        'CameraViewAngleMode','manual');
camva(ax, 'manual');

% Boton de cierre de aplicacion
uicontrol('Style','pushbutton', ...
          'Parent', fig, ...
          'String','salir', ...
          'Units','normalized', ...
          'Position',[0.93 0.02 0.06 0.05], ...
          'BackgroundColor',[0.15 0.15 0.15], ...
          'ForegroundColor',[1 1 1], ...
          'FontSize',10, ...
          'Callback', @(~,~) cerrar(fig,u) );

% Propiedades geometricas y colores
color_palma   = [0 1 1];
color_falange = [1 1 1];
color_punta   = [0 1 1];
facealpha     = 1;
w = 10; h = 10;

% Longitud de falanges por dedo (pulgar a menique)
l_falanges = [
    25 20 15;  % pulgar
    30 25 20;  % indice
    32 30 25;  % medio
    30 25 20;  % anular
    27 20 12]; % menique

% Desplazamientos base respecto a la palma
finger_offsets = [
    -35, -5;   % pulgar
    -22,  0;   % indice
      -4,  0;  % medio
      12,  0;  % anular
      26, -5]; % menique

pulgar_yaw  = deg2rad(0);
pulgar_lean = deg2rad(-15);

% Geometria de la palma y el antebrazo
palma = hgtransform('Parent', ax);
drawCuboid([60, 15, 50], [0, 10, -20], color_palma, facealpha, palma);

antebrazo = hgtransform('Parent', palma);
[XC, YC, ZC] = cylinder(20, 30);
ZC = -ZC * 80 - 45;
YC = YC + 10;
surf(XC, YC, ZC, 'FaceColor', color_palma, 'EdgeColor','none', ...
    'FaceAlpha', facealpha, 'Parent', antebrazo);

theta = linspace(0, 2*pi, 30);
r = 20;
x_circ = r * cos(theta);
y_circ = r * sin(theta) + 10;
fill3(x_circ, y_circ, -120*ones(size(x_circ)), color_palma, ...
      'FaceAlpha',facealpha, 'EdgeColor','none','Parent',antebrazo);
fill3(x_circ, y_circ, -45 *ones(size(x_circ)), color_palma, ...
      'FaceAlpha',facealpha, 'EdgeColor','none','Parent',antebrazo);

% Estructura cinemática de las falanges
num_dedos = 5;
prox = gobjects(num_dedos,1);
med  = gobjects(num_dedos,1);
dist = gobjects(num_dedos,1);
puntas = gobjects(num_dedos,1);

ang_actual = zeros(1,5);
ang_obj    = zeros(1,5);

idx = struct('pulgar',1,'indice',2,'medio',3,'anular',4,'menique',5);

for i = 1:num_dedos
    offset = finger_offsets(i,:);
    lf = l_falanges(i,:);
    base = hgtransform('Parent', palma);

    if i == 1
        base.Matrix = makehgtform( ...
            'translate',[offset(1), offset(2)+15, 10]) * ...
            makehgtform('zrotate', pulgar_yaw) * ...
            makehgtform('yrotate', pulgar_lean);
    else
        base.Matrix = makehgtform('translate',[offset(1), offset(2)+5, 20]);
    end

    % Falange proximal
    prox(i) = hgtransform('Parent', base);
    drawCuboid([w,h,lf(1)], [0,0,0], color_falange, facealpha, prox(i));

    % Falange media
    med(i) = hgtransform('Parent', prox(i));
    drawCuboid([w,h,lf(2)], [0,0,0], color_falange, facealpha, med(i));
    med(i).Matrix = makehgtform('translate',[0 0 lf(1)]);

    % Falange distal
    dist(i) = hgtransform('Parent', med(i));
    drawCuboid([w,h,lf(3)], [0,0,0], color_falange, facealpha, dist(i));
    dist(i).Matrix = makehgtform('translate',[0 0 lf(2)]);

    % Extremo del dedo
    puntas(i) = hgtransform('Parent', dist(i));
    [xs,ys,zs] = sphere(10);
    r_tip = w/2;
    surf(r_tip*xs, r_tip*ys, r_tip*zs + lf(3), 'FaceColor', color_punta, ...
         'EdgeColor','none', 'FaceAlpha',facealpha, 'Parent',puntas(i));
end

% Parametros de suavizado y limites angulares
roll_actual = 0;   roll_target = 0;
pitch_actual = 0;  pitch_target = 0;
correccion_roll = deg2rad(-30);
alpha_smooth = 0.12;
alpha_finger = 0.14;

limit_prox = deg2rad([0 85]);
limit_med  = deg2rad([0 95]);
limit_dist = deg2rad([0 110]);

% Bucle de animacion y renderizado
while ishandle(fig)
    if u.NumDatagramsAvailable > 0
        d = read(u, 1, "string");
        msg = strtrim(d.Data);

        % Lectura de apertura y cierre de dedos
        if contains(msg, "mano=abierta")
            ang_obj = zeros(1,5);
        elseif contains(msg, "mano=cerrada")
            ang_obj = (pi/3) * ones(1,5);
        elseif contains(msg, ":")
            tokens = regexp(msg, '(pulgar|indice|medio|anular|menique)\s*:\s*(abierto|cerrado)', 'tokens');
            for t = 1:numel(tokens)
                nombre = string(tokens{t}{1});
                estado = string(tokens{t}{2});
                j = idx.(char(nombre));
                ang_obj(j) = (estado == "abierto")*0 + (estado == "cerrado")*(pi/3);
            end
        end

        % Lectura de roll
        if contains(msg, "izquierda")
            roll_target = deg2rad(30);
        elseif contains(msg, "derecha")
            roll_target = deg2rad(-30);
        elseif contains(msg, "centro")
            roll_target = 0;
        end

        % Lectura de pitch
        if contains(msg, "adelante")
            pitch_target = deg2rad(40);
        elseif contains(msg, "atras")
            pitch_target = deg2rad(-60);
        elseif contains(msg, "centro")
            pitch_target = 0;
        end
    end

    % Filtrado paso bajo de movimientos
    roll_actual  = roll_actual  + alpha_smooth * (roll_target  - roll_actual);
    pitch_actual = pitch_actual + alpha_smooth * (pitch_target - pitch_actual);
    ang_actual   = ang_actual   + alpha_finger * (ang_obj      - ang_actual);

    % Actualizar transformaciones de articulaciones
    for i = 1:num_dedos
        lf = l_falanges(i,:);
        a0 = clamp(ang_actual(i),       limit_prox(1), limit_prox(2));
        a1 = clamp(1.25*ang_actual(i),  limit_med(1),  limit_med(2));
        a2 = clamp(1.55*ang_actual(i),  limit_dist(1), limit_dist(2));

        prox(i).Matrix = makehgtform('xrotate', a0);
        med(i).Matrix  = makehgtform('translate',[0 0 lf(1)]) * makehgtform('xrotate', a1);
        dist(i).Matrix = makehgtform('translate',[0 0 lf(2)]) * makehgtform('xrotate', a2);
    end

    % Actualizar transformacion de la palma
    R = makehgtform('zrotate', roll_actual + correccion_roll) * ...
        makehgtform('xrotate', pitch_actual) * ...
        makehgtform('translate', [0, 10, -20]);
    palma.Matrix = R;

    drawnow limitrate
end

cerrar(fig,u);

% Funciones auxiliares
function y = clamp(x, a, b)
    y = min(max(x, a), b);
end

function drawCuboid(dim, pos, color, alpha, parent)
    [w,h,l] = deal(dim(1), dim(2), dim(3));
    [x,y,z] = ndgrid([0 w], [0 h], [0 l]);
    V = [x(:), y(:), z(:)];
    V = V - mean(V);
    V = V + pos;
    F = [1 2 4 3; 5 6 8 7; 1 2 6 5; 2 4 8 6; 4 3 7 8; 3 1 5 7];
    patch('Faces',F,'Vertices',V,'FaceColor',color,...
          'EdgeColor','none','FaceAlpha',alpha,'Parent',parent);
end

function cerrar(fig,u)
    try
        if exist('u','var') && ~isempty(u)
            clear u;
        end
    end
    try
        if isvalid(fig)
            delete(fig);
        end
    end
end
