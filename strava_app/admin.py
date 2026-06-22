from django.contrib import admin

from strava_app.models import StravaAccount


@admin.register(StravaAccount)
class StravaAccountAdmin(admin.ModelAdmin):
    list_display = ('strava_athlete_id', 'user', 'expires_at', 'updated_at')
    search_fields = ('strava_athlete_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
