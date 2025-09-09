# Image: tapis/camera_traps_engine

FROM python:3.12
ARG BRANCH

RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update && apt-get install -y docker.io docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

ADD ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ADD build_from_repo.sh /build_from_repo.sh
RUN /build_from_repo.sh && rm /build_from_repo.sh

ENTRYPOINT ["./entrypoint.sh"]
