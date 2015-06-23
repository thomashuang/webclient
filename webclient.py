#!/usr/bin/env python
# Copyright (C) 2015 Thomas Huang
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#!/usr/bin/env python


"""The module provides the HTTP/HTTPS Client class,
it can handle the http(s) request and return the response and other response property access unities
"""


import sys
import urllib2
import base64
from json import loads



__version__ = "0.1.0"

PY_MAJOR = sys.version_info[0]
PY_MINOR = sys.version_info[1]
PY2 = PY_MAJOR == 2

if PY2:  # pragma: nocover

    from cStringIO import StringIO as BytesIO
    from Cookie import SimpleCookie  # noqa
else:  # pragma: nocover
    from io import BytesIO
    from http.cookies import SimpleCookie


GzipFile = __import__('gzip', None, None, ['GzipFile']).GzipFile

if PY2 and PY_MINOR < 7:  # pragma: nocover
    __saved_GzipFile__ = GzipFile

    def GzipFile(filename=None, mode=None, compresslevel=9,
                 fileobj=None, mtime=None):
        return __saved_GzipFile__(filename, mode, compresslevel,
                                  fileobj)


if PY2:

    from httplib import HTTPConnection  # noqa
    from httplib import HTTPSConnection  # noqa
    from urllib import urlencode  # noqa
    from urlparse import urljoin  # noqa
    from urlparse import urlsplit  # noqa
    from urlparse import urlunsplit  # noqa

else:
    from http.client import HTTPConnection
    from http.client import HTTPSConnection
    from urllib.parse import urlencode
    from urllib.parse import urljoin
    from urllib.parse import urlsplit
    from urllib.parse import urlunsplit


import socket
import ssl


class VerifyHttpsConnection(HTTPSConnection):

    """ Class to make a HTTPS connection, with support for full client-based SSL Authentication"""

    def __init__(self, host, port, key_file, cert_file, ca_file, timeout=None):
        HTTPSConnection.__init__(self, host, key_file=key_file, cert_file=cert_file)
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_file = ca_file
        self.timeout = timeout

    def connect(self):
        """ Connect to a host on a given (SSL) port.
            If ca_file is pointing somewhere, use it to check Server Certificate.
            Redefined/copied and extended from httplib.py:1105 (Python 2.6.x).
            This is needed to pass cert_reqs=ssl.CERT_REQUIRED as parameter to ssl.wrap_socket(),
            which forces SSL to check server certificate against our client certificate.
        """
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # If there's no CA File, don't force Server Certificate Check
        if self.ca_file:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        ca_certs=self.ca_file, cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, cert_reqs=ssl.CERT_NONE)


def compress(data, compresslevel=9):
    """ Compress data in one shot.
    """
    s = BytesIO()
    f = GzipFile(fileobj=s, mode='wb', mtime=0)
    f.write(data)
    f.close()
    return s.getvalue()


def decompress(data):
    """ Decompress data in one shot.
    """
    return GzipFile(fileobj=BytesIO(data), mode='rb').read()


class lazy_attr(object):

    def __init__(self, wrapped):
        self.wrapped = wrapped
        try:
            self.__doc__ = wrapped.__doc__
        except:  # pragma: no cover
            pass

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val


