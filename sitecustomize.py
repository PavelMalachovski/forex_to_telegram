"""
Test helper: patch telebot.types.Message to allow no-arg construction in tests.

Some tests instantiate Message() without required positional args. This shim
keeps real behavior when args are provided, and creates a minimal stub when
called with no args, so tests can set attributes afterwards.
"""

try:
    import telebot.types as _t

    _OriginalMessage = getattr(_t, 'Message', None)

    if _OriginalMessage is not None:
        class _PatchedMessage(_OriginalMessage):
            def __init__(self, *args, **kwargs):
                if args or kwargs:
                    # Preserve original behavior when provided
                    super().__init__(*args, **kwargs)
                else:
                    # Minimal stub fields; tests will set attributes explicitly
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
    # Fail silently; tests that rely on this will fail and surface the error
    pass


