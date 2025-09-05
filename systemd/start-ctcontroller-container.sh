#!/bin/bash

IMAGE=tapis/ctcontroller:demo
CONTAINER=ctcontroller
PORT=8080

#docker pull $IMAGE

# check if container already exists
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
    CURRENT_IMAGE=$(docker inspect --format='{{.Image}}' "$CONTAINER")
    NEW_IMAGE=$(docker images -q "$IMAGE")

    # New image has been pulled, remove old container and create new one
    if [ "$CURRENT_IMAGE" != "$NEW_IMAGE" ]; then
        docker rm -f "$CONTAINER"
        docker create --name "$CONTAINER" -p $PORT:$PORT $IMAGE -d
    fi
else
    # no container exists yet, create it
    docker create --name "$CONTAINER" -p $PORT:$PORT $IMAGE -d
fi
