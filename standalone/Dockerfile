FROM alpine/helm:3 as base

WORKDIR /tmp

RUN apk add --no-cache wget && \
  if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "arm64" ]; then \
    wget https://github.com/k3s-io/k3s/releases/download/v1.29.9%2Bk3s1/k3s-arm64 -O /tmp/k3s; \
  else \
    wget https://github.com/k3s-io/k3s/releases/download/v1.29.9%2Bk3s1/k3s -O /tmp/k3s; \
  fi && \
  chmod +x /tmp/k3s

RUN git clone --depth=1 -b V6.0 https://github.com/goodrain/rainbond-chart.git && \
    helm package rainbond-chart && \
    mv rainbond-*.tgz rainbond-cluster.tgz

FROM alpine:3

COPY standalone/entrypoint.sh /entrypoint.sh
COPY standalone/config.yaml /etc/rancher/k3s/config.yaml
COPY standalone/registries.yaml /etc/rancher/k3s/registries.yaml
COPY rbd-images.tar /tmp/rbd-images.tar

COPY --from=base /tmp/k3s /bin/k3s
COPY --from=base /tmp/rainbond-cluster.tgz /tmp/rainbond-cluster.tgz

RUN apk add --no-cache iptables 

ENV CRI_CONFIG_FILE="/var/lib/rancher/k3s/agent/etc/crictl.yaml"
ENV KUBECONFIG=/etc/rancher/k3s/k3s.yaml

VOLUME /var/lib/rancher

ENTRYPOINT [ "/entrypoint.sh" ]

CMD [ "/bin/k3s", "server" ]