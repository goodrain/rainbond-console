#!/usr/bin/env python
# -*- coding: utf8 -*-

import re

IS_URL = "is_url"
IS_DOCKER = "is_docker"

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
        return IS_URL, [image_url]
    else:
        list_params=rc_split[1].split(" ")[1:]
        opts, args = _getopt(list_params, "p:v:e:", ["expose=", "link=", "volumes-from=", "name="])
        opts = [(mm[0], (lambda x:x.split(":")[-1])(mm[1])) for mm in opts[:-1] if mm[1]]
        opts.append(args[-1])
        return IS_DOCKER, opts

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
    image1 = "daf docker run docker"
    image2 = "docker run -m -it -d -p 80 -p 9000:8080 -p 127.0.0.1:5000:5000 --va=test piggymetrics"
    image3 = "docker run -d -p 90:90 -p 9000:8080 -p 127.0.0.1:5000:5000 --expose=9000 --link config " \
             "-e SERVICE_PASSWORD=root --name=example -v /home/test_volume/:/home/test --volumes-from dbdata " \
             "-e PASS=root goodraincloudframeworks/piggymetrics-statistics-service"
    _is, list_args = analystImage(image3)
    print _is
    print list_args
    print list_args[-1]
    print list_args[:-1]
    args = ""
    for mm in list_args[:-1]:
        if args:
            args = "{0}^_^{1}={2}".format(args, mm[0], mm[1])
        else:
            args = "{0}={1}".format(mm[0], mm[1])

    import base64
    args64 = base64.b64encode(args)
    print args64
    print base64.b64decode(args64)

    #print regex.sub(lambda m: '[' + m.group(0) + ']', text)
