"""Chatly launcher.

If the app fails while loading, this shows the real error on screen (with a Copy button)
instead of the app just closing.
"""
import traceback

try:
    from chatly_app import ChatApp
    STARTUP_ERROR = None
except Exception:
    ChatApp = None
    STARTUP_ERROR = traceback.format_exc()

if ChatApp is not None:
    ChatApp().run()
else:
    from kivy.app import App
    from errscreen import make_error_widget

    class ErrorApp(App):
        def build(self):
            return make_error_widget(STARTUP_ERROR)

    ErrorApp().run()
