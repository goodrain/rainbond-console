ARG IMAGE_NAMESPACE=rainbond
ARG VERSION=V5.4-dev

FROM golang:1.14-stretch as builder
ARG ADAPTOR_VERSION=v5.6.0-release
# ENV GOPROXY=https://goproxy.io
ENV CGO_ENABLED=1
ENV GOPATH=/go
ENV VERSION=${VERSION}
ARG DOMESTIC_NAMESPACE=goodrain
ENV DOMESTIC_NAMESPACE=${DOMESTIC_NAMESPACE}
RUN git clone -b ${ADAPTOR_VERSION} --depth=1 https://github.com/goodrain/cloud-adaptor /go/src/goodrain.com/cloud-adaptor
WORKDIR /go/src/goodrain.com/cloud-adaptor/
ARG LDFLAGS
RUN go build -ldflags "$LDFLAGS" -o /cloud-adaptor $PWD/cmd/cloud-adaptor

ARG IMAGE_NAMESPACE=rainbond
ARG VERSION=V5.4-dev

FROM ${IMAGE_NAMESPACE}/rainbond-ui:${VERSION}
ARG RELEASE_DESC=
ARG ARCH=amd64
ARG BRANCH=v2.3.0

LABEL author="zengqg@goodrain.com"
RUN mkdir -p /app/ui /usr/share/zoneinfo/Asia/ && \
    mkdir -p /opt/rainbond/ && \
    mkdir -p /var/lib/k3s/server/manifests/metrics-server/rainbond && \
	mkdir -p ~/.kube/ && \
    mkdir -p /app/logs/ && \
    touch /app/logs/init_rainbond_node.log && \
    touch /app/logs/init_rainbond_api.log && \
	apt-get update && apt-get install -y supervisor nfs-common iptables && rm -rf /var/lib/apt/lists/* && \
    set -eux; \
    if [ "${ARCH}" = "arm64" ]; then \
        wget "https://pkg.goodrain.com/pkg/helm-arm64" && chmod +x helm-arm64 && mv helm-arm64 /usr/local/bin/helm; \
    else \
        wget "https://pkg.goodrain.com/pkg/helm" && chmod +x helm && mv helm /usr/local/bin/; \
    fi && \
    mkdir -p /var/log/supervisor
# Distinguish download addresses according to the CPU architecture of the build environment
RUN set -eux; \
	case "${ARCH}" in \
		'amd64') \
			docker_url='https://download.docker.com/linux/static/stable/x86_64/docker-20.10.11.tgz'; \
            k3s_url="https://github.com/rancher/k3s/releases/download/v1.22.3+k3s1/k3s" \
            kubectl_url="https://storage.googleapis.com/kubernetes-release/release/v1.22.3/bin/linux/amd64/kubectl" \
			;; \
		'arm64') \
			docker_url='https://pkg.goodrain.com/pkg/docker-20.10.11.tgz'; \
            k3s_url="https://pkg.goodrain.com/pkg/k3s-arm64" \
            kubectl_url="https://pkg.goodrain.com/pkg/kubectl" \
			;; \
	esac \
    && wget -O docker.tgz "$docker_url" \
	&& tar xzf docker.tgz --strip-components 1 --directory /usr/local/bin/ \
	&& rm docker.tgz \
    && mkdir -p /etc/docker \
    && wget -O /usr/local/bin/k3s "$k3s_url" \
    && wget -O /usr/local/bin/kubectl "$kubectl_url" \
	&& chmod +x /usr/local/bin/kubectl /usr/local/bin/k3s \
	&& ln -s /etc/rancher/k3s/k3s.yaml ~/.kube/config
    

COPY --from=builder /go/src/goodrain.com/cloud-adaptor/chart /app/chart
COPY --from=builder /cloud-adaptor /app/cloudadaptor
ADD . /app/ui
WORKDIR /app/ui
ARG VERSION=V5.4-dev
ARG DOMESTIC_NAMESPACE=goodrain
ARG CLONE_URL=https://github.com/goodrain
RUN set -eux; \
    if [ "${ARCH}" = "arm64" ]; then \
        wget "https://pkg.rainbond.com/images-pkg/arm64/rainbond-v5.6.0.tar"; \
        wget "https://pkg.rainbond.com/images-pkg/arm64/log"; \
    else \
        wget "https://rainbond-pkg.oss-cn-shanghai.aliyuncs.com/images-pkg/rainbond-${VERSION}.tar"; \
        wget "https://pkg.rainbond.com/images-pkg/log"; \
    fi && \
    git clone -b ${BRANCH} --depth=1 ${CLONE_URL}/rainbond-operator.git /app/ui/rainbond-operator && \
    chmod +x /app/ui/entrypoint.sh /app/ui/start.sh /app/ui/k3s.sh  /app/ui/init_rainbond.sh && \
    mv /app/ui/supervisord.conf /etc/supervisor/supervisord.conf && \
    mv /app/ui/rainbond.conf /etc/supervisor/conf.d/rainbond.conf && \
    mv /app/ui/dind.conf /etc/supervisor/conf.d/dind.conf.bak && \
	mv /app/ui/daemon.json /etc/docker/daemon.json && \
	chmod +x /app/cloudadaptor && \
    mv /dist/index.html /app/ui/www/templates/index.html && \
    chmod +x /app/ui/log && mv /app/ui/log /usr/bin/log && \
    rm -rf /app/ui/www/static/dists && \
    mkdir /app/ui/www/static/dists && \
    cp -a /dist/* /app/ui/www/static/dists/ && \
    rm -rf /dist \
    && mkdir /app/data \
    && mkdir /root/.ssh \
    && python -m pip install --upgrade pip \
    && pip install -r requirements.txt \
    && python manage.py collectstatic --noinput --ignore weavescope-src --ignore drf-yasg  --ignore rest_framework\
    && rm -rf /root/.cache \
    && rm -rf /tmp/* \
    && rm -rf /app/ui/www/static/www/weavescope

ENV PORT 7070
ENV IS_OPEN_API=true
ENV RELEASE_DESC=${RELEASE_DESC}
ENV HOME_DIR=/app
# cloud adaptor
ENV DB_PATH=/app/data/cloudadaptor
ENV CHART_PATH=/app/chart
ENV CONFIG_DIR=/app/data/cloudadaptor
ENV HELM_PATH=/usr/local/bin/helm
ENV MYSQL_DB=console
ENV VERSION=${VERSION}
ENV RAINBOND_VERSION=${VERSION}
ENV OPERATOR_VERSION=${VERSION}
ENV DOMESTIC_NAMESPACE=${DOMESTIC_NAMESPACE}

VOLUME /app/data
VOLUME /app/logs
VOLUME /root/.ssh
VOLUME /opt/rainbond
VOLUME /var/lib/docker

ENTRYPOINT [ "/app/ui/start.sh" ]
CMD ["/usr/bin/supervisord","-c","/etc/supervisor/supervisord.conf"]
