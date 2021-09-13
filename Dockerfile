ARG BASE_VERSION=V5.3
FROM rainbond/rbd-ui-base:${BASE_VERSION}

ARG RELEASE_DESC=
ARG PIP_SOURCE_URL=http://mirrors.aliyun.com/pypi/simple
ARG PIP_SOURCE_HOST=mirrors.aliyun.com

LABEL author="zengqg@goodrain.com" 

RUN mkdir -p /app/ui /usr/share/zoneinfo/Asia/

ADD . /app/ui

WORKDIR /app/ui

RUN chmod +x /app/ui/entrypoint.sh \
      && mkdir /app/logs \
      && mkdir /app/data \
      && pip config set global.index-url "$PIP_SOURCE_URL" \
      && pip config set install.trusted-host "$PIP_SOURCE_HOST" \
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
ENV MYSQL_DB=console

VOLUME /app/data
VOLUME /app/logs

ENTRYPOINT ["./entrypoint.sh"]