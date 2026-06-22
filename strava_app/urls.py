from django.urls import path

from strava_app import views

urlpatterns = [
    path('auth/strava/login/', views.strava_login, name='strava-login'),
    path('auth/strava/callback/', views.strava_callback, name='strava-callback'),
    path('auth/strava/callback', views.strava_callback, name='strava-callback-no-slash'),
    path('athlete/', views.athlete_detail, name='athlete-detail'),
]
