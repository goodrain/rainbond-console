ARG IMAGE_NAMESPACE=rainbond
ARG VERSION=v6.0.0-release

# build ui
FROM ${IMAGE_NAMESPACE}/rainbond-ui:${VERSION} AS ui

ADD . /app/ui
WORKDIR /app/ui

RUN mv /dist/index.html /app/ui/www/templates/index.html && \
    rm -rf /app/ui/www/static/dists && \
    mkdir -p /app/ui/www/static/dists  && \
    cp -a /dist/* /app/ui/www/static/dists/

# build console
FROM python:3.6-stretch AS build-console
ARG PYTHONPROXY
ARG TARGETARCH
ARG VERSION

COPY --from=ui /app/ui /app/ui
WORKDIR /app/ui
ENV PATH="/app/ui/py_venv/bin:$PATH"

RUN python -m venv --copies /app/ui/py_venv && \
    python -m pip install --upgrade pip && pip install numpy==1.19.3 && \
    pip install -r requirements.txt $PYTHONPROXY && \
    python manage.py collectstatic --noinput --ignore weavescope-src --ignore drf-yasg --ignore rest_framework

RUN git clone --depth=1 -b main https://github.com/goodrain/rainbond-chart /app/ui/rainbond-chart && \
    sed -i "s/installVersion: .*/installVersion: $VERSION/" /app/ui/rainbond-chart/values.yaml && \
    wget https://get.helm.sh/helm-v3.16.2-linux-$TARGETARCH.tar.gz -O /tmp/helm.tar.gz && \
    tar -zxvf /tmp/helm.tar.gz -C /tmp && \
    mv /tmp/linux-$TARGETARCH/helm /tmp && \
    chmod +x /tmp/helm

# build console image
FROM python:3.6-slim-stretch

ARG RELEASE_DESC=
ARG VERSION

COPY --from=build-console /app/ui /app/ui
COPY --from=build-console /tmp/helm /usr/local/bin/helm
WORKDIR /app/ui

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
	echo 'Asia/Shanghai' >/etc/timezone && \
	echo "deb http://archive.debian.org/debian/ stretch main" > /etc/apt/sources.list && \
	echo "deb http://archive.debian.org/debian-security stretch/updates main" >> /etc/apt/sources.list && \
	apt-get update && apt-get --no-install-recommends install -y \
	curl mysql-client sqlite3 default-libmysqlclient-dev && \
  mkdir -p /app/logs /app/data && \
	rm -rf /var/lib/apt/lists/*

ENV PATH=/app/ui/py_venv/bin:$PATH
ENV PORT 7070
ENV IS_OPEN_API=true
ENV RELEASE_DESC=${RELEASE_DESC}
ENV HOME_DIR=/app

VOLUME /app/data
VOLUME /app/logs

EXPOSE 7070

CMD [ "bash", "/app/ui/entrypoint.sh" ]
