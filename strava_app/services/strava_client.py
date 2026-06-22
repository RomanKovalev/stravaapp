from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone as django_timezone

from strava_app.models import StravaAccount

STRAVA_AUTH_URL = 'https://www.strava.com/oauth/authorize'
STRAVA_TOKEN_URL = 'https://www.strava.com/oauth/token'
STRAVA_API_BASE = 'https://www.strava.com/api/v3'


class StravaAPIError(Exception):
    def __init__(self, message, status_code=502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_authorization_url(state):
    params = {
        'client_id': settings.STRAVA_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.STRAVA_REDIRECT_URI,
        'approval_prompt': 'auto',
        'scope': 'read',
        'state': state,
    }
    return f'{STRAVA_AUTH_URL}?{urlencode(params)}'


def exchange_code_for_token(code):
    response = requests.post(
        STRAVA_TOKEN_URL,
        data={
            'client_id': settings.STRAVA_CLIENT_ID,
            'client_secret': settings.STRAVA_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
        },
        timeout=30,
    )
    return _handle_token_response(response)


def refresh_access_token(refresh_token):
    response = requests.post(
        STRAVA_TOKEN_URL,
        data={
            'client_id': settings.STRAVA_CLIENT_ID,
            'client_secret': settings.STRAVA_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        },
        timeout=30,
    )
    return _handle_token_response(response)


def get_valid_access_token(strava_account):
    if django_timezone.now() >= strava_account.expires_at:
        token_data = refresh_access_token(strava_account.refresh_token)
        _update_account_tokens(strava_account, token_data)
    return strava_account.access_token


def fetch_athlete(access_token):
    response = requests.get(
        f'{STRAVA_API_BASE}/athlete',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
    )
    if response.status_code == 401:
        raise StravaAPIError('Strava access token is invalid or expired.', status_code=401)
    if response.status_code == 429:
        raise StravaAPIError('Strava rate limit exceeded.', status_code=429)
    if not response.ok:
        raise StravaAPIError(
            f'Strava API error: {response.status_code}',
            status_code=response.status_code,
        )
    return response.json()


def _handle_token_response(response):
    if response.status_code == 429:
        raise StravaAPIError('Strava rate limit exceeded.', status_code=429)
    if not response.ok:
        raise StravaAPIError(
            f'Failed to obtain Strava token: {response.status_code}',
            status_code=response.status_code,
        )
    return response.json()


def _update_account_tokens(strava_account, token_data):
    strava_account.access_token = token_data['access_token']
    strava_account.refresh_token = token_data['refresh_token']
    strava_account.expires_at = datetime.fromtimestamp(
        token_data['expires_at'],
        tz=timezone.utc,
    )
    if 'athlete' in token_data:
        strava_account.athlete_data = token_data['athlete']
    strava_account.save()
