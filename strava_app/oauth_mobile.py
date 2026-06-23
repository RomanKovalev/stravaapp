import secrets
from urllib.parse import urlencode, urlparse, urlunparse

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

EXCHANGE_CODE_PREFIX = 'strava_mobile_code:'
EXCHANGE_CODE_TIMEOUT = 60


def mobile_redirect_configured():
    return bool(settings.MOBILE_AUTH_REDIRECT_URI)


def is_mobile_oauth_state(state_data):
    if isinstance(state_data, dict):
        return state_data.get('mobile', False)
    return False


def build_mobile_redirect(**query_params):
    parsed = urlparse(settings.MOBILE_AUTH_REDIRECT_URI)
    query = urlencode(query_params)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', query, ''))


def mobile_redirect_response(**query_params):
    response = HttpResponse(status=302)
    response['Location'] = build_mobile_redirect(**query_params)
    return response


def create_exchange_code(tokens):
    code = secrets.token_urlsafe(32)
    cache.set(f'{EXCHANGE_CODE_PREFIX}{code}', tokens, timeout=EXCHANGE_CODE_TIMEOUT)
    return code


def consume_exchange_code(code):
    key = f'{EXCHANGE_CODE_PREFIX}{code}'
    tokens = cache.get(key)
    if tokens is None:
        return None
    cache.delete(key)
    return tokens
