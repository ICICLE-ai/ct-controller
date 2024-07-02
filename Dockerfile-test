# Image: tapis/camera_traps_engine

FROM python:3.12
ARG VER

ADD ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ADD dist/ctcontroller-${VER}-py3-none-any.whl /
RUN pip install /ctcontroller-${VER}-py3-none-any.whl \
    && rm /ctcontroller-${VER}-py3-none-any.whl


ENTRYPOINT ["./entrypoint.sh"]
