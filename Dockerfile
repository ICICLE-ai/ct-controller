# Image: tapis/camera_traps_engine

FROM python:3.12
ARG VER

ADD dist/ctcontroller-${VER}-py3-none-any.whl /
ADD ./entrypoint.sh /entrypoint.sh
ADD ./inputs /inputs

RUN chmod +x /entrypoint.sh

RUN pip install /ctcontroller-${VER}-py3-none-any.whl
RUN rm /ctcontroller-${VER}-py3-none-any.whl


ENTRYPOINT ["./entrypoint.sh"]
