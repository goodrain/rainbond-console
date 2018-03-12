# -*- coding: utf8 -*-
"""
  Created on 18/1/25.
"""
import datetime


def time_to_str(time, fmt="%Y-%m-%d %H:%M"):
    return time.strftime(fmt)


def str_to_time(time_str, fmt="%Y-%m-%d %H:%M"):
    return datetime.datetime.strptime(time_str, fmt)


def current_time_str(fmt="%Y-%m-%d %H:%M"):
    return datetime.datetime.now().strftime(fmt)


def current_time():
    return datetime.datetime.now()


def current_time_to_str(fmt="%Y-%m-%d"):
    return datetime.datetime.now().strftime(fmt)
