FROM python:2.7.8

MAINTAINER zhengys@goodrain.com

RUN echo "Asia/Shanghai" > /etc/timezone;dpkg-reconfigure -f noninteractive tzdata

RUN mkdir -p /app/ui

WORKDIR /app/ui

ADD sources.list  /etc/apt/sources.list
ADD . /app/ui
RUN chmod +x /app/ui/entrypoint.sh
RUN apt-get update && apt-get install -y libmemcached-dev zlib1g-dev python-zmq && rm -r /var/lib/apt/lists/*

RUN pip install -r requirements.txt -i https://mirrors.ustc.edu.cn/pypi/web/simple

ENV PORT 7070 
ENV REGION_TAG cloudbang

ENV RELEASE_DESC=__RELEASE_DESC__

ENTRYPOINT ["/app/ui/entrypoint.sh"]
