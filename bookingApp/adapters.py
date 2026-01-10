from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class SafeSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Ensures Google login NEVER disables password-based login
    """

    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email
        if not email:
            return

        try:
            user = User.objects.get(email=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
