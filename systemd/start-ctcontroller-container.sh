#!/bin/bash

IMAGE=tapis/ctcontroller:demo
CONTAINER=ctcontroller
PORT=8080

docker pull $IMAGE
CMD="docker create --name "$CONTAINER" -v /var/lib/ctcontroller:/var/lib/ctcontroller -v /var/run/docker.sock:/var/run/docker.sock -e ENV_PATH=/var/lib/ctcontroller/env -p $PORT:$PORT $IMAGE -d"

# check if container already exists
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
    CURRENT_IMAGE=$(docker inspect --format='{{.Image}}' "$CONTAINER")
    NEW_IMAGE=$(docker images -q "$IMAGE")

    # New image has been pulled, remove old container and create new one
    if [ "$CURRENT_IMAGE" != "$NEW_IMAGE" ]; then
        docker rm -f "$CONTAINER"
	$CMD
    fi
else
    # no container exists yet, create it
    $CMD
fi
