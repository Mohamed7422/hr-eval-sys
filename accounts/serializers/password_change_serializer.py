
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True) 
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        try:
            validate_password(attrs['new_password'], self.context['request'].user)
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return attrs