from rest_framework import serializers


class AthleteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField(required=False, allow_null=True)
    firstname = serializers.CharField(required=False, allow_null=True)
    lastname = serializers.CharField(required=False, allow_null=True)
    city = serializers.CharField(required=False, allow_null=True)
    state = serializers.CharField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_null=True)
    sex = serializers.CharField(required=False, allow_null=True)
    premium = serializers.BooleanField(required=False)
    summit = serializers.BooleanField(required=False)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    badge_type_id = serializers.IntegerField(required=False, allow_null=True)
    weight = serializers.FloatField(required=False, allow_null=True)
    profile_medium = serializers.URLField(required=False, allow_null=True)
    profile = serializers.URLField(required=False, allow_null=True)
    follower_count = serializers.IntegerField(required=False, allow_null=True)
    friend_count = serializers.IntegerField(required=False, allow_null=True)
    measurement_preference = serializers.CharField(required=False, allow_null=True)
    ftp = serializers.IntegerField(required=False, allow_null=True)
