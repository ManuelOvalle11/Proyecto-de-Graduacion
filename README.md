# Proyecto-de-Graduacion
Proyecto de Graduación – Teleoperación Gestual e Integración de Sistemas Robóticos

Este repositorio reúne todos los scripts, códigos y simulaciones desarrollados durante el proyecto de graduación de Manuel Enrique Ovalle Fuentes en la Universidad del Valle de Guatemala.

El trabajo demuestra la integración y el control de múltiples sistemas robóticos (tanto físicos como virtuales) utilizando interfaces gestuales en tiempo real con el sensor Leap Motion. El ecosistema conecta hardware de robótica aérea y terrestre con simulaciones interactivas utilizando Python y MATLAB.

Descripción general
El objetivo principal del proyecto es lograr un control intuitivo y fluido de diferentes plataformas robóticas mediante el mapeo de los movimientos de la mano humana. Los módulos desarrollados van desde algoritmos de control de vuelo y navegación terrestre, hasta entornos gamificados diseñados para poner a prueba los reflejos del usuario en talleres interactivos.

El sistema completo incluye:

Dron físico (Crazyflie 2.1): Scripts de vuelo asistido y teleoperación gestual utilizando el módulo Flow deck.

Robot móvil físico (Pololu 3pi+): Control de tracción diferencial adaptado a los gestos de la muñeca para pistas de obstáculos.

Entornos de simulación en Python (Pygame): Juegos interactivos en 2D controlados por gestos (Flappy Leap Duo y Dron Racer).

Simulaciones de control avanzado en MATLAB: Planificación de trayectorias (A*) y simulación de aterrizaje de cohetes.

Interfaces de comunicación: Puentes de transmisión de datos en tiempo real mediante protocolos UDP entre el Leap Motion, Python y el hardware.
