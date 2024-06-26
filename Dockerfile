# Image: tapis/camera_traps_engine

FROM python:3.12

ADD dist/ctcontroller-0.1-py3-none-any.whl /
ADD ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

RUN pip install /ctcontroller-0.1-py3-none-any.whl
RUN rm /ctcontroller-0.1-py3-none-any.whl


ENTRYPOINT ["./entrypoint.sh"]
