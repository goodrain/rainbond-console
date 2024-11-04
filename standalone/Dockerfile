FROM alpine/helm:3 as base
ARG TARGETARCH
WORKDIR /tmp

RUN apk add --no-cache wget && \
    if [ "$TARGETARCH" = "amd64" ]; then \
      wget https://github.com/k3s-io/k3s/releases/download/v1.30.4%2Bk3s1/k3s -O /tmp/k3s && chmod +x /tmp/k3s; \
    else \
      wget https://github.com/k3s-io/k3s/releases/download/v1.30.4%2Bk3s1/k3s-arm64 -O /tmp/k3s && chmod +x /tmp/k3s; \
    fi && \
    git clone --depth=1 -b V6-k3s https://github.com/goodrain/rainbond-chart.git && \
    helm package rainbond-chart && \
    mv rainbond-*.tgz rainbond-cluster.tgz

FROM ubuntu:24.04
ARG VERSION
ARG TARGETARCH

COPY standalone/entrypoint.sh /entrypoint.sh
COPY standalone/config.yaml /etc/rancher/k3s/config.yaml
COPY standalone/registries.yaml /etc/rancher/k3s/registries.yaml
COPY rbd-images-$TARGETARCH.tar /tmp/rbd-images.tar

COPY --from=base /tmp/rainbond-cluster.tgz /tmp/rainbond-cluster.tgz
COPY --from=base /tmp/k3s /bin/k3s

RUN apt-get update && apt -y install ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ENV VERSION=${VERSION}
ENV KUBECONFIG=/etc/rancher/k3s/k3s.yaml
ENV CRI_CONFIG_FILE="/opt/rainbond/k3s/agent/etc/crictl.yaml"

VOLUME /opt/rainbond

ENTRYPOINT [ "/entrypoint.sh" ]

CMD [ "/bin/k3s", "server" ]