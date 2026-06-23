# stravaapp

Django REST API with Strava OAuth authentication and JWT.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Strava credentials
python manage.py migrate
python manage.py runserver 0.0.0.0:8080
```

## API

### 1. Authorize via Strava

Open in a browser (redirects to Strava automatically):

```
GET /api/auth/strava/login/
```

For JSON response with the URL (mobile / API clients):

```
GET /api/auth/strava/login/?format=json&mobile=1
```

For browser/curl testing without deep link:

```
GET /api/auth/strava/login/?format=json
```

### 2. OAuth callback

Strava redirects to `/api/auth/strava/callback?code=...&state=...`

With `mobile=1` at login — redirects to `stravaapp://auth?code=...`.

Without `mobile=1` — JSON response:

```json
{
  "athlete_id": 12345,
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

### 3. Exchange one-time code (mobile deep link)

```
POST /api/auth/strava/token/
Content-Type: application/json

{"code": "<one_time_code>"}
```

### 4. Get athlete profile

```
GET /api/athlete/
Authorization: Bearer <access_token>
```

### 5. Refresh access token

```
POST /api/auth/token/refresh/
Content-Type: application/json

{"refresh": "<refresh_token>"}
```

### 6. Logout

```
POST /api/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{"refresh": "<refresh_token>"}
```

## JWT settings

- Access token lifetime: 60 minutes
- Refresh token lifetime: 30 days
- Refresh tokens rotate on use and old ones are blacklisted

## Strava app settings

In [strava.com/settings/api](https://www.strava.com/settings/api) → Edit Application:

- **Authorization Callback Domain:** `13.51.255.182` (only IP, no port, no `http://`)
- **Redirect URI used by this app:** `http://13.51.255.182:8080/api/auth/strava/callback`

Strava does not allow port numbers in the Callback Domain field. The port belongs only in `redirect_uri`.

### Mobile deep link

Set in `.env`:

```
MOBILE_AUTH_REDIRECT_URI=stravaapp://auth
```

Mobile clients start login with `?format=json&mobile=1` and exchange the deep link code via `POST /api/auth/strava/token/`.

## Mobile integration

See [docs/MOBILE_API.md](docs/MOBILE_API.md).
