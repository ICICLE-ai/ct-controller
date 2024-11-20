# Image: tapis/camera_traps_engine

FROM python:3.12
ARG BRANCH

ADD ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ADD build_from_repo.sh
RUN ./build_from_repo.sh && rm ./build_from_repo.sh

ENTRYPOINT ["./entrypoint.sh"]
