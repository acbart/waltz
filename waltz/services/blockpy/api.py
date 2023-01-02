from json import JSONDecodeError

import warnings
import requests

from waltz.exceptions import WaltzException


class WaltzBlockPyServiceError(WaltzException):
    pass


class BlockPyAPI:
    email: str
    password: str
    base: str
    allow_insecure: bool

    def __init__(self, email, password, base, allow_insecure):
        self.email = email
        self.password = password
        self.base = base
        self.allow_insecure = allow_insecure

    def _make_request(self, verb, endpoint, json=None):
        url = self.base + 'api/' + endpoint
        if json is None:
            json = {}
        json['email'] = self.email
        json['password'] = self.password
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            response = verb(url, json=json, verify=not self.allow_insecure)
        if response.status_code == 200:
            try:
                return response.json()
            except JSONDecodeError as jde:
                raise WaltzBlockPyServiceError("Could not parse JSON:\n{}\n{}".format(response.content, str(jde)))
        else:
            raise WaltzBlockPyServiceError("{}: Service Error:\n{}\n{}".format(response.status_code,
                                                                               response.reason,
                                                                               response.text))

    def get(self, endpoint, json=None):
        return self._make_request(requests.get, endpoint, json=json)

    def post(self, endpoint, json=None):
        return self._make_request(requests.post, endpoint, json=json)
