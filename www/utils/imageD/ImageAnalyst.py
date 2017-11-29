#!/usr/bin/env python
# -*- coding: utf8 -*-

import re
import logging

logger = logging.getLogger('default')
IS_URL = "is_url"
IS_DOCKER = "is_docker"

MATCHRULE_ONE_ACROSS = "\s?-d\s[-+\w]?.*\s(-\w+\s\S+)\s(\S+)\s?(-.*)?"
#MATCHRULE_TWO_ACROSS = "\s?-d\s[-+\w]?.*\s(--\w+\s\S+)\s(\S+)\s?(-.*)?"
#MATCHRULE_TWO_ACROSS = "\s?-d\s[-+\w]?.*\s(--\w+\S+)\s(\S+)\s?(-.*)?"
MATCHRULE_TWO_ACROSS = "\s?-d\s[-+\w]?.*\s(--\w+[\s|==]\S+)\s(\S+)\s?(-.*)?"
MATCHRULE_CE = "\s?-d\s(\S+)\s?(-.*)?"

def analystImage(image_url):
    '''
    image_url = "hubimage/wrk:V2"
    image_url = "docker run -d -p 80:80 -p 9000:8080 -p 127.0.0.1:5000:5000 --expose=9000 --link config:config
                -e SERVICE_PASSWORD=root --name=example -v /home/test_volume/:/home/test --volumes-from dbdata
                goodraincloudframeworks/piggymetrics-statistics-service"
    '''
    DOCKER_RUN = "^docker run"
    rc_split = re.split(DOCKER_RUN, image_url, maxsplit=1)
    if 1 == len(rc_split):
        print IS_URL, [image_url], None
        return IS_DOCKER, [image_url], ""
    else:
        list_params = reString(rc_split[1]).split(" ")[1:]
        imagename, runArgs = matchString(reString(rc_split[1]))
        opts, args = _getopt(list_params, "p:v:e:", ["expose=", "link=", "volumes-from=", "name="])
        logger.debug("opts {}".format(args[-1]))
        opts = [(mm[0], (lambda x:x.split(":")[-1])(mm[1])) for mm in opts if mm[1]]
        #opts.append(args[-1])
        opts.append(imagename)
        return IS_DOCKER, opts, runArgs

class GetoptError(Exception):
    opt = ''
    msg = ''
    def __init__(self, msg, opt=''):
        self.msg = msg
        self.opt = opt
        Exception.__init__(self, msg, opt)

    def __str__(self):
        return self.msg

#error = GetoptError # backward compatibility
def reString(args):
    normalStr = re.sub("[\s|\\\]+", " ", args)
    logger.debug("normal str is {}".format(normalStr))
    return normalStr

def whetherAcross(imagename):
    # imagename 后期增加其他判断
    if str(imagename).startswith("-"):
        return False
    else:
        return True

def matchString(args):
    #matchObj = re.match(r"\s?-d\s.*(-\w+\s\S+\s)(\S+)\s(.*)", args)
    if re.match(r"\s?-d\s-+", args):
        #print "match rule is {}".format(MATCHRULE_ONE_ACROSS)
        matchObj = re.match(MATCHRULE_ONE_ACROSS, args)
        if matchObj:
            logger.debug("match group 2 images name is {}".format(matchObj.group(2)))
            if whetherAcross(matchObj.group(2)):
                return matchObj.group(2), matchObj.group(3)
            else:
                matchObj = re.match(MATCHRULE_TWO_ACROSS, args)
                if matchObj:
                    logger.debug("match group2 images name is {}".format(matchObj.group(2)))
                    logger.debug("match group3 is {}".format(matchObj.group(3)))
                    if whetherAcross(matchObj.group(2)):
                        return matchObj.group(2), matchObj.group(3)
                    else:
                        return "", ""
        else:
            matchObj = re.match(MATCHRULE_TWO_ACROSS, args)
            if matchObj:
                logger.debug("match group2 images name is {}".format(matchObj.group(2)))
                logger.debug("match group3 is {}".format(matchObj.group(3)))
                if whetherAcross(matchObj.group(2)):
                    return matchObj.group(2), matchObj.group(3)
                else:
                    return "", ""
            else:
                #print "处理异常。需要添加 -d 参数，此处只能运行后台模式的容器，或者正确格式的镜像名称"
                logger.debug("matchstring exec errors  -d")
                return "", ""
    else:
        matchObj = re.search(MATCHRULE_CE, args)
        if matchObj:
            logger.debug("match group 1 images name is {}".format(matchObj.group(1)))
            print matchObj.group(1), matchObj.group(2)
            return matchObj.group(1), matchObj.group(2)
        else:
            return "", ""


def _getopt(args, shortopts, longopts = []):
    opts = []
    if type(longopts) == type(""):
        longopts = [longopts]
    else:
        longopts = list(longopts)
    while args and args[0].startswith('-') and args[0] != '-':
        if args[0] == '--':
            args = args[1:]
            break
        if args[0].startswith('--'):
            opts, args = do_longs(opts, args[0][2:], longopts, args[1:])
        else:
            opts, args = do_shorts(opts, args[0][1:], shortopts, args[1:])

    return opts, args

def gnu_getopt(args, shortopts, longopts = []):
    opts = []
    prog_args = []
    if isinstance(longopts, str):
        longopts = [longopts]
    else:
        longopts = list(longopts)

    # Allow options after non-option arguments?
    #if shortopts.startswith('+'):
    #    shortopts = shortopts[1:]
    #    all_options_first = True
    #elif os.environ.get("POSIXLY_CORRECT"):
    #    all_options_first = True
    #else:
    all_options_first = False

    while args:
        if args[0] == '--':
            prog_args += args[1:]
            break

        if args[0][:2] == '--':
            opts, args = do_longs(opts, args[0][2:], longopts, args[1:])
        elif args[0][:1] == '-' and args[0] != '-':
            opts, args = do_shorts(opts, args[0][1:], shortopts, args[1:])
        else:
            if all_options_first:
                prog_args += args
                break
            else:
                prog_args.append(args[0])
                args = args[1:]

    return opts, prog_args

