import os
import re
import sqlite3
import threading
import time
from datetime import datetime

import certifi
import requests
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.storage.jsonstore import JsonStore
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog

import config

KV = """
#:set PRIMARY (0.0, 0.52, 1.0, 1)
#:set BG (0.955, 0.965, 0.985, 1)
#:set WHITE (1, 1, 1, 1)
#:set INK (0.09, 0.10, 0.14, 1)
#:set MUTED (0.45, 0.48, 0.56, 1)
#:set LINE (0.92, 0.93, 0.95, 1)
#:set GREEN (0.15, 0.65, 0.35, 1)

<AvatarDot>:
    size_hint: None, None
    PassCard:
        size_hint: 1, 1
        pos_hint: {"x": 0, "y": 0}
        radius: [root.width / 2]
        elevation: 0
        md_bg_color: root.color
        MDLabel:
            text: root.initial
            text_size: self.size
            halign: "center"
            valign: "middle"
            bold: True
            font_style: "H4" if root.width > dp(80) else ("H6" if root.width > dp(48) else "Subtitle1")
            theme_text_color: "Custom"
            text_color: WHITE
    PassCard:
        size_hint: None, None
        size: root.width * .38, root.width * .38
        pos_hint: {"right": 1, "y": 0}
        radius: [self.width / 2]
        elevation: 0
        md_bg_color: WHITE
        padding: self.width * .16
        opacity: 1 if root.online else 0
        PassCard:
            radius: [self.width / 2]
            elevation: 0
            md_bg_color: GREEN
    PassCard:
        size_hint: None, None
        size: pill.texture_size[0] + dp(12), dp(20)
        pos_hint: {"right": 1.04, "y": -0.04}
        radius: [dp(10)]
        elevation: 0
        md_bg_color: (0.08, 0.09, 0.12, .9)
        opacity: 1 if root.badge else 0
        padding: dp(6), 0
        Label:
            id: pill
            text: root.badge
            font_size: "11sp"
            bold: True
            color: WHITE
            size_hint: None, None
            size: self.texture_size
            pos_hint: {"center_y": .5}
    PassCard:
        size_hint: None, None
        size: root.width * .42, root.width * .42
        pos_hint: {"right": 1.02, "y": -0.02}
        radius: [self.width / 2]
        elevation: 0
        md_bg_color: (0.16, 0.18, 0.24, 1)
        opacity: 1 if root.plus else 0
        MDIcon:
            icon: "plus"
            size_hint: 1, 1
            text_size: self.size
            halign: "center"
            valign: "middle"
            font_size: "16sp"
            theme_text_color: "Custom"
            text_color: WHITE

<StoryItem>:
    orientation: "vertical"
    size_hint: None, None
    size: dp(86), dp(124)
    padding: dp(4), 0
    spacing: dp(3)
    Label:
        id: nmeas
        text: root.note
        font_size: "11sp"
        size_hint: None, None
        size: 0, 0
        opacity: 0
    PassCard:
        size_hint: None, None
        size: min(nmeas.texture_size[0] + dp(18), dp(78)), dp(26)
        pos_hint: {"center_x": .5}
        radius: [dp(13)]
        elevation: 0
        md_bg_color: (0.93, 0.94, 0.97, 1)
        opacity: 1 if root.note else 0
        padding: dp(8), 0
        Label:
            text: root.note
            font_size: "11sp"
            color: MUTED if root.placeholder else INK
            halign: "center"
            valign: "middle"
            shorten: True
            max_lines: 1
            text_size: self.size
    AvatarDot:
        size: dp(60), dp(60)
        pos_hint: {"center_x": .5}
        initial: root.initial
        color: root.color
        online: root.online
        badge: root.badge
        plus: root.plus
    Label:
        text: root.name
        font_size: "12sp"
        color: INK
        size_hint_y: None
        height: dp(18)
        halign: "center"
        shorten: True
        max_lines: 1
        text_size: self.width, None

<SectionLabel>:
    halign: "left"
    font_style: "Caption"
    bold: True
    theme_text_color: "Custom"
    text_color: MUTED
    size_hint_y: None
    text_size: self.width, None
    height: self.texture_size[1] + dp(6)

<SwitchRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(64)
    spacing: dp(8)
    padding: 0, 0, dp(14), 0
    MDBoxLayout:
        orientation: "vertical"
        adaptive_height: True
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.title
            font_style: "Subtitle1"
            theme_text_color: "Custom"
            text_color: INK
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
        MDLabel:
            text: root.subtitle
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: MUTED
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
    MDSwitch:
        active: root.active
        pos_hint: {"center_y": .5}
        on_active: root.active = self.active

<MenuRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(60)
    spacing: dp(14)
    padding: dp(4), 0
    md_bg_color: (0.95, 0.96, 0.98, 1) if self.state == "down" else (1, 1, 1, 0)
    MDIcon:
        icon: root.icon
        size_hint: None, None
        size: dp(28), dp(28)
        pos_hint: {"center_y": .5}
        theme_text_color: "Custom"
        text_color: PRIMARY
    MDBoxLayout:
        orientation: "vertical"
        adaptive_height: True
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.title
            font_style: "Subtitle1"
            theme_text_color: "Custom"
            text_color: INK
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
        MDLabel:
            text: root.subtitle
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: MUTED
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
    MDIcon:
        icon: "chevron-right"
        size_hint: None, None
        size: dp(24), dp(24)
        pos_hint: {"center_y": .5}
        theme_text_color: "Custom"
        text_color: MUTED

<Bubble>:
    orientation: "horizontal"
    adaptive_height: True
    padding: dp(10), dp(2)
    Label:
        id: meas
        text: root.text
        font_size: "16sp"
        size_hint: None, None
        size: 0, 0
        opacity: 0
    Widget:
        size_hint_x: 1 if root.mine else None
        width: 0
    MDCard:
        orientation: "vertical"
        size_hint: None, None
        width: max(lbl.width, tlbl.width) + dp(28)
        height: lbl.height + tlbl.height + dp(22)
        radius: [20, 20, 6, 20] if root.mine else [20, 20, 20, 6]
        padding: dp(14), dp(8)
        spacing: dp(2)
        elevation: 0
        md_bg_color: PRIMARY if root.mine else WHITE
        Label:
            id: lbl
            text: root.text
            font_size: "16sp"
            color: WHITE if root.mine else INK
            halign: "left"
            size_hint: None, None
            text_size: min(meas.texture_size[0] + dp(4), root.width * .74, dp(300)), None
            size: self.texture_size
        Label:
            id: tlbl
            text: root.time
            font_size: "11sp"
            color: (1, 1, 1, .75) if root.mine else MUTED
            size_hint: None, None
            size: self.texture_size
            pos_hint: {"right": 1}
    Widget:
        size_hint_x: None if root.mine else 1
        width: 0

<ContactRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(76)
    padding: dp(18), dp(10)
    spacing: dp(14)
    md_bg_color: (0.94, 0.95, 0.98, 1) if self.state == "down" else WHITE
    AvatarDot:
        size: dp(54), dp(54)
        pos_hint: {"center_y": .5}
        initial: root.initial
        color: root.avatar_color
        online: root.online
    MDBoxLayout:
        orientation: "vertical"
        adaptive_height: True
        spacing: dp(2)
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.name
            bold: True
            font_style: "Subtitle1"
            theme_text_color: "Custom"
            text_color: INK
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
        MDLabel:
            text: root.subtitle
            bold: root.unread > 0
            font_style: "Body2"
            theme_text_color: "Custom"
            text_color: INK if root.unread > 0 else MUTED
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
    PassCard:
        size_hint: None, None
        size: (dp(26), dp(26)) if root.unread > 0 else (0, 0)
        opacity: 1 if root.unread > 0 else 0
        radius: [dp(13)]
        elevation: 0
        pos_hint: {"center_y": .5}
        md_bg_color: PRIMARY
        MDLabel:
            text: str(root.unread) if root.unread < 100 else "99+"
            text_size: self.size
            halign: "center"
            valign: "middle"
            bold: True
            font_size: "12sp"
            theme_text_color: "Custom"
            text_color: WHITE

MDScreenManager:

    MDScreen:
        name: "login"
        md_bg_color: PRIMARY
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(210)
                padding: dp(24), dp(30), dp(24), dp(10)
                spacing: dp(8)
                Image:
                    source: "logo.png"
                    size_hint: None, None
                    size: dp(84), dp(84)
                    pos_hint: {"center_x": .5}
                MDLabel:
                    text: "Chatly"
                    halign: "center"
                    font_style: "H5"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: WHITE
                    size_hint_y: None
                    height: dp(36)
                MDLabel:
                    text: "Chat with friends, instantly"
                    halign: "center"
                    font_style: "Body2"
                    theme_text_color: "Custom"
                    text_color: (1, 1, 1, .85)
                    size_hint_y: None
                    height: dp(22)
            MDCard:
                orientation: "vertical"
                radius: [dp(32), dp(32), 0, 0]
                elevation: 0
                md_bg_color: WHITE
                padding: dp(24), dp(24), dp(24), 0
                ScrollView:
                    bar_width: 0
                    do_scroll_x: False
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(12)
                        padding: 0, 0, 0, dp(24)
                        MDLabel:
                            text: "Create your account" if app.signup_mode else "Welcome back"
                            font_style: "H5"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            height: dp(40)
                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: dp(12)
                            size_hint_y: None
                            height: (dp(64) * 2 + dp(12)) if app.signup_mode else 0
                            opacity: 1 if app.signup_mode else 0
                            disabled: not app.signup_mode
                            MDTextField:
                                id: display_field
                                hint_text: "Display name (shown to friends)"
                                mode: "rectangle"
                            MDTextField:
                                id: username_field
                                hint_text: "Username (letters, numbers, _ .)"
                                mode: "rectangle"
                        MDTextField:
                            id: email_field
                            hint_text: "Email"
                            mode: "rectangle"
                            input_type: "mail"
                        MDTextField:
                            id: pass_field
                            hint_text: "Password (min 6 characters)"
                            mode: "rectangle"
                            password: True
                            on_text_validate: app.submit()
                        MDRaisedButton:
                            text: "Please wait..." if app.loading else ("Create account" if app.signup_mode else "Sign in")
                            size_hint: 1, None
                            height: dp(52)
                            font_size: "16sp"
                            md_bg_color: PRIMARY
                            disabled: app.loading
                            on_release: app.submit()
                        MDFlatButton:
                            text: "Have an account? Sign in" if app.signup_mode else "New here? Create account"
                            pos_hint: {"center_x": .5}
                            theme_text_color: "Custom"
                            text_color: PRIMARY
                            on_release: app.toggle_mode()

    MDScreen:
        name: "contacts"
        md_bg_color: WHITE
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(76)
                padding: dp(22), dp(14), dp(8), dp(6)
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    pos_hint: {"center_y": .5}
                    MDLabel:
                        text: "Chats"
                        font_style: "H5"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: INK
                        size_hint_y: None
                        height: dp(34)
                    MDLabel:
                        text: "Signed in as " + app.me_name
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        height: dp(18)
                MDIconButton:
                    icon: "cog-outline"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: PRIMARY
                    on_release: app.open_settings()
            MDBoxLayout:
                size_hint_y: None
                height: dp(60)
                padding: dp(16), dp(6)
                MDCard:
                    radius: [dp(22)]
                    elevation: 0
                    md_bg_color: (0.94, 0.95, 0.97, 1)
                    padding: dp(14), 0
                    spacing: dp(8)
                    MDIcon:
                        icon: "magnify"
                        size_hint: None, None
                        size: dp(24), dp(24)
                        pos_hint: {"center_y": .5}
                        theme_text_color: "Custom"
                        text_color: MUTED
                    TextInput:
                        id: search_field
                        hint_text: "Search people"
                        multiline: False
                        background_color: 0, 0, 0, 0
                        background_normal: ""
                        background_active: ""
                        foreground_color: INK
                        hint_text_color: MUTED
                        cursor_color: PRIMARY
                        font_size: "16sp"
                        padding: [0, dp(12), 0, dp(12)]
                        on_text: app.refresh_contacts()
            ScrollView:
                id: rail_sv
                size_hint_y: None
                height: dp(126)
                bar_width: 0
                do_scroll_y: False
                MDBoxLayout:
                    id: rail
                    orientation: "horizontal"
                    adaptive_width: True
                    size_hint_y: None
                    height: dp(126)
                    padding: dp(10), 0
            ScrollView:
                bar_width: 0
                MDBoxLayout:
                    id: contact_list
                    orientation: "vertical"
                    adaptive_height: True

    MDScreen:
        name: "settings"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                md_bg_color: WHITE
                padding: dp(4), dp(6), dp(12), dp(6)
                spacing: dp(6)
                MDIconButton:
                    icon: "arrow-left"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: INK
                    on_release: app.close_settings()
                MDLabel:
                    text: "Settings"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                    size_hint_y: None
                    text_size: self.width, None
                    height: self.texture_size[1]
                    pos_hint: {"center_y": .5}
            MDBoxLayout:
                size_hint_y: None
                height: dp(1)
                md_bg_color: LINE
            ScrollView:
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16), dp(18), dp(16), dp(30)
                    spacing: dp(10)
                    AvatarDot:
                        size: dp(88), dp(88)
                        pos_hint: {"center_x": .5}
                        initial: app.me_initial
                        color: app.me_color
                    MDLabel:
                        text: app.me_name
                        halign: "center"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: INK
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    MDLabel:
                        text: "@" + app.me_username
                        halign: "center"
                        font_style: "Subtitle1"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    MDLabel:
                        text: app.me_email
                        halign: "center"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    SectionLabel:
                        text: "ACCOUNT"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(12), dp(4)
                        MenuRow:
                            icon: "account-outline"
                            title: "Profile"
                            subtitle: app.me_name
                            on_release: app.open_profile()
                        MenuRow:
                            icon: "lock-outline"
                            title: "Change password"
                            subtitle: "Update your password"
                            on_release: app.open_password()
                    SectionLabel:
                        text: "PRIVACY"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(16), dp(4)
                        SwitchRow:
                            id: active_row
                            title: "Show when I'm active"
                            subtitle: "Friends can see when you are online"
                            on_active: app.set_show_active(self.active)
                    SectionLabel:
                        text: "CHATS"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(16), dp(4)
                        SwitchRow:
                            id: rail_row
                            title: "Active friends strip"
                            subtitle: "Show friends and notes at the top of Chats"
                            on_active: app.set_pref("rail", self.active)
                        SwitchRow:
                            id: preview_row
                            title: "Message previews"
                            subtitle: "Show the last message in your chat list"
                            on_active: app.set_pref("previews", self.active)
                    SectionLabel:
                        text: "STORAGE"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(16), dp(12)
                        spacing: dp(4)
                        MDLabel:
                            text: "Chats are saved on this phone so they open instantly. Clearing them is safe: they reload from the server."
                            font_style: "Body2"
                            theme_text_color: "Custom"
                            text_color: MUTED
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        MDFlatButton:
                            text: "Clear saved chats"
                            theme_text_color: "Custom"
                            text_color: PRIMARY
                            on_release: app.clear_cache()
                    SectionLabel:
                        text: "ABOUT"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(16), dp(12)
                        spacing: dp(2)
                        MDLabel:
                            text: "Chatly"
                            font_style: "Subtitle1"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        MDLabel:
                            text: "Version 1.0"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: MUTED
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                    MDFlatButton:
                        text: "Log out"
                        pos_hint: {"center_x": .5}
                        theme_text_color: "Custom"
                        text_color: INK
                        on_release: app.logout()
                    MDFlatButton:
                        text: "Delete account"
                        pos_hint: {"center_x": .5}
                        theme_text_color: "Custom"
                        text_color: (0.86, 0.2, 0.25, 1)
                        on_release: app.confirm_delete_account()

    MDScreen:
        name: "profile"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                md_bg_color: WHITE
                padding: dp(4), dp(6), dp(12), dp(6)
                spacing: dp(6)
                MDIconButton:
                    icon: "arrow-left"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: INK
                    on_release: app.back_to_settings()
                MDLabel:
                    text: "Profile"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                    size_hint_y: None
                    text_size: self.width, None
                    height: self.texture_size[1]
                    pos_hint: {"center_y": .5}
            MDBoxLayout:
                size_hint_y: None
                height: dp(1)
                md_bg_color: LINE
            ScrollView:
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16), dp(22), dp(16), dp(30)
                    spacing: dp(10)
                    AvatarDot:
                        size: dp(96), dp(96)
                        pos_hint: {"center_x": .5}
                        initial: app.me_initial
                        color: app.me_color
                    MDLabel:
                        text: "@" + app.me_username
                        halign: "center"
                        font_style: "Subtitle1"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    MDLabel:
                        text: app.me_email
                        halign: "center"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    SectionLabel:
                        text: "DISPLAY NAME"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(14)
                        spacing: dp(12)
                        MDTextField:
                            id: name_field
                            hint_text: "Display name"
                            mode: "rectangle"
                        MDLabel:
                            text: "This is the name your friends see in chats."
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: MUTED
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        MDRaisedButton:
                            text: "Save"
                            size_hint: 1, None
                            height: dp(48)
                            font_size: "16sp"
                            md_bg_color: PRIMARY
                            disabled: app.loading
                            on_release: app.save_profile()

    MDScreen:
        name: "password"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                md_bg_color: WHITE
                padding: dp(4), dp(6), dp(12), dp(6)
                spacing: dp(6)
                MDIconButton:
                    icon: "arrow-left"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: INK
                    on_release: app.back_to_settings()
                MDLabel:
                    text: "Change password"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                    size_hint_y: None
                    text_size: self.width, None
                    height: self.texture_size[1]
                    pos_hint: {"center_y": .5}
            MDBoxLayout:
                size_hint_y: None
                height: dp(1)
                md_bg_color: LINE
            ScrollView:
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16), dp(22), dp(16), dp(30)
                    spacing: dp(10)
                    MDLabel:
                        text: "Choose a new password with at least 6 characters."
                        font_style: "Body2"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        radius: [dp(16)]
                        padding: dp(14)
                        spacing: dp(12)
                        MDTextField:
                            id: pw_new
                            hint_text: "New password"
                            mode: "rectangle"
                            password: True
                        MDTextField:
                            id: pw_confirm
                            hint_text: "Confirm new password"
                            mode: "rectangle"
                            password: True
                            on_text_validate: app.change_password()
                        MDRaisedButton:
                            text: "Update password"
                            size_hint: 1, None
                            height: dp(48)
                            font_size: "16sp"
                            md_bg_color: PRIMARY
                            disabled: app.loading
                            on_release: app.change_password()

    MDScreen:
        name: "note"
        md_bg_color: (0, 0, 0, 1)
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(68)
                padding: dp(8), dp(10), dp(14), dp(10)
                MDIconButton:
                    icon: "close"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: WHITE
                    on_release: app.close_note()
                MDLabel:
                    text: "New note"
                    halign: "center"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: WHITE
                TapBox:
                    size_hint: None, None
                    size: dp(88), dp(42)
                    pos_hint: {"center_y": .5}
                    on_release: app.share_note()
                    PassCard:
                        radius: [dp(21)]
                        elevation: 0
                        md_bg_color: PRIMARY if app.note_ready else (0.17, 0.17, 0.19, 1)
                        MDLabel:
                            text: "Share"
                            text_size: self.size
                            halign: "center"
                            valign: "middle"
                            bold: True
                            font_style: "Subtitle1"
                            theme_text_color: "Custom"
                            text_color: WHITE if app.note_ready else (0.55, 0.56, 0.6, 1)
            Widget:
                size_hint_y: .5
            MDFloatLayout:
                size_hint: None, None
                size: dp(290), dp(200)
                pos_hint: {"center_x": .5}
                AvatarDot:
                    size: dp(104), dp(104)
                    pos_hint: {"center_x": .5, "y": 0}
                    initial: app.me_initial
                    color: app.me_color
                PassCard:
                    size_hint: None, None
                    size: dp(16), dp(16)
                    pos_hint: {"x": .31, "y": .585}
                    radius: [dp(8)]
                    elevation: 0
                    md_bg_color: (0.14, 0.14, 0.15, 1)
                PassCard:
                    size_hint: None, None
                    size: dp(8), dp(8)
                    pos_hint: {"x": .345, "y": .54}
                    radius: [dp(4)]
                    elevation: 0
                    md_bg_color: (0.14, 0.14, 0.15, 1)
                MDCard:
                    size_hint: None, None
                    size: dp(270), dp(46)
                    pos_hint: {"center_x": .5, "y": .70}
                    radius: [dp(23)]
                    elevation: 0
                    md_bg_color: (0.14, 0.14, 0.15, 1)
                    padding: dp(18), 0
                    TextInput:
                        id: note_input
                        hint_text: "Share a thought..."
                        multiline: False
                        text_validate_unfocus: False
                        background_color: 0, 0, 0, 0
                        background_normal: ""
                        background_active: ""
                        foreground_color: WHITE
                        hint_text_color: (0.6, 0.62, 0.66, 1)
                        cursor_color: PRIMARY
                        font_size: "17sp"
                        padding: [0, dp(13), 0, dp(13)]
                        on_text: app.on_note_text(self)
                        on_text_validate: app.share_note()
            MDFlatButton:
                text: "Delete note"
                pos_hint: {"center_x": .5}
                opacity: 1 if app.has_note else 0
                disabled: not app.has_note
                theme_text_color: "Custom"
                text_color: (1, 0.35, 0.4, 1)
                on_release: app.delete_note()
            Widget:
                size_hint_y: .9
            MDLabel:
                text: "Friends can see your note on Chatly for 24 hours."
                halign: "center"
                font_style: "Body2"
                theme_text_color: "Custom"
                text_color: (0.82, 0.83, 0.86, 1)
                size_hint_y: None
                text_size: self.width - dp(32), None
                height: dp(64)

    MDScreen:
        name: "chat"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                md_bg_color: WHITE
                padding: dp(4), dp(6), dp(12), dp(6)
                spacing: dp(8)
                MDIconButton:
                    icon: "arrow-left"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: INK
                    on_release: app.back()
                AvatarDot:
                    size: dp(42), dp(42)
                    pos_hint: {"center_y": .5}
                    initial: app.peer_initial
                    color: app.peer_color
                    online: app.peer_active
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    pos_hint: {"center_y": .5}
                    MDLabel:
                        text: app.peer_name
                        font_style: "Subtitle1"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: INK
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    MDLabel:
                        text: app.peer_status
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: GREEN if app.peer_active else MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1] if self.text else 0
            MDBoxLayout:
                size_hint_y: None
                height: dp(1)
                md_bg_color: LINE
            ScrollView:
                id: scroll
                bar_width: 0
                MDBoxLayout:
                    id: msg_list
                    orientation: "vertical"
                    adaptive_height: True
                    padding: 0, dp(10)
                    spacing: dp(4)
            MDBoxLayout:
                size_hint_y: None
                height: dp(68)
                padding: dp(12), dp(10)
                spacing: dp(10)
                MDCard:
                    radius: [dp(24)]
                    elevation: 0
                    md_bg_color: WHITE
                    padding: dp(18), 0
                    TextInput:
                        id: msg_field
                        hint_text: "Message"
                        multiline: False
                        text_validate_unfocus: False
                        background_color: 0, 0, 0, 0
                        background_normal: ""
                        background_active: ""
                        foreground_color: INK
                        hint_text_color: MUTED
                        cursor_color: PRIMARY
                        font_size: "16sp"
                        padding: [0, dp(14), 0, dp(14)]
                        on_text_validate: app.send()
                MDCard:
                    size_hint: None, None
                    size: dp(48), dp(48)
                    radius: [dp(24)]
                    elevation: 0
                    md_bg_color: PRIMARY
                    MDIconButton:
                        icon: "send"
                        pos_hint: {"center_x": .5, "center_y": .5}
                        theme_icon_color: "Custom"
                        icon_color: WHITE
                        on_release: app.send()
"""


