ARG IMAGE_NAMESPACE=rainbond
ARG VERSION=v6.0.0-release
ARG IMAGE_VERSION=v6.0.0-release
# Python base images, overridable to a mirror (e.g. GHCR) to avoid Docker Hub
# pull-rate limits in CI. Defaults keep pulling from Docker Hub (release builds
# unchanged); dev-build overrides these to a mirror via --build-arg.
ARG PYTHON_BASE=python:3.11-bookworm
ARG PYTHON_SLIM_BASE=python:3.11-slim-bookworm

# Fetch static UI assets independently of Python dependencies.
FROM ${IMAGE_NAMESPACE}/rainbond-ui:${IMAGE_VERSION} AS ui

# Build a stable Python environment independently of application/UI files.
FROM ${PYTHON_BASE} AS dependencies
ARG PYTHONPROXY
WORKDIR /app/ui
ENV PATH="/app/ui/py_venv/bin:$PATH"

# Code and UI changes must not invalidate the installed Python dependencies.
COPY requirements.txt ./
RUN python -m venv --copies /app/ui/py_venv && \
    python -m pip install --no-cache-dir --upgrade pip 'setuptools<70' && \
    pip install --no-cache-dir -r requirements.txt $PYTHONPROXY

COPY scripts/install_openapi_client.sh scripts/install_openapi_client.sh
RUN bash scripts/install_openapi_client.sh --no-cache-dir $PYTHONPROXY
RUN find /app/ui/py_venv/lib/python3.11/site-packages -depth -type d \( -name __pycache__ -o -name tests \) -exec rm -rf {} + && \
    find /app/ui/py_venv -name '*.pyc' -delete

# Helm also stays stable when only the application version changes.
ARG TARGETARCH
RUN wget https://get.helm.sh/helm-v3.16.2-linux-$TARGETARCH.tar.gz -O /tmp/helm.tar.gz && \
    tar -zxvf /tmp/helm.tar.gz -C /tmp && \
    mv /tmp/linux-$TARGETARCH/helm /tmp && \
    chmod +x /tmp/helm

FROM dependencies AS build-console
COPY . /app/ui
COPY --from=ui /dist /tmp/ui-dist
RUN mv /tmp/ui-dist/index.html /app/ui/www/templates/index.html && \
    rm -rf /app/ui/www/static/dists && \
    mkdir -p /app/ui/www/static/dists && \
    cp -a /tmp/ui-dist/. /app/ui/www/static/dists/ && \
    rm -rf /tmp/ui-dist && \
    python manage.py collectstatic --link --noinput --ignore weavescope-src --ignore drf-yasg --ignore rest_framework && \
    python -m whitenoise.compress --no-brotli static/ && \
    python -m whitenoise.compress --no-brotli www/static/ && \
    rm -rf /app/ui/py_venv

# Keep assets out of the application layer as well. Collected files link to
# their original paths, which are preserved in the runtime image below.
RUN mkdir -p /tmp/runtime-static && \
    mv /app/ui/static /tmp/runtime-static/collected && \
    mv /app/ui/www/static /tmp/runtime-static/source

ARG VERSION
RUN git clone --depth=1 -b main https://github.com/goodrain/rainbond-chart /app/ui/rainbond-chart && \
    rm -rf /app/ui/rainbond-chart/.git && \
    sed -i "s/installVersion: .*/installVersion: $VERSION/" /app/ui/rainbond-chart/values.yaml

# build console image
FROM ${PYTHON_SLIM_BASE}

# OS packages are independent of source code and release metadata.
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
	echo 'Asia/Shanghai' >/etc/timezone && \
	apt-get update && apt-get --no-install-recommends install -y \
	curl mariadb-client sqlite3 libmariadb3 \
	libjpeg62-turbo libfreetype6 libpng16-16 zlib1g liblcms2-2 libwebp7 libtiff6 libopenjp2-7 libxcb1 && \
  mkdir -p /app/logs /app/data && \
	rm -rf /var/lib/apt/lists/*

ARG RELEASE_DESC=
ARG VERSION
ARG RAINBOND_ERROR_REPORTING_DSN=
ARG RAINBOND_ERROR_REPORTING_CONSOLE_DSN=
ARG RAINBOND_ERROR_REPORTING_BACKEND_DSN=
ARG RAINBOND_ERROR_REPORTING_FRONTEND_TUNNEL=/console/sentry
ARG RAINBOND_SENTRY_PROXY_TARGET=https://sentry.goodrain.com
ARG RAINBOND_POSTHOG_API_HOST=/console/posthog
ARG RAINBOND_POSTHOG_UI_HOST=https://posthog.goodrain.com
ARG RAINBOND_POSTHOG_PROXY_TARGET=https://posthog.goodrain.com
ARG RAINBOND_POSTHOG_ASSET_PROXY_TARGET=https://posthog.goodrain.com

# Copy dependencies before application files so code/UI/version updates keep
# the large dependency blob unchanged in both registries.
COPY --from=dependencies /tmp/helm /usr/local/bin/helm
COPY --from=dependencies /app/ui/py_venv /app/ui/py_venv
COPY --from=build-console /tmp/runtime-static/source /app/ui/www/static
COPY --from=build-console /tmp/runtime-static/collected /app/ui/static
COPY --from=build-console /app/ui /app/ui
WORKDIR /app/ui

ENV PATH=/app/ui/py_venv/bin:$PATH
ENV PORT 7070
ENV IS_OPEN_API=true
ENV RELEASE_DESC=${RELEASE_DESC}
ENV HOME_DIR=/app
ENV RAINBOND_ERROR_REPORTING_DSN=${RAINBOND_ERROR_REPORTING_DSN}
ENV RAINBOND_ERROR_REPORTING_FRONTEND_DSN=https://dec2adb7a6a5451ca440dc1c7c9d583a@sentry.goodrain.com/2
ENV RAINBOND_ERROR_REPORTING_CONSOLE_DSN=${RAINBOND_ERROR_REPORTING_CONSOLE_DSN}
ENV RAINBOND_ERROR_REPORTING_BACKEND_DSN=${RAINBOND_ERROR_REPORTING_BACKEND_DSN}
ENV RAINBOND_ERROR_REPORTING_FRONTEND_TUNNEL=${RAINBOND_ERROR_REPORTING_FRONTEND_TUNNEL}
ENV RAINBOND_SENTRY_PROXY_TARGET=${RAINBOND_SENTRY_PROXY_TARGET}
ENV RAINBOND_POSTHOG_API_HOST=${RAINBOND_POSTHOG_API_HOST}
ENV RAINBOND_POSTHOG_UI_HOST=${RAINBOND_POSTHOG_UI_HOST}
ENV RAINBOND_POSTHOG_PROXY_TARGET=${RAINBOND_POSTHOG_PROXY_TARGET}
ENV RAINBOND_POSTHOG_ASSET_PROXY_TARGET=${RAINBOND_POSTHOG_ASSET_PROXY_TARGET}

VOLUME /app/data
VOLUME /app/logs

EXPOSE 7070

CMD [ "bash", "/app/ui/entrypoint.sh" ]
