FROM alpine/helm:3 as base
ARG TARGETARCH
WORKDIR /tmp

RUN apk add --no-cache wget && \
    wget https://cdn.dl.k8s.io/release/v1.30.4/bin/linux/$TARGETARCH/kubectl -O /tmp/kubectl && chmod +x /tmp/kubectl && \
    if [ "$TARGETARCH" = "amd64" ]; then \
      wget https://github.com/k3s-io/k3s/releases/download/v1.30.4%2Bk3s1/k3s -O /tmp/k3s; \
    else \
      wget https://github.com/k3s-io/k3s/releases/download/v1.30.4%2Bk3s1/k3s-arm64 -O /tmp/k3s; \
    fi && \
    git clone --depth=1 -b V6-dind https://github.com/goodrain/rainbond-chart.git && \
    helm package rainbond-chart && \
    mv rainbond-*.tgz rainbond-cluster.tgz

FROM ubuntu:24.04

COPY standalone/entrypoint.sh /entrypoint.sh
COPY standalone/config.yaml /etc/rancher/k3s/config.yaml
COPY standalone/registries.yaml /etc/rancher/k3s/registries.yaml
COPY rbd-images.tar /tmp/rbd-images.tar

COPY --from=base /tmp/rainbond-cluster.tgz /tmp/rainbond-cluster.tgz
COPY --from=base /tmp/k3s /bin/k3s

ENV KUBECONFIG=/etc/rancher/k3s/k3s.yaml

VOLUME /opt/rainbond

ENTRYPOINT [ "/entrypoint.sh" ]

CMD [ "/bin/k3s", "server" ]