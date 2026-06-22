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

### 1. Get Strava authorization URL

```
GET /api/auth/strava/login/
```

Response: `{ "authorization_url": "https://www.strava.com/oauth/authorize?..." }`

Open the URL in a browser and authorize the app.

### 2. OAuth callback

Strava redirects to `/api/auth/strava/callback/?code=...&state=...`

Response: `{ "token": "...", "athlete_id": 12345 }`

### 3. Get athlete profile

```
GET /api/athlete/
Authorization: Token <token>
```

## Strava app settings

- Authorization Callback Domain: `13.51.255.182:8080`
- Redirect URI: `http://13.51.255.182:8080/api/auth/strava/callback/`
