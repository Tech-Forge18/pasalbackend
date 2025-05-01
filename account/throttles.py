from rest_framework.throttling import UserRateThrottle

class LoginThrottle(UserRateThrottle):
    rate = '5/minute'

class PasswordResetThrottle(UserRateThrottle):
    rate = '3/minute'