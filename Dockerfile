# Image: tapis/camera_traps_engine

FROM python:3.12
ARG VER

ADD ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

RUN pip install git+https://github.com/ICICLE-ai/ct-controller#@v${VER}


ENTRYPOINT ["./entrypoint.sh"]
