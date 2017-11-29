# =========================================================================
# Copyright 2012-present Yunify, Inc.
# -------------------------------------------------------------------------
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this work except in compliance with the License.
# You may obtain a copy of the License in the LICENSE file, or at:
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========================================================================

import time
import base64


def get_utf8_value(value):
    try:
        return value.encode('utf-8')
    except:
        return str(value)


ISO8601 = '%Y-%m-%dT%H:%M:%SZ'
ISO8601_MS = '%Y-%m-%dT%H:%M:%S.%fZ'


def get_ts(ts=None):
    """ Get formatted time
    """
    if not ts:
        ts = time.gmtime()
    return time.strftime(ISO8601, ts)


def encode_base64(content):
    try:
        base64str = base64.standard_b64encode(content)
        return base64str
    except Exception:
        return ''


def decode_base64(base64str):
    try:
        decodestr = base64.standard_b64decode(base64str)
        return decodestr
    except Exception:
        return ''


def base64_url_decode(inp):
    return base64.urlsafe_b64decode(str(inp + '=' * (4 - len(inp) % 4)))


def base64_url_encode(inp):
    return base64.urlsafe_b64encode(str(inp)).rstrip('=')
