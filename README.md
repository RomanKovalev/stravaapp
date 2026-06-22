# stravaapp

Django REST API with Strava OAuth authentication.

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

For JSON response with the URL (Postman/API clients):

```
GET /api/auth/strava/login/?format=json
```

### 2. OAuth callback

Strava redirects to `/api/auth/strava/callback/?code=...&state=...`

Response: `{ "token": "...", "athlete_id": 12345 }`

### 3. Get athlete profile

```
GET /api/athlete/
Authorization: Token <token>
```

## Strava app settings

In [strava.com/settings/api](https://www.strava.com/settings/api) → Edit Application:

- **Authorization Callback Domain:** `13.51.255.182` (only IP, no port, no `http://`)
- **Redirect URI used by this app:** `http://13.51.255.182:8080/api/auth/strava/callback`

Strava does not allow port numbers in the Callback Domain field. The port belongs only in `redirect_uri`.
