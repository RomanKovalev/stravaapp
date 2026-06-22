import secrets
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from strava_app.models import StravaAccount
from strava_app.serializers import AthleteSerializer
from strava_app.services.strava_client import (
    StravaAPIError,
    exchange_code_for_token,
    fetch_athlete,
    get_authorization_url,
    get_valid_access_token,
)

User = get_user_model()


@api_view(['GET'])
@permission_classes([AllowAny])
def strava_login(request):
    state = secrets.token_urlsafe(32)
    cache.set(f'strava_oauth_state:{state}', True, timeout=600)
    authorization_url = get_authorization_url(state)

    if request.query_params.get('format') == 'json':
        return Response({'authorization_url': authorization_url})

    return redirect(authorization_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def strava_callback(request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    state_key = f'strava_oauth_state:{state}'

    if not code:
        return Response({'error': 'Missing authorization code.'}, status=status.HTTP_400_BAD_REQUEST)
    if not state or not cache.get(state_key):
        return Response({'error': 'Invalid OAuth state.'}, status=status.HTTP_400_BAD_REQUEST)
    cache.delete(state_key)

    try:
        token_data = exchange_code_for_token(code)
    except StravaAPIError as exc:
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

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'athlete_id': athlete_id})


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