def do_longs(opts, opt, longopts, args):
    try:
        i = opt.index('=')
    except ValueError:
        optarg = None
    else:
        opt, optarg = opt[:i], opt[i+1:]

    has_arg, opt = long_has_args(opt, longopts)
    if has_arg:
        if optarg is None:
            if not args:
                raise GetoptError('option --%s requires argument' % opt, opt)
            optarg, args = args[0], args[1:]
    elif optarg is not None:
        raise GetoptError('option --%s must not have an argument' % opt, opt)
    opts.append(('--' + opt, optarg or ''))
    return opts, args

def long_has_args(opt, longopts):
    possibilities = [o for o in longopts if o.startswith(opt)]
    if possibilities:
        #raise GetoptError('option --%s not recognized' % opt, opt)
        if opt in possibilities:
            return False, opt
        elif opt + '=' in possibilities:
            return True, opt
        # No exact match, so better be unique.
        if len(possibilities) > 1:
            raise GetoptError('option --%s not a unique prefix' % opt, opt)
        assert len(possibilities) == 1
        unique_match = possibilities[0]
        has_arg = unique_match.endswith('=')
        if has_arg:
            unique_match = unique_match[:-1]
        return has_arg, unique_match
    else:
        # 不存在的opt直接返回
        return opt, opt

def do_shorts(opts, optstring, shortopts, args):
    while optstring != '':
        opt, optstring = optstring[0], optstring[1:]
        if short_has_arg(opt, shortopts):
            if optstring == '':
                if not args:
                    raise GetoptError('option -%s requires argument' % opt,
                                      opt)
                optstring, args = args[0], args[1:]
            optarg, optstring = optstring, ''
        else:
            optarg = ''
        opts.append(('-' + opt, optarg))
    return opts, args

def short_has_arg(opt, shortopts):
    for i in range(len(shortopts)):
        if opt == shortopts[i] != ':':
            return shortopts.startswith(':', i+1)
        else:
            # 不存在的短opt直接返回
            pass
    #raise GetoptError('option -%s not recognized' % opt, opt)

if __name__ == '__main__':
    image = "hubimage/wrk:V2"
    image1 = "docker run -d docker"
    image2 = "docker run -d -e CONFIG_SERVICE_PASSWORD=${CONFIG_SERVICE_PASSWORD} -e STATISTICS_SERVICE_PASSWORD=${STATISTICS_SERVICE_PASSWORD} -e MONGODB_PASSWORD=${MONGODB_PASSWORD} --link config:config --link statistics-mongodb:statistics-mongodb --link registry:registry --link auth-service:auth-service --link rabbitmq:rabbitmq --name=statistics-service goodraincloudframeworks/piggymetrics-statistics-service"
    image3 = "docker run -d -p 90:90 -p 9000:8080 -p 127.0.0.1:5000:5000 --expose=9000 --link config " \
             "-e SERVICE_PASSWORD=root --name=example -v /home/test_volume/:/home/test --volumes-from dbdata " \
             "-e PASS=root goodraincloudframeworks/piggymetrics-statistics-service"

    image4 = "docker run    -d  -p 80 -p   9000:8080 -p 127.0.0.1:5000:5000 \   -p 2333:2333 --name piggy_test -e PASSWD=root piggymetrics -name etcd0"
    image5 = "docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -p 4001:4001 -p 2380:2380 -p 2379:2379 \  --name etcd quay.io/coreos/etcd:v2.3.8 \  -name etcd0 \  -advertise-client-urls http://192.168.12.50:2379,http://192.168.12.50:4001 \  -listen-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001 \  -initial-advertise-peer-urls http://192.168.12.50:2380 \  -listen-peer-urls http://0.0.0.0:2380 \  -initial-cluster-token etcd-cluster-1 \  -initial-cluster etcd0=http://192.168.12.50:2380,etcd1=http://192.168.12.51:2380,etcd2=http://192.168.12.52:2380 \  -initial-cluster-state new"
    image6 = "docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -p 4001:4001 -p 2380:2380 -p 2379:2379 \  --name etcd quay.io/coreos/etcd:v2.3.8"
    image7 = "docker run -d --shm-size=1g --rm -v /isisi:/sitespeed.io sitespeedio/sitespeed.io:X.Y.Z -b chrome https://www.sitespeed.io/"
    # image7 不支持
    image8 = "docker run -d nginx:1.11"
    image9 = "docker run --name some-app --link some-cassandra:cassandra -d app-that-uses-cassandra"
    image10 = "docker run -d -p15672:15672 --name=rabbitmq rabbitmq:3-management"
    _is, list_args, run_execs = analystImage(image)
    args = ""
    for mm in list_args[:-1]:
        if args:
            args = "{0}^_^{1}=={2}".format(args, mm[0], mm[1])
        else:
            args = "{0}=={1}".format(mm[0], mm[1])
            if args:
                args += "^_^{0}=={1}^_^{2}=={3}".format("image", list_args[-1], "run_exec", run_execs)
            else:
                args = "{0}=={1}^_^{2}=={3}".format("image", list_args[-1], "run_exec", run_execs)
    import base64
    args64 = base64.b64encode(args)
    print args64
    print len(args64)
    print base64.b64decode(args64)

    #print regex.sub(lambda m: '[' + m.group(0) + ']', text)
