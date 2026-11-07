"""A plain-Kivy error screen. It uses no Chatly code, so it can still show up when Chatly itself fails."""
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


def make_error_widget(tb, title="Chatly could not start"):
    tb = str(tb)
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
    box.add_widget(Label(text=title, size_hint_y=None, height=dp(44), font_size="20sp", bold=True))
    box.add_widget(Label(text="Tap Copy error and send it to the developer.", size_hint_y=None,
                         height=dp(28), font_size="13sp"))
    sv = ScrollView()
    body = Label(text=tb[-3500:], size_hint_y=None, halign="left", valign="top", font_size="12sp",
                 text_size=(Window.width - dp(24), None))
    body.bind(texture_size=lambda inst, size: setattr(inst, "height", size[1]))
    sv.add_widget(body)
    box.add_widget(sv)
    btn = Button(text="Copy error", size_hint_y=None, height=dp(52))
    btn.bind(on_release=lambda *a: Clipboard.copy(tb))
    box.add_widget(btn)
    return box
