from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from strava_app.services.strava_client import StravaAPIError

MOBILE_URI = 'stravaapp://auth'
STRAVA_TOKEN_RESPONSE = {
    'access_token': 'strava_access',
    'refresh_token': 'strava_refresh',
    'expires_at': 1893456000,
    'athlete': {'id': 42, 'firstname': 'Test', 'lastname': 'Athlete'},
}


@override_settings(MOBILE_AUTH_REDIRECT_URI=MOBILE_URI)
class StravaMobileOAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def _start_login(self, mobile=False):
        params = {'format': 'json'}
        if mobile:
            params['mobile'] = '1'
        response = self.client.get(reverse('strava-login'), params)
        self.assertEqual(response.status_code, 200)
        return response.json()['authorization_url']

    def _extract_state(self, authorization_url):
        for part in authorization_url.split('?')[1].split('&'):
            key, value = part.split('=', 1)
            if key == 'state':
                return value
        raise AssertionError('state not found in authorization URL')

    def test_login_with_mobile_stores_flag_in_cache(self):
        authorization_url = self._start_login(mobile=True)
        state = self._extract_state(authorization_url)
        state_data = cache.get(f'strava_oauth_state:{state}')
        self.assertEqual(state_data, {'mobile': True})

    def test_login_without_mobile_stores_false_flag(self):
        authorization_url = self._start_login(mobile=False)
        state = self._extract_state(authorization_url)
        state_data = cache.get(f'strava_oauth_state:{state}')
        self.assertEqual(state_data, {'mobile': False})

    @override_settings(MOBILE_AUTH_REDIRECT_URI='')
    def test_login_mobile_without_redirect_uri_returns_503(self):
        response = self.client.get(reverse('strava-login'), {'format': 'json', 'mobile': '1'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'Mobile auth redirect is not configured.')

    @patch('strava_app.views.exchange_code_for_token', return_value=STRAVA_TOKEN_RESPONSE)
    def test_callback_mobile_redirects_to_deep_link(self, _mock_exchange):
        authorization_url = self._start_login(mobile=True)
        state = self._extract_state(authorization_url)

        response = self.client.get(
            reverse('strava-callback'),
            {'code': 'auth_code', 'state': state, 'scope': 'read'},
        )

        self.assertEqual(response.status_code, 302)
        location = response['Location']
        self.assertTrue(location.startswith(f'{MOBILE_URI}?code='))

    @patch('strava_app.views.exchange_code_for_token', return_value=STRAVA_TOKEN_RESPONSE)
    def test_callback_without_mobile_returns_json(self, _mock_exchange):
        authorization_url = self._start_login(mobile=False)
        state = self._extract_state(authorization_url)

        response = self.client.get(
            reverse('strava-callback'),
            {'code': 'auth_code', 'state': state, 'scope': 'read'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['athlete_id'], 42)
        self.assertIn('access', data)
        self.assertIn('refresh', data)

    @patch('strava_app.views.exchange_code_for_token', return_value=STRAVA_TOKEN_RESPONSE)
    def test_token_exchange_returns_jwt_and_is_single_use(self, _mock_exchange):
        authorization_url = self._start_login(mobile=True)
        state = self._extract_state(authorization_url)

        callback_response = self.client.get(
            reverse('strava-callback'),
            {'code': 'auth_code', 'state': state, 'scope': 'read'},
        )
        exchange_code = callback_response['Location'].split('code=')[1]

        token_response = self.client.post(
            reverse('strava-token-exchange'),
            {'code': exchange_code},
            format='json',
        )
        self.assertEqual(token_response.status_code, 200)
        data = token_response.json()
        self.assertEqual(data['athlete_id'], 42)
        self.assertIn('access', data)
        self.assertIn('refresh', data)

        repeat_response = self.client.post(
            reverse('strava-token-exchange'),
            {'code': exchange_code},
            format='json',
        )
        self.assertEqual(repeat_response.status_code, 400)
        self.assertEqual(repeat_response.json()['error'], 'Invalid or expired code.')

    def test_token_exchange_invalid_code_returns_400(self):
        response = self.client.post(
            reverse('strava-token-exchange'),
            {'code': 'invalid'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_callback_mobile_access_denied_redirects_to_deep_link(self):
        authorization_url = self._start_login(mobile=True)
        state = self._extract_state(authorization_url)

        response = self.client.get(
            reverse('strava-callback'),
            {'error': 'access_denied', 'state': state},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'{MOBILE_URI}?error=access_denied')

    def test_callback_unknown_state_returns_json_error(self):
        response = self.client.get(
            reverse('strava-callback'),
            {'code': 'auth_code', 'state': 'unknown_state'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid OAuth state.')

    @patch('strava_app.views.exchange_code_for_token', side_effect=StravaAPIError('Failed to obtain Strava token.'))
    def test_callback_mobile_token_exchange_error_redirects(self, _mock_exchange):
        authorization_url = self._start_login(mobile=True)
        state = self._extract_state(authorization_url)

        response = self.client.get(
            reverse('strava-callback'),
            {'code': 'auth_code', 'state': state},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'{MOBILE_URI}?error=token_exchange')