class WebClient(object):

    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36',
        'Accept-Encoding': 'gzip',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    def __init__(self, url, headers=None, auth=None, ca=None):
        scheme, uri, path, query, fragment = urlsplit(url)
        http_class = scheme == 'http' and HTTPConnection or HTTPSConnection
        self.connection = http_class(uri)
        self.default_headers = self.DEFAULT_HEADERS.copy()

        if headers:
            self.default_headers.update(headers)
        self.path = path
        self.headers = {}
        self.cookies = {}
        self.etags = {}
        self.status_code = 0
        self.body = None
        self.__content = None
        self.__json = None

        self.auth = auth
        # todo: add ca handle
        #self.ca = ca

    def ajax(self, method, path, **kwargs):
        """ GET HTTP AJAX request."""
        headers = headers or {}
        headers['X-Requested-With'] = 'XMLHttpRequest'
        return self.do_request(method, path, headers=headers, **kwargs)

    def get(self, path, **kwargs):
        """ GET HTTP request."""
        return self.do_request('GET', path, **kwargs)

    def head(self, path, **kwargs):
        """ HEAD HTTP request."""
        return self.do_request('HEAD', path, **kwargs)

    def post(self, path, **kwargs):
        """ POST HTTP request."""
        return self.do_request('POST', path, **kwargs)

    def follow(self):
        sc = self.status_code
        assert sc in [207, 301, 302, 303, 307]
        location = self.headers['location'][0]
        scheme, netloc, path, query, fragment = urlsplit(location)
        method = sc == 307 and self.method or 'GET'
        return self.do_request(method, path)

    def do_request(self, method, path, payload=None, headers={}, auth=None):

        headers = self.default_headers.copy()
        headers.update(headers)

        auth = auth or self.auth
        if auth:
            self.handle_auth_header(auth[0], auth[1])

        if self.cookies:
            headers['Cookie'] = '; '.join(
                '%s=%s' % cookie for cookie in self.cookies.items())
        path = urljoin(self.path, path)

        if path in self.etags:
            headers['If-None-Match'] = self.etags[path]

        body = ''
        if payload:
            if method == 'GET':
                path += '?' + urlencode(payload, doseq=True)
            else:
                body = urlencode(payload, doseq=True)
                headers['Content-Type'] = 'application/x-www-form-urlencoded'

        self.status_code = 0
        self.body = None

        self.__content = None
        self.__json = None

        self.connection.connect()
        self.connection.request(method, path, body, headers)
        r = self.connection.getresponse()
        self.body = r.read()
        self.connection.close()

        self.status_code = r.status
        self.headers = {}
        for name, value in r.getheaders():
            self.headers[name] = value

        self.handle_content_encoding()
        self.handle_etag(path)
        self.handle_cookies()
        return self.status_code

    def handle_auth_header(self, username, password):
        auth_base64 = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        self.heades.add_header("Authorization", "Basic %s" % base64string)

    def handle_content_encoding(self):
        if 'content-encoding' in self.headers \
                and 'gzip' in self.headers['content-encoding']:
            self.body = decompress(self.body)

    def handle_etag(self, path):
        if 'etag' in self.headers:
            self.etags[path] = self.headers['etag'][-1]

    def handle_cookies(self):
        if 'set-cookie' in self.headers:
            cookie_string = self.headers['set-cookie']
            cookies = SimpleCookie(cookie_string)
            for name in cookies:
                value = cookies[name].value
                if value:
                    self.cookies[name] = value
                elif name in self.cookies:
                    del self.cookies[name]

    def clear_cookies(self):
        self.cookies = {}

    @property
    def content(self):
        """ Returns a content of the response.
        """
        if self.__content is None:
            self.__content = self.body
        return self.__content

    @property
    def json(self):
        """ Returns a json response."""
        assert 'application/json' in self.headers['content-type']
        if self.__json is None:
            self.__json = loads(self.body)
        return self.__json

    def show(self):
        """Opens the current page in real web browser."""
        with open('page.html', 'w') as fp:
            fp.write(self.body)
        import webbrowser
        import os
        url = 'file://' + os.path.abspath('page.html')
        webbrowser.open(url)

    def get_header(self, key):
        key = key.replace('_', '-')
        if key in self.headers:
            return self.headers[key]

    @property
    def content_type(self):
        value = self.get_header('content-type')
        c = value.split(';')
        return c[0]

    @property
    def charset(self):
        value = self.get_header('content-type')
        c = value.split(';')
        if len(c) == 2:
            return c[1].split('=')[1]


if __name__ == '__main__':

    c = WebClient('https://github.com')
    c.get('/')
