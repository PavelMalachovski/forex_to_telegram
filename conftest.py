"""Pytest configuration and runtime shims for test stability.

Adds a lightweight shim so tests that instantiate telebot.types.Message()
without required constructor arguments won't fail. This does not affect
normal runtime behavior because production code never instantiates Message
directly.
"""

def pytest_sessionstart(session):
    try:
        import telebot.types as _t
        _OriginalMessage = getattr(_t, 'Message', None)
        if _OriginalMessage is None:
            return

        class _PatchedMessage(_OriginalMessage):
            def __init__(self, *args, **kwargs):
                if args or kwargs:
                    super().__init__(*args, **kwargs)
                else:
                    # Minimal placeholders for tests that set attributes manually
                    self.message_id = 0
                    self.from_user = None
                    self.date = 0
                    self.chat = None
                    self.content_type = 'text'
                    self.options = None
                    self.json_string = '{}'
                    self.text = ''

        _t.Message = _PatchedMessage
    except Exception:
        # Non-fatal; tests relying on direct Message() construction may fail
        pass


