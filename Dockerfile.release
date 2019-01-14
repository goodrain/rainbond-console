FROM rainbond/rainbond-ui:VERSION

MAINTAINER zhengys@goodrain.com

RUN mkdir -p /app/ui /usr/share/zoneinfo/Asia/

ADD . /app/ui

WORKDIR /app/ui

RUN chmod +x /app/ui/entrypoint.sh &&  \
    cp /app/ui/hack/Shanghai /usr/share/zoneinfo/Asia/Shanghai && \
    mv /dist/index.html /app/ui/www/templates/index.html && \
    rm -rf /app/ui/www/static/dists/* && \
    cp -a /dist/* /app/ui/www/static/dists/ && \
    rm -rf /dist

RUN apk update && apk --no-cache add --virtual .build-deps \
      build-base \
      gcc \
      libmemcached \
      libmemcached-dev \
      zlib-dev \
      cyrus-sasl \
      cyrus-sasl-dev \
      libc-dev \
      libffi-dev \
      mariadb-dev \
	mariadb-client-libs \
      freetype-dev \
      libpng-dev \
      libjpeg-turbo-dev \
      py-mysqldb \
      && mkdir /app/logs \
      && pip install -r requirements.txt \
      && cp -a /usr/lib/libmysqlclient.so.18* /tmp/ \
      && cp -a /usr/lib/libmemcached* /tmp/ \
      && cp -a /usr/lib/libsas* /tmp/ \
      && cp -a /usr/lib/libjpeg* /tmp/ \
      && apk del .build-deps \
      && cp -a /tmp/lib* /usr/lib/ \
      && python manage.py collectstatic --noinput \
      && rm -rf /root/.cache \
      && rm -rf /tmp/* \
      && rm -rf /app/ui/www/static/www/weavescope

ENV PORT 7070

ENV RELEASE_DESC=__RELEASE_DESC__

VOLUME /initdata
VOLUME /app/logs

ENTRYPOINT ["./entrypoint.sh"]

