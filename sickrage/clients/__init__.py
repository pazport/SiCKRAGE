# Author: echel0n <echel0n@sickrage.ca>
# URL: https://sickrage.ca
#
# This file is part of SiCKRAGE.
#
# SiCKRAGE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SiCKRAGE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SiCKRAGE.  If not, see <http://www.gnu.org/licenses/>.


import re
import time
from base64 import b16encode, b32decode
from hashlib import sha1

import requests
from bencode3 import bdecode, bencode, BencodeError

import sickrage
from sickrage.core.websession import WebSession

__all__ = [
    'utorrent',
    'transmission',
    'deluge',
    'deluged',
    'download_station',
    'rtorrent',
    'qbittorrent',
    'mlnet',
    'putio'
]

default_host = {
    'utorrent': 'http://localhost:8000',
    'transmission': 'http://localhost:9091',
    'deluge': 'http://localhost:8112',
    'deluged': 'scgi://localhost:58846',
    'download_station': 'http://localhost:5000',
    'rtorrent': 'scgi://localhost:5000',
    'qbittorrent': 'http://localhost:8080',
    'mlnet': 'http://localhost:4080',
    'putio': 'http://localhost:8080'
}


def get_client_module(name):
    name = name.lower()
    prefix = "sickrage.clients."

    return __import__(prefix + name, fromlist=__all__)


def get_client_instance(name):
    module = get_client_module(name)
    className = module.api.__class__.__name__

    return getattr(module, className)


class GenericClient(object):
    def __init__(self, name, host=None, username=None, password=None):
        self.name = name
        self.username = sickrage.app.config.torrent_username if not username else username
        self.password = sickrage.app.config.torrent_password if not password else password
        self.host = sickrage.app.config.torrent_host if not host else host
        self.rpcurl = sickrage.app.config.torrent_rpcurl

        self.url = None
        self.auth = None
        self.last_time = time.time()

        self.session = WebSession(cache=False)

        self._response = None

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, value):
        self._response = value

    def _request(self, method='get', params=None, data=None, *args, **kwargs):
        if time.time() > self.last_time + 1800 or not self.auth:
            self.last_time = time.time()
            self._get_auth()

        sickrage.app.log.debug(
            '{name}: Requested a {method} connection to {url} with'
            ' params: {params} Data: {data}'.format(
                name=self.name,
                method=method.upper(),
                url=self.url,
                params=params,
                data=str(data)[0:99] + '...' if len(str(data)) > 102 else str(data)
            )
        )

        if not self.auth:
            sickrage.app.log.warning(self.name + ': Authentication Failed')
            return False

        try:
            self.response = self.session.request(method.upper(), self.url,
                                                 params=params, data=data, auth=(self.username, self.password), timeout=120, verify=False, *args, **kwargs)

            sickrage.app.log.debug('{name}: Response to {method} request is {response}'.format(
                name=self.name,
                method=method.upper(),
                response=self.response.text
            ))
        except requests.exceptions.HTTPError as e:
            return False

        return True

    def _get_auth(self):
        """
        This should be overridden and should return the auth_id needed for the client
        """
        return None

    def _add_torrent_uri(self, result):
        """
        This should be overridden should return the True/False from the client
        when a torrent is added via url (magnet or .torrent link)
        """
        return False

    def _add_torrent_file(self, result):
        """
        This should be overridden should return the True/False from the client
        when a torrent is added via result.content (only .torrent file)
        """
        return False

    def _set_torrent_label(self, result):
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with label
        """
        return True

    def _set_torrent_ratio(self, result):
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with ratio
        """
        return True

    def _set_torrent_seed_time(self, result):
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with a seed time
        """
        return True

    def _set_torrent_priority(self, result):
        """
        This should be overriden should return the True/False from the client
        when a torrent is set with result.priority (-1 = low, 0 = normal, 1 = high)
        """
        return True

    def _set_torrent_path(self, torrent_path):
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with path
        """
        return True

    def _set_torrent_pause(self, result):
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with pause
        """
        return True

    @staticmethod
    def _get_torrent_hash(result):
        if result.url.startswith('magnet'):
            result.hash = re.findall(r'urn:btih:([\w]{32,40})', result.url)[0]
            if len(result.hash) == 32:
                result.hash = b16encode(b32decode(result.hash)).lower()
        else:
            if not result.content:
                sickrage.app.log.warning('Torrent without content')
                raise Exception('Torrent without content')

            try:
                torrent_bdecode = bdecode(result.content)
            except BencodeError:
                sickrage.app.log.warning('Unable to bdecode torrent')
                sickrage.app.log.debug('Torrent bencoded data: %r' % result.content)
                raise

            try:
                info = torrent_bdecode["info"]
            except Exception:
                sickrage.app.log.warning('Unable to find info field in torrent')
                raise

            result.hash = sha1(bencode(info)).hexdigest()

        return result

    def send_torrent(self, result):

        r_code = False

        sickrage.app.log.debug('Calling ' + self.name + ' Client')

        try:
            if not self._get_auth():
                sickrage.app.log.warning(self.name + ': Authentication Failed')
                return r_code

            # Sets per provider seed ratio
            result.ratio = result.provider.seed_ratio

            # lazy fix for now, I'm sure we already do this somewhere else too
            result = self._get_torrent_hash(result)

            # convert to magnetic url if result has info hash and is not a private provider
            if sickrage.app.config.torrent_file_to_magnet:
                if result.hash and not result.provider.private and not result.url.startswith('magnet'):
                    result.url = "magnet:?xt=urn:btih:{}".format(result.hash)

            if result.url.startswith('magnet'):
                r_code = self._add_torrent_uri(result)
            else:
                r_code = self._add_torrent_file(result)

            if not r_code:
                sickrage.app.log.warning(self.name + ': Unable to send Torrent')
                return False

            if not self._set_torrent_pause(result):
                sickrage.app.log.warning(self.name + ': Unable to set the pause for Torrent')

            if not self._set_torrent_label(result):
                sickrage.app.log.warning(self.name + ': Unable to set the label for Torrent')

            if not self._set_torrent_ratio(result):
                sickrage.app.log.warning(self.name + ': Unable to set the ratio for Torrent')

            if not self._set_torrent_seed_time(result):
                sickrage.app.log.warning(self.name + ': Unable to set the seed time for Torrent')

            if not self._set_torrent_path(result):
                sickrage.app.log.warning(self.name + ': Unable to set the path for Torrent')

            if result.priority != 0 and not self._set_torrent_priority(result):
                sickrage.app.log.warning(self.name + ': Unable to set priority for Torrent')
        except Exception as e:
            sickrage.app.log.warning(self.name + ': Failed Sending Torrent')
            sickrage.app.log.debug(self.name + ': Exception raised when sending torrent: {}. Error: {}'.format(result, e))
            return r_code

        return r_code

    def test_authentication(self):
        try:
            # verify valid url
            # self.response = self.session.get(self.url, timeout=120, verify=False)

            # verify auth
            if self._get_auth():
                return True, 'Success: Connected and Authenticated'
            return False, 'Error: Unable to get ' + self.name + ' Authentication, check your config!'
        except Exception:
            return False, 'Error: Unable to connect to ' + self.name
