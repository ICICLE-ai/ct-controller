# Image: tapis/camera_traps_engine

FROM python:3.12
ARG BRANCH

ADD ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

RUN if [[ -z "$BRANCH" ]]; then \
      pip install git+https://github.com/ICICLE-ai/ct-controller \
    else \
      pip install git+https://github.com/ICICLE-ai/ct-controller@${BRANCH} \
    fi

ENTRYPOINT ["./entrypoint.sh"]
