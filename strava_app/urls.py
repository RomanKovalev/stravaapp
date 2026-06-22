from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from strava_app import views

urlpatterns = [
    path('auth/strava/login/', views.strava_login, name='strava-login'),
    path('auth/strava/callback/', views.strava_callback, name='strava-callback'),
    path('auth/strava/callback', views.strava_callback, name='strava-callback-no-slash'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', views.logout, name='logout'),
    path('athlete/', views.athlete_detail, name='athlete-detail'),
]
