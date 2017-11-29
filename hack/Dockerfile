FROM alpine:3.6
MAINTAINER qisy@goodrain.com

RUN apk --no-cache add tzdata bash libstdc++
ENV TZ Asia/Shanghai

RUN adduser -u 200 -D -S -s /bin/bash rain

ENV PORT 7070
ENV REGION_TAG cloudbang

ADD entrypoint.sh /entrypoint.sh
ADD app /app

#USER rain
WORKDIR /app
ENV RELEASE_DESC=__RELEASE_DESC__

ENTRYPOINT ["/entrypoint.sh"]
