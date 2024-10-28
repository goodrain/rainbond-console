FROM alpine/helm:3 as base
ARG TARGETARCH
WORKDIR /tmp

RUN apk add --no-cache wget && \
    wget https://cdn.dl.k8s.io/release/v1.30.4/bin/linux/$TARGETARCH/kubectl -O /tmp/kubectl && chmod +x /tmp/kubectl && \
    git clone --depth=1 -b V6-dind https://github.com/goodrain/rainbond-chart.git && \
    helm package rainbond-chart && \
    mv rainbond-*.tgz rainbond-cluster.tgz

FROM rancher/k3s:v1.30.4-k3s1

COPY standalone/entrypoint.sh /entrypoint.sh
COPY standalone/config.yaml /etc/rancher/k3s/config.yaml
COPY standalone/registries.yaml /etc/rancher/k3s/registries.yaml
COPY rbd-images.tar /tmp/rbd-images.tar

# COPY --from=base /tmp/kubectl /bin/kubectl
COPY --from=base /tmp/rainbond-cluster.tgz /tmp/rainbond-cluster.tgz

ENV CRI_CONFIG_FILE="/var/lib/rancher/k3s/agent/etc/crictl.yaml"
ENV KUBECONFIG=/etc/rancher/k3s/k3s.yaml

VOLUME /var/lib/rancher

ENTRYPOINT [ "/entrypoint.sh" ]

CMD [ "/bin/k3s", "server" ]