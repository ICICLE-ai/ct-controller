#!/bin/bash

if [ "$1" == "-d" ]; then
    #python -u -c "import ctcontroller; ctcontroller.run(True)"
    uvicorn ctcontroller.api:app --host 0.0.0.0 --port 8080 --reload --env-file $ENV_PATH
else
    python -u -c "import ctcontroller; ctcontroller.run()"
fi
