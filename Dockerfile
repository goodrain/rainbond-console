ARG VERSION=V5.3-dev
ARG RELEASE_DESC=

FROM rainbond/rbd-ui-base:${VERSION}

LABEL author="zengqg@goodrain.com" 

RUN mkdir -p /app/ui /usr/share/zoneinfo/Asia/

ADD . /app/ui

WORKDIR /app/ui

RUN chmod +x /app/ui/entrypoint.sh \
      && mkdir /app/logs \
      && mkdir /app/data \
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

VOLUME /app/data
VOLUME /app/logs

ENTRYPOINT ["./entrypoint.sh"]
