"""
Framework integrations for linlog.

Submodules are imported lazily — importing linlog.integrations does NOT
pull in Django or any ASGI framework. Use:

    from linlog.integrations.django import RequestIDMiddleware
    from linlog.integrations.fastapi import RequestIDMiddleware
"""
