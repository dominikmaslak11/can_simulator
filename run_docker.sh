#!/bin/bash
# Skrypt do budowania i uruchamiania CAN Simulator w Dockerze

xhost +local:docker
docker build -t can-simulator .
docker run -it --rm \
    --privileged \
    --network host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $(pwd)/data:/app/data \
    --name can_simulator \
    can-simulator
xhost -local:docker
