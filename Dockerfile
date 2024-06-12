FROM python:alpine as build-stage

# Official Python base image is needed or some applications will segfault.
# PyInstaller needs zlib-dev, gcc, libc-dev, and musl-dev
RUN apk --update --no-cache add \
    zlib-dev \
    musl-dev \
    libc-dev \
    gcc \
    g++ \
    git \
    make \
    cmake \
    upx && \
    # update pip
    pip install --upgrade pip

ADD requirements.txt /tmp/requirements.txt
ADD src/ /tmp/app/
RUN pip install pyinstaller && \
    pip install -r /tmp/requirements.txt && \
    cd /tmp/app/ && \
    pyinstaller \
        -n chips \
        --onefile main.py \
        --python-option u \
        --hidden-import config.py \
        --hidden-import stbmock.py \
        --hidden-import storage.py \
        --hidden-import utils.py
ADD config_template /tmp/app/dist/config.template
ADD docker-entrypoint.sh /tmp/app/dist/docker-entrypoint.sh
RUN chmod +x -R /tmp/app/dist

FROM alpine:latest

LABEL maintainer="VergilGao"
LABEL org.opencontainers.image.source="https://github.com/VergilGao/Telecom-IPTV-Mock"

ENV TZ="Asia/Shanghai"
ENV UID=99
ENV GID=100
ENV UMASK=002
ENV CRONTAB="0 1 * * *"

RUN apk add --no-cache --update \
      coreutils \
      shadow \
      cronie \
      su-exec && \
    rm -rf /var/cache/apk/* && \
    mkdir -p /app && \
    mkdir -p /data && \
    mkdir -p /config && \
    useradd -d /config -s /bin/sh abc && \
    chown -R abc /config && \
    chown -R abc /data

COPY --from=build-stage /tmp/app/dist/ /app/

VOLUME [ "/data", "/config" ]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
