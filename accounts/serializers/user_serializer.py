from rest_framework import serializers
from django.contrib.auth import get_user_model



User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    """Create-only serializer. Hashes password & returns user_id."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["user_id", "username", "first_name", "last_name", "name", "email", "phone", "avatar", "password", "role", "title"]
        read_only_fields = ("user_id", "created_at", "updated_at")  # user_id is auto-generated

    def create(self, validated_data):  # called by viewset
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)          # 🔑 hashes!
        user.save()
        return user 

    #---------------UPDATE / PATCH----------------
    def update(self, instance, validated_data):
         # change password if supplied
        pwd = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if pwd:
            instance.set_password(pwd)
        instance.save()
        return instance  