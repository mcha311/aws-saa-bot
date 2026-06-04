"""
boto3 wrapper that mocks all calls when AWS_REAL_DEPLOY != 'true'.
"""
import logging
import os

import boto3

log = logging.getLogger(__name__)
AWS_REAL_DEPLOY = os.getenv("AWS_REAL_DEPLOY", "false").lower() == "true"


class _MockClient:
    def __init__(self, service: str) -> None:
        self._service = service

    def __getattr__(self, name: str):
        def _noop(*args, **kwargs):
            log.debug("[MOCK] boto3.%s.%s(%s, %s)", self._service, name, args, kwargs)
            return {}
        return _noop


def get_client(service: str, **kwargs):
    if not AWS_REAL_DEPLOY:
        return _MockClient(service)
    return boto3.client(service, **kwargs)


def get_resource(service: str, **kwargs):
    if not AWS_REAL_DEPLOY:
        return _MockClient(service)
    return boto3.resource(service, **kwargs)
