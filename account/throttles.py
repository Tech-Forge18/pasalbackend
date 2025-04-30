from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

class LoginThrottle(AnonRateThrottle):
    scope = 'login'
    rate = '3/minute'

class RegisterThrottle(AnonRateThrottle):
    scope = 'register'
    rate = '2/minute'

class PasswordResetThrottle(ScopedRateThrottle):
    scope = 'password_reset'
    rate = '3/hour'

class HighSecurityThrottle(AnonRateThrottle):
    scope = 'high_security'
    rate = '1/minute'