AVATAR_COLORS = [
    (0.00, 0.52, 1.00, 1), (0.55, 0.36, 0.96, 1), (0.96, 0.36, 0.52, 1), (0.98, 0.58, 0.16, 1),
    (0.13, 0.70, 0.56, 1), (0.20, 0.60, 0.86, 1), (0.86, 0.30, 0.70, 1), (0.40, 0.45, 0.90, 1),
]


def avatar_color(name):
    return list(AVATAR_COLORS[sum(ord(c) for c in (name or "?")) % len(AVATAR_COLORS)])


def initial(name):
    return ((name or "?").strip()[:1] or "?").upper()


def fmt_time(ts):
    """'2026-11-04T08:11:06.12+00:00' -> local 'HH:MM' (empty string if unknown)."""
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone().strftime("%H:%M")
    except Exception:
        return str(ts)[11:16]


def name_of(u):
    return (u.get("display_name") or u.get("username") or "?").strip()


def is_online(sec):
    return sec is not None and sec < 70


def presence_text(sec):
    if sec is None:
        return ""
    if sec < 70:
        return "Active now"
    m = int(sec // 60)
    if m < 60:
        return f"Active {m}m ago"
    h = m // 60
    return f"Active {h}h ago" if h < 24 else f"Active {h // 24}d ago"


def short(text, n):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "..."


def badge_text(sec):
    """'10m' / '3h' pill for friends who were recently active (empty when online or unknown)."""
    if sec is None or sec < 70:
        return ""
    m = int(sec // 60)
    if m < 60:
        return f"{m}m"
    h = m // 60
    return f"{h}h" if h < 24 else ""


class Supa:
    """Minimal Supabase client (Auth + PostgREST) using plain HTTPS requests."""

    def __init__(self, on_tokens=None):
        self.base = config.SUPABASE_URL.rstrip("/")
        self.key = config.SUPABASE_ANON_KEY
        self.access = self.refresh = self.uid = None
        self.username = ""
        self.email = ""
        self.exp = 0
        self.on_tokens = on_tokens

    def _req(self, method, path, auth=True, headers=None, **kw):
        if auth:
            self.ensure()
        h = {"apikey": self.key}
        if auth:
            h["Authorization"] = f"Bearer {self.access}"
        elif not self.key.startswith("sb_"):
            h["Authorization"] = f"Bearer {self.key}"  # legacy anon key is a JWT
        h.update(headers or {})
        r = requests.request(method, self.base + path, headers=h, timeout=15,
                             verify=certifi.where(), **kw)
        if r.status_code >= 400:
            try:
                j = r.json()
                msg = j.get("msg") or j.get("error_description") or j.get("message") or r.text
            except ValueError:
                msg = r.text
            raise RuntimeError(msg)
        return r.json() if r.text else None

    def _set(self, d):
        self.access, self.refresh = d["access_token"], d["refresh_token"]
        self.exp = time.time() + d.get("expires_in", 3600) - 60
        user = d["user"]
        self.uid = user["id"]
        self.email = user.get("email") or ""
        self.username = (user.get("user_metadata") or {}).get("username", "")
        if self.on_tokens:
            self.on_tokens(self.refresh)

    def ensure(self):
        if self.refresh and time.time() > self.exp:
            self._set(self._req("POST", "/auth/v1/token?grant_type=refresh_token", auth=False,
                                json={"refresh_token": self.refresh}))

    # ----- auth -----
    def sign_up(self, email, password, username, display_name=""):
        d = self._req("POST", "/auth/v1/signup", auth=False,
                      json={"email": email, "password": password,
                            "data": {"username": username, "display_name": display_name}})
        if d and d.get("access_token"):
            self._set(d)
            return True
        return False  # email confirmation required

    def sign_in(self, email, password):
        self._set(self._req("POST", "/auth/v1/token?grant_type=password", auth=False,
                            json={"email": email, "password": password}))

    def sign_out(self):
        try:
            self._req("POST", "/auth/v1/logout")
        except Exception:
            pass
        self.access = self.refresh = self.uid = None

    # ----- data -----
    def users(self):
        """People with display names + presence. Falls back if supabase/update_v2.sql was not run yet."""
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_people", json={})
            return [{"id": r["id"], "username": r["username"], "display_name": r.get("display_name"),
                     "seconds_ago": r.get("seconds_ago"), "note": r.get("note")} for r in rows]
        except RuntimeError:
            rows = self._req("GET", "/rest/v1/profiles", params={"select": "id,username", "order": "username"})
            return [{"id": r["id"], "username": r["username"], "display_name": None, "seconds_ago": None,
                     "note": None} for r in rows if r["id"] != self.uid]

    def me(self):
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_me", json={})
            if rows:
                return rows[0]
        except RuntimeError:
            pass  # supabase/update_v3.sql not run yet
        for cols in ("id,username,display_name,show_active", "id,username"):
            try:
                rows = self._req("GET", "/rest/v1/profiles", params={"select": cols, "id": f"eq.{self.uid}"})
                if rows:
                    return rows[0]
            except RuntimeError:
                continue
        return {"id": self.uid, "username": self.username}

    def set_display_name(self, name):
        self._req("PATCH", "/rest/v1/profiles", params={"id": f"eq.{self.uid}"},
                  json={"display_name": name or None}, headers={"Prefer": "return=minimal"})

    def set_show_active(self, flag):
        self._req("PATCH", "/rest/v1/profiles", params={"id": f"eq.{self.uid}"},
                  json={"show_active": bool(flag)}, headers={"Prefer": "return=minimal"})

    def change_password(self, new_password):
        self._req("PUT", "/auth/v1/user", json={"password": new_password})

    def delete_account(self):
        self._req("POST", "/rest/v1/rpc/delete_my_account", json={})

    def set_note(self, text):
        self._req("POST", "/rest/v1/rpc/set_note", json={"p_note": text})

    def touch(self):
        self._req("POST", "/rest/v1/rpc/touch_presence", json={})

    def history(self, peer):
        a, b = self.uid, peer
        rows = self._req("GET", "/rest/v1/messages", params={
            "select": "*",
            "or": f"(and(sender.eq.{a},receiver.eq.{b}),and(sender.eq.{b},receiver.eq.{a}))",
            "order": "id.desc", "limit": "200"})
        return list(reversed(rows))

    def incoming(self, after):
        return self._req("GET", "/rest/v1/messages", params={
            "select": "*", "receiver": f"eq.{self.uid}", "id": f"gt.{after}", "order": "id.asc"})

    def latest_incoming_id(self):
        rows = self._req("GET", "/rest/v1/messages", params={
            "select": "id", "receiver": f"eq.{self.uid}", "order": "id.desc", "limit": "1"})
        return rows[0]["id"] if rows else 0

    def send(self, peer, text):
        rows = self._req("POST", "/rest/v1/messages", headers={"Prefer": "return=representation"},
                         json={"sender": self.uid, "receiver": peer, "text": text})
        return rows[0]


class LocalDB:
    """On-device SQLite cache: chats open instantly and survive app restarts."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock, self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT NOT NULL, display_name TEXT);
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY, sender TEXT NOT NULL, receiver TEXT NOT NULL,
                    text TEXT NOT NULL, created_at TEXT);
                CREATE INDEX IF NOT EXISTS idx_pair ON messages(sender, receiver, id);
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
            """)
            cols = [r[1] for r in self.conn.execute("PRAGMA table_info(users)")]
            if "display_name" not in cols:  # cache created by an older app version
                self.conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")

    def save_users(self, users):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM users")
            self.conn.executemany("INSERT INTO users(id, username, display_name) VALUES(?, ?, ?)",
                                  [(u["id"], u["username"], u.get("display_name")) for u in users])

    def load_users(self):
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, username, display_name FROM users ORDER BY COALESCE(display_name, username)").fetchall()
        return [{"id": r["id"], "username": r["username"], "display_name": r["display_name"],
                 "seconds_ago": None} for r in rows]

    def save_messages(self, msgs):
        with self.lock, self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO messages(id, sender, receiver, text, created_at) VALUES(?,?,?,?,?)",
                [(m["id"], m["sender"], m["receiver"], m["text"], m.get("created_at")) for m in msgs])

    def load_history(self, me, peer, limit=200):
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM (SELECT * FROM messages WHERE (sender=? AND receiver=?) "
                "OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (me, peer, peer, me, limit)).fetchall()
        return [dict(r) for r in rows]

    def last_message(self, me, peer):
        with self.lock:
            row = self.conn.execute(
                "SELECT id, sender, text FROM messages WHERE (sender=? AND receiver=?) "
                "OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (me, peer, peer, me)).fetchone()
        return dict(row) if row else None

    def clear_cache(self):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM messages")
            self.conn.execute("DELETE FROM users")

    def get_meta(self, key):
        with self.lock:
            row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key, value):
        with self.lock, self.conn:
            self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", (key, str(value)))

    def destroy(self):
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                pass
        for suffix in ("", "-journal"):
            try:
                os.remove(self.path + suffix)
            except OSError:
                pass


class CrashCatcher(ExceptionHandler):
    """Keeps the app alive on unexpected errors, logs them, and shows the message."""

    def handle_exception(self, inst):
        import traceback
        tb = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
        try:
            app = MDApp.get_running_app()
            with open(os.path.join(app.user_data_dir, "crash.log"), "a") as f:
                f.write(time.ctime() + "\n" + tb + "\n")
            where = ""
            for fr in reversed(traceback.extract_tb(inst.__traceback__)):
                if fr.filename.endswith("main.py"):
                    where = f" (line {fr.lineno}, in {fr.name})"
                    break
            last = f"{type(inst).__name__}: {inst}{where}"
            Clock.schedule_once(lambda dt: app.notify("Unexpected error: " + last))
        except Exception:
            pass
        return ExceptionManager.PASS


ExceptionManager.add_handler(CrashCatcher())


class Bubble(MDBoxLayout):
    text = StringProperty("")
    time = StringProperty("")
    mine = BooleanProperty(False)


class PassCard(MDCard):
    """A card that ignores touches, so a tap on it reaches the tappable row that contains it.
    (Plain MDCards are clickable themselves and would swallow the tap.)"""

    def on_touch_down(self, touch):
        return False

    def on_touch_move(self, touch):
        return False

    def on_touch_up(self, touch):
        return False


class AvatarDot(MDFloatLayout):
    """Round avatar with an initial and an optional green 'active' dot."""
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    online = BooleanProperty(False)
    badge = StringProperty("")
    plus = BooleanProperty(False)


class SectionLabel(MDLabel):
    """Small grey heading above a group of settings."""


class SwitchRow(MDBoxLayout):
    """Title + subtitle with an on/off switch (two-way bound to `active`)."""
    title = StringProperty("")
    subtitle = StringProperty("")
    active = BooleanProperty(False)


class MenuRow(ButtonBehavior, MDBoxLayout):
    """A tappable settings row: icon, title, subtitle and a chevron."""
    icon = StringProperty("")
    title = StringProperty("")
    subtitle = StringProperty("")


class TapBox(ButtonBehavior, MDBoxLayout):
    """A plain tappable container."""


class StoryItem(ButtonBehavior, MDBoxLayout):
    """One avatar in the top 'active friends' rail."""
    name = StringProperty("")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    note = StringProperty("")
    placeholder = BooleanProperty(False)
    online = BooleanProperty(False)
    badge = StringProperty("")
    plus = BooleanProperty(False)


class ContactRow(ButtonBehavior, MDBoxLayout):
    name = StringProperty("")
    subtitle = StringProperty("")
    initial = StringProperty("?")
    avatar_color = ListProperty([0, 0.52, 1, 1])
    unread = NumericProperty(0)
    online = BooleanProperty(False)


class ChatApp(MDApp):
    signup_mode = BooleanProperty(False)
    loading = BooleanProperty(False)
    me_name = StringProperty("")
    peer_name = StringProperty("")
    peer_initial = StringProperty("")
    peer_color = ListProperty([0, 0.52, 1, 1])
    peer_status = StringProperty("")
    peer_active = BooleanProperty(False)
    me_username = StringProperty("")
    me_email = StringProperty("")
    me_initial = StringProperty("?")
    me_color = ListProperty([0, 0.52, 1, 1])
    note_ready = BooleanProperty(False)
    has_note = BooleanProperty(False)

    def build(self):
        self.title = "Chatly"
        self.theme_cls.primary_palette = "Blue"
        self.store = JsonStore(os.path.join(self.user_data_dir, "session.json"))
        self.api = Supa(on_tokens=lambda t: self.store.put("session", refresh=t))
        self.local = None
        self.users = []
        self.msgs = {}
        self.seen = set()
        self.unread = {}
        self.peer = None
        self.last_id = 0
        self.poll_busy = False
        self.tick = 0
        self.me = {}
        self._profile_loading = False
        self.prefs = {"previews": True, "rail": True}
        if self.store.exists("prefs"):
            self.prefs.update(self.store.get("prefs"))
        Window.softinput_mode = "below_target"
        Window.bind(on_keyboard=self._on_key)
        return Builder.load_string(KV)

    def on_start(self):
        Clock.schedule_interval(self.poll, 2.5)
        Clock.schedule_interval(self.heartbeat, 30)
        if self.store.exists("session"):
            self.api.refresh = self.store.get("session")["refresh"]
            self.api.exp = 0
            self.loading = True
            self.bg(self.api.ensure, lambda _: self.enter_app(), self.restore_failed)

    # ---------- helpers ----------
    def notify(self, text):
        text = str(text)[:400]
        try:
            old = getattr(self, "_dialog", None)
            if old:
                old.dismiss()
            self._dialog = MDDialog(
                title="Chatly", text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self._dialog.dismiss())])
            self._dialog.open()
        except Exception:
            Popup(title="Chatly", content=Label(text=text, text_size=(Window.width * .7, None)),
                  size_hint=(.85, .4)).open()

    def bg(self, fn, ok=None, err=None):
        def run():
            try:
                res = fn()
            except Exception as e:
                exc = e
                Clock.schedule_once(lambda dt: (err or self.show_err)(exc))
                return
            if ok:
                Clock.schedule_once(lambda dt: ok(res))
        threading.Thread(target=run, daemon=True).start()

    def show_err(self, e):
        self.loading = False
        self.notify(str(e)[:140])

    def toggle_mode(self):
        self.signup_mode = not self.signup_mode

    def set_me(self, me):
        self.me = me or {}
        self.me_email = self.api.email or ""
        self.me_username = self.me.get("username") or self.api.username
        self.me_name = self.me.get("display_name") or self.me_username
        self.me_initial = initial(self.me_name)
        self.me_color = avatar_color(self.me_username)

    def users_key(self, users):
        return [(u["id"], name_of(u), is_online(u.get("seconds_ago")), u.get("note"),
                 badge_text(u.get("seconds_ago"))) for u in users]

    def user_by_id(self, uid):
        return next((u for u in self.users if u["id"] == uid), None)

    def update_peer_status(self):
        u = self.user_by_id(self.peer) if self.peer else None
        if not u:
            return
        self.peer_name = name_of(u)
        self.peer_initial = initial(self.peer_name)
        self.peer_active = is_online(u.get("seconds_ago"))
        self.peer_status = presence_text(u.get("seconds_ago"))

    def heartbeat(self, dt):
        """Tell the server we are active (others see 'Active now')."""
        if self.api.uid and not self.loading:
            self.bg(self.api.touch, None, lambda e: None)

    def on_resume(self):
        self.heartbeat(0)

    def _on_key(self, window, key, *args):
        """Android back button: go back a screen instead of closing the app."""
        if key == 27 and self.root:
            if self.root.current == "chat":
                self.back()
                return True
            if self.root.current in ("profile", "password"):
                self.back_to_settings()
                return True
            if self.root.current == "settings":
                self.close_settings()
                return True
            if self.root.current == "note":
                self.close_note()
                return True
        return False

    # ---------- auth ----------
    def submit(self):
        url, key = config.SUPABASE_URL, config.SUPABASE_ANON_KEY
        if not url.startswith("https://") or "YOUR-" in url or not key or "YOUR-" in key:
            self.notify("Supabase is not configured in this build. Add the SUPABASE_URL and "
                        "SUPABASE_ANON_KEY secrets on GitHub, then rebuild the app.")
            return
        ids = self.root.ids
        email, pw = ids.email_field.text.strip(), ids.pass_field.text
        if "@" not in email or len(pw) < 6:
            self.notify("Enter a valid email and a password of 6+ characters")
            return
        self.loading = True
        if self.signup_mode:
            name = ids.username_field.text.strip()
            display = ids.display_field.text.strip()
            if not re.fullmatch(r"[A-Za-z0-9_.]{3,24}", name):
                self.loading = False
                self.notify("Username must be 3-24 characters: letters, numbers, _ or .")
                return
            if len(display) > 40:
                self.loading = False
                self.notify("Display name can be up to 40 characters")
                return
            display = display or name
            self.bg(lambda: self.api.sign_up(email, pw, name, display), self.signed_up, self.auth_fail)
        else:
            self.bg(lambda: self.api.sign_in(email, pw), lambda _: self.enter_app(), self.auth_fail)

    def signed_up(self, signed_in):
        if signed_in:
            self.enter_app()
        else:
            self.loading = False
            self.signup_mode = False
            self.notify("Account created. Confirm your email, then sign in.")

    def auth_fail(self, e):
        self.loading = False
        msg = str(e)
        if "database error" in msg.lower():
            msg = "That username is already taken"
        self.notify(msg[:140])

    def restore_failed(self, e):
        self.loading = False
        if isinstance(e, requests.RequestException):
            self.notify("No internet connection. Check your network and reopen the app.")
            return  # keep the saved session
        if self.store.exists("session"):
            self.store.delete("session")

    def enter_app(self):
        self.me_username = self.api.username
        self.me_name = self.api.username
        self.root.ids.pass_field.text = ""

        self.local = LocalDB(os.path.join(self.user_data_dir, f"chat_{self.api.uid}.db"))
        local = self.local
        self.users = local.load_users()
        self.msgs, self.seen, self.unread = {}, set(), {}
        cached_last = local.get_meta("last_id")
        resume_from = int(cached_last) if cached_last else None

        def init():
            users = self.api.users()
            me = self.api.me()
            last = resume_from if resume_from is not None else self.api.latest_incoming_id()
            local.save_users(users)
            local.set_meta("last_id", last)
            try:
                self.api.touch()
            except Exception:
                pass
            return users, last, me

        def done(res):
            self.users, self.last_id, me = res
            self.set_me(me)
            self.loading = False
            self.refresh_contacts()
            self.root.current = "contacts"

        self.bg(init, done)

    def logout(self):
        api = self.api
        threading.Thread(target=api.sign_out, daemon=True).start()
        if self.store.exists("session"):
            self.store.delete("session")
        if self.local:
            local, self.local = self.local, None
            threading.Thread(target=local.destroy, daemon=True).start()
        self.users, self.msgs, self.unread, self.seen = [], {}, {}, set()
        self.peer, self.last_id = None, 0
        self.me, self.me_name, self.peer_status, self.peer_active = {}, "", "", False
        self.root.ids.contact_list.clear_widgets()
        self.root.current = "login"

    # ---------- polling for new messages ----------
    def poll(self, dt):
        if not self.api.uid or self.poll_busy or self.loading:
            return
        self.poll_busy = True
        self.tick += 1

        local = self.local

        def work():
            inc = self.api.incoming(self.last_id)
            users = self.api.users() if self.tick % 6 == 0 else None
            if local:
                if inc:
                    local.save_messages(inc)
                    local.set_meta("last_id", max(m["id"] for m in inc))
                if users is not None:
                    local.save_users(users)
            return inc, users

        def done(res):
            self.poll_busy = False
            inc, users = res
            changed = False
            if users is not None:
                if self.users_key(users) != self.users_key(self.users):
                    changed = True
                self.users = users
                self.update_peer_status()
            for m in inc:
                self.last_id = max(self.last_id, m["id"])
                if m["id"] in self.seen:
                    continue
                self.seen.add(m["id"])
                peer = m["sender"]
                self.msgs.setdefault(peer, []).append(m)
                if peer == self.peer and self.root.current == "chat":
                    self.add_bubble(m)
                else:
                    self.unread[peer] = self.unread.get(peer, 0) + 1
                    changed = True
            if changed and self.root.current == "contacts":
                self.refresh_contacts()

        def fail(e):
            self.poll_busy = False

        self.bg(work, done, fail)

    # ---------- contacts ----------
    def refresh_contacts(self):
        if not self.root:
            return
        q = self.root.ids.search_field.text.strip().lower()
        lst = self.root.ids.contact_list
        lst.clear_widgets()
        rows = []
        for u in self.users:
            name = name_of(u)
            if q and q not in name.lower() and q not in u["username"].lower():
                continue
            last = self.local.last_message(self.api.uid, u["id"]) if self.local and self.api.uid else None
            rows.append((last["id"] if last else 0, name, u, last))
        rows.sort(key=lambda r: (-r[0], r[1].lower()))  # recent chats first
        for _, name, u, last in rows:
            if last and self.prefs.get("previews", True):
                text = " ".join(last["text"].split())
                text = text if len(text) <= 38 else text[:36] + "..."
                sub = ("You: " if last["sender"] == self.api.uid else "") + text
            else:
                sub = "@" + u["username"]
            lst.add_widget(ContactRow(
                name=name, subtitle=sub, initial=initial(name),
                avatar_color=avatar_color(u["username"]), unread=self.unread.get(u["id"], 0),
                online=is_online(u.get("seconds_ago")),
                on_release=lambda x, uid=u["id"], n=name: self.open_chat(uid, n)))
        if not rows:
            lst.add_widget(MDLabel(
                text="No matches" if q else "No one else has joined yet.\nInvite a friend to create an account!",
                halign="center", theme_text_color="Hint", size_hint_y=None, height=dp(140)))
        sv = self.root.ids.rail_sv
        hide = bool(q) or not self.prefs.get("rail", True)  # hidden while searching or if turned off
        sv.height, sv.opacity = (0, 0) if hide else (dp(126), 1)
        if not hide:
            self.refresh_rail()

    def refresh_rail(self):
        """Top strip: your note, then friends who are online / recently active or have a note."""
        rail = self.root.ids.rail
        rail.clear_widgets()
        mine = self.me.get("note") or ""
        rail.add_widget(StoryItem(
            name="Your note", initial=self.me_initial, color=self.me_color,
            note=short(mine, 14) if mine else "What's up?", placeholder=not mine, plus=True,
            on_release=lambda x: self.open_note()))
        people = []
        for u in self.users:
            sec = u.get("seconds_ago")
            if is_online(sec) or u.get("note") or (sec is not None and sec < 86400):
                people.append(u)
        people.sort(key=lambda u: (u.get("seconds_ago") is None, u.get("seconds_ago") or 0))
        for u in people[:20]:
            sec, full = u.get("seconds_ago"), name_of(u)
            rail.add_widget(StoryItem(
                name=short(full.split()[0], 10), initial=initial(full),
                color=avatar_color(u["username"]), note=short(u.get("note") or "", 14),
                online=is_online(sec), badge=badge_text(sec),
                on_release=lambda x, uid=u["id"], n=full: self.open_chat(uid, n)))

    # ---------- chat ----------
    def open_chat(self, uid, name):
        self.peer = uid
        self.unread.pop(uid, None)
        u = self.user_by_id(uid)
        self.peer_name, self.peer_initial = name, initial(name)
        self.peer_color = avatar_color(u["username"] if u else name)
        self.update_peer_status()
        self.root.current = "chat"
        cached = self.local.load_history(self.api.uid, uid) if self.local else []
        if cached:
            self.msgs[uid] = cached
            self.seen.update(m["id"] for m in cached)
        self.rebuild_chat()
        local = self.local

        def fetch():
            rows = self.api.history(uid)
            if local:
                local.save_messages(rows)
            return rows

        self.bg(fetch, lambda rows: self.apply_history(uid, rows))

    def apply_history(self, uid, rows):
        """Show server history; only touch the screen if something changed (no flicker or jump)."""
        if self.peer != uid:
            return
        old_ids = [m["id"] for m in self.msgs.get(uid, [])]
        new_ids = [m["id"] for m in rows]
        self.msgs[uid] = rows
        self.seen.update(new_ids)
        if old_ids == new_ids:
            return  # already showing exactly this
        if new_ids[:len(old_ids)] == old_ids:
            for m in rows[len(old_ids):]:  # only new messages: append them
                self.add_bubble(m)
        else:
            self.rebuild_chat()

    def back(self):
        self.peer = None
        self.root.current = "contacts"
        self.refresh_contacts()

    # ---------- profile ----------
    def open_settings(self):
        ids = self.root.ids
        self._profile_loading = True  # don't treat these programmatic changes as user taps
        ids.active_row.active = self.me.get("show_active") is not False
        ids.rail_row.active = bool(self.prefs.get("rail", True))
        ids.preview_row.active = bool(self.prefs.get("previews", True))
        self._profile_loading = False
        self.root.current = "settings"

    def open_profile(self):
        self.root.ids.name_field.text = self.me.get("display_name") or ""
        self.root.current = "profile"

    def open_password(self):
        self.root.ids.pw_new.text = self.root.ids.pw_confirm.text = ""
        self.root.current = "password"

    def back_to_settings(self):
        for f in (self.root.ids.name_field, self.root.ids.pw_new, self.root.ids.pw_confirm):
            f.focus = False
        self.root.current = "settings"

    def close_settings(self):
        self.root.current = "contacts"
        self.refresh_contacts()

    def save_profile(self):
        name = self.root.ids.name_field.text.strip()
        if len(name) > 40:
            self.notify("Display name can be up to 40 characters")
            return
        self.loading = True

        def done(_):
            self.loading = False
            self.me["display_name"] = name or None
            self.set_me(self.me)
            self.back_to_settings()

        self.bg(lambda: self.api.set_display_name(name), done)

    # ---------- notes (Messenger-style composer) ----------
    def open_note(self):
        ids = self.root.ids
        current = self.me.get("note") or ""
        ids.note_input.text = current
        self.has_note = bool(current)
        self.note_ready = False  # nothing new to share yet
        self.root.current = "note"
        Clock.schedule_once(lambda dt: setattr(ids.note_input, "focus", True), 0.35)

    def close_note(self):
        self.root.ids.note_input.focus = False
        self.root.current = "contacts"
        self.refresh_contacts()

    def on_note_text(self, widget):
        text = widget.text
        if len(text) > 60:
            widget.text = text[:60]  # notes are limited to 60 characters
            return
        t = text.strip()
        self.note_ready = bool(t) and t != (self.me.get("note") or "")

    def share_note(self):
        text = self.root.ids.note_input.text.strip()
        if not text or not self.note_ready:
            return
        self.loading = True

        def done(_):
            self.loading = False
            self.me["note"] = text
            self.close_note()

        self.bg(lambda: self.api.set_note(text), done, self.note_fail)

    def delete_note(self):
        self.loading = True

        def done(_):
            self.loading = False
            self.me["note"] = None
            self.close_note()

        self.bg(lambda: self.api.set_note(""), done, self.note_fail)

    def note_fail(self, e):
        self.loading = False
        msg = str(e)
        if "set_note" in msg or "schema cache" in msg:
            msg = "Notes are not set up in your Supabase project yet. Run update_v3.sql in the SQL Editor."
        self.notify(msg[:200])

    def set_pref(self, key, value):
        """Device-level preferences (kept after log out)."""
        if self._profile_loading:
            return
        self.prefs[key] = bool(value)
        self.store.put("prefs", **self.prefs)
        self.refresh_contacts()

    def change_password(self):
        ids = self.root.ids
        pw, pw2 = ids.pw_new.text, ids.pw_confirm.text
        if len(pw) < 6:
            self.notify("Password must be at least 6 characters")
            return
        if pw != pw2:
            self.notify("The two passwords do not match")
            return
        self.loading = True

        def done(_):
            self.loading = False
            ids.pw_new.text = ids.pw_confirm.text = ""
            self.back_to_settings()
            self.notify("Password updated.")

        self.bg(lambda: self.api.change_password(pw), done)

    def clear_cache(self):
        if self.local:
            self.local.clear_cache()
        self.msgs, self.seen = {}, set()
        self.refresh_contacts()
        self.notify("Saved chats were removed from this phone. They reload from the server when you open them.")

    def confirm_delete_account(self):
        def close(*args):
            dlg.dismiss()

        def go(*args):
            dlg.dismiss()
            self.delete_account()

        dlg = MDDialog(
            title="Delete account?",
            text="This permanently deletes your account, profile and all your messages. "
                 "This cannot be undone.",
            buttons=[MDFlatButton(text="CANCEL", on_release=close),
                     MDFlatButton(text="DELETE", theme_text_color="Custom",
                                  text_color=(0.86, 0.2, 0.25, 1), on_release=go)])
        dlg.open()

    def delete_account(self):
        self.loading = True

        def done(_):
            self.loading = False
            self.logout()
            self.notify("Your account was deleted.")

        def fail(e):
            self.loading = False
            msg = str(e)
            if "delete_my_account" in msg or "schema cache" in msg:
                msg = "Account deletion is not set up yet. Run update_v4.sql in the Supabase SQL Editor."
            self.notify(msg[:200])

        self.bg(self.api.delete_account, done, fail)

    def set_show_active(self, flag):
        if self._profile_loading or not self.api.uid:
            return
        self.me["show_active"] = bool(flag)
        self.bg(lambda: self.api.set_show_active(flag), None, self.show_err)

    def rebuild_chat(self):
        sv, box = self.root.ids.scroll, self.root.ids.msg_list
        sv.opacity = 0  # stay invisible until the list sits at the newest message
        box.clear_widgets()
        sv.scroll_y = 0
        for m in self.msgs.get(self.peer, []):
            self.add_bubble(m, scroll=False)
        Clock.schedule_once(self._reveal_chat, 0.06)

    def _reveal_chat(self, dt):
        sv = self.root.ids.scroll
        sv.scroll_y = 0
        sv.opacity = 1

    def add_bubble(self, m, scroll=True):
        self.root.ids.msg_list.add_widget(Bubble(
            text=m["text"], mine=m["sender"] == self.api.uid, time=fmt_time(m.get("created_at"))))
        if scroll and (m["sender"] == self.api.uid or self.root.ids.scroll.scroll_y < 0.25):
            self.scroll_down()

    def scroll_down(self):
        Clock.schedule_once(lambda dt: setattr(self.root.ids.scroll, "scroll_y", 0), 0)

    def send(self):
        field = self.root.ids.msg_field
        text, peer = field.text.strip(), self.peer
        if not text or not peer:
            return
        field.text = ""
        Clock.schedule_once(lambda dt: setattr(field, "focus", True), 0.05)

        local = self.local

        def push():
            m = self.api.send(peer, text)
            if local:
                local.save_messages([m])
            return m

        def done(m):
            self.seen.add(m["id"])
            self.msgs.setdefault(peer, []).append(m)
            if self.peer == peer:
                self.add_bubble(m)

        def fail(e):
            if not field.text:
                field.text = text
            self.show_err(e)

        self.bg(push, done, fail)


if __name__ == "__main__":
    ChatApp().run()
