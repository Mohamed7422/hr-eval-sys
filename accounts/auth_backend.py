from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class FlexibleAuthBackend(ModelBackend):
    """
    Authenticate with:
    - email + password
    - username + password
    - email + username + password (both must match)
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email")

        if not password:
            return None
        if not (username or email):
            return None

        try:
            if username and email:
                # legacy payload: both must match the same user
                user = User.objects.get(username=username, email__iexact=email)
            elif username:
                user = User.objects.get(username=username)
            else:
                user = User.objects.get(email__iexact=email)
        except User.MultipleObjectsReturned:
            # Disambiguate if your emails aren’t unique (best: enforce unique emails)
            return None
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
