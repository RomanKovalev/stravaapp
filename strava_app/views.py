import secrets
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from strava_app.auth import get_tokens_for_user
from strava_app.models import StravaAccount
from strava_app.oauth_mobile import (
    consume_exchange_code,
    create_exchange_code,
    is_mobile_oauth_state,
    mobile_redirect_configured,
    mobile_redirect_response,
)
from strava_app.serializers import AthleteSerializer
from strava_app.services.strava_client import (
    StravaAPIError,
    exchange_code_for_token,
    fetch_athlete,
    get_authorization_url,
    get_valid_access_token,
)

User = get_user_model()
OAUTH_STATE_TIMEOUT = 600


def _oauth_state_key(state):
    return f'strava_oauth_state:{state}'


def _mobile_error_response(request, error):
    if mobile_redirect_configured():
        return mobile_redirect_response(error=error)
    return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def strava_login(request):
    mobile = request.query_params.get('mobile') == '1'
    if mobile and not mobile_redirect_configured():
        return Response(
            {'error': 'Mobile auth redirect is not configured.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    state = secrets.token_urlsafe(32)
    cache.set(_oauth_state_key(state), {'mobile': mobile}, timeout=OAUTH_STATE_TIMEOUT)
    authorization_url = get_authorization_url(state)

    if request.query_params.get('format') == 'json':
        return Response({'authorization_url': authorization_url})

    return redirect(authorization_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def strava_callback(request):
    state = request.query_params.get('state')
    state_key = _oauth_state_key(state)
    state_data = cache.get(state_key) if state else None
    mobile = is_mobile_oauth_state(state_data)

    strava_error = request.query_params.get('error')
    if strava_error:
        if state_data is not None:
            cache.delete(state_key)
        if mobile:
            return _mobile_error_response(request, strava_error)
        return Response({'error': strava_error}, status=status.HTTP_400_BAD_REQUEST)

    code = request.query_params.get('code')
    if not code:
        if mobile:
            return _mobile_error_response(request, 'missing_code')
        return Response({'error': 'Missing authorization code.'}, status=status.HTTP_400_BAD_REQUEST)
    if not state_data:
        if mobile:
            return _mobile_error_response(request, 'invalid_state')
        return Response({'error': 'Invalid OAuth state.'}, status=status.HTTP_400_BAD_REQUEST)
    cache.delete(state_key)

    try:
        token_data = exchange_code_for_token(code)
    except StravaAPIError as exc:
        if mobile:
            return _mobile_error_response(request, 'token_exchange')
        return Response({'error': exc.message}, status=exc.status_code)

    athlete = token_data['athlete']
    athlete_id = athlete['id']
    account = StravaAccount.objects.filter(strava_athlete_id=athlete_id).select_related('user').first()

    if account:
        user = account.user
    else:
        user = User.objects.create_user(username=f'strava_{athlete_id}')
        account = StravaAccount(user=user, strava_athlete_id=athlete_id)

    account.access_token = token_data['access_token']
    account.refresh_token = token_data['refresh_token']
    account.expires_at = datetime.fromtimestamp(token_data['expires_at'], tz=timezone.utc)
    account.athlete_data = athlete
    account.save()

    tokens = get_tokens_for_user(user)
    payload = {'athlete_id': athlete_id, **tokens}

    if mobile:
        if not mobile_redirect_configured():
            return Response(
                {'error': 'Mobile auth redirect is not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        exchange_code = create_exchange_code(payload)
        return mobile_redirect_response(code=exchange_code)

    return Response(payload)


@api_view(['POST'])
@permission_classes([AllowAny])
def strava_token_exchange(request):
    code = request.data.get('code')
    if not code:
        return Response({'error': 'Code is required.'}, status=status.HTTP_400_BAD_REQUEST)

    tokens = consume_exchange_code(code)
    if tokens is None:
        return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(tokens)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh = request.data.get('refresh')
    if not refresh:
        return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        RefreshToken(refresh).blacklist()
    except TokenError:
        return Response({'error': 'Invalid refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'detail': 'Successfully logged out.'})


@api_view(['GET'])
def athlete_detail(request):
    try:
        account = request.user.strava_account
    except StravaAccount.DoesNotExist:
        return Response(
            {'error': 'Strava account not connected.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        access_token = get_valid_access_token(account)
        athlete_data = fetch_athlete(access_token)
    except StravaAPIError as exc:
        return Response({'error': exc.message}, status=exc.status_code)

    serializer = AthleteSerializer(data=athlete_data)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data)
