import os
import re
import sqlite3
import threading
import time
from datetime import date, datetime

import certifi
import requests
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.storage.jsonstore import JsonStore
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, ScreenManager
from kivy.uix.popup import Popup
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog

import config
from errscreen import make_error_widget

KV = """
#:import NoTransition kivy.uix.screenmanager.NoTransition
#:set PRIMARY (0.094, 0.467, 0.949, 1)
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

<TopBar>:
    size_hint_y: None
    height: dp(56)
    md_bg_color: PRIMARY
    padding: dp(16), 0, dp(4), 0
    Label:
        text: "chatly"
        font_size: "30sp"
        bold: True
        color: WHITE
        halign: "left"
        valign: "middle"
        text_size: self.size
    MDIconButton:
        icon: "magnify"
        pos_hint: {"center_y": .5}
        theme_icon_color: "Custom"
        icon_color: WHITE
        on_release: app.open_search()
    MDIconButton:
        icon: "message-text-outline"
        pos_hint: {"center_y": .5}
        theme_icon_color: "Custom"
        icon_color: WHITE
        on_release: app.go_tab("contacts")

<TabItem>:
    MDIcon:
        icon: root.icon
        size_hint: None, None
        size: dp(28), dp(28)
        pos_hint: {"center_x": .5, "center_y": .55}
        theme_text_color: "Custom"
        text_color: PRIMARY if root.active else MUTED
    MDBoxLayout:
        size_hint: 1, None
        height: dp(3)
        pos_hint: {"x": 0, "y": 0}
        md_bg_color: PRIMARY if root.active else (0, 0, 0, 0)
    PassCard:
        size_hint: None, None
        size: dp(18), dp(18)
        pos_hint: {"center_x": .64, "center_y": .76}
        radius: [dp(9)]
        elevation: 0
        md_bg_color: (0.9, 0.2, 0.25, 1)
        opacity: 1 if root.badge > 0 else 0
        Label:
            text: str(root.badge) if root.badge < 10 else "9+"
            font_size: "10sp"
            bold: True
            color: WHITE
            text_size: self.size
            halign: "center"
            valign: "middle"

<TabBar>:
    size_hint_y: None
    height: dp(50)
    md_bg_color: WHITE
    TabItem:
        icon: "home-variant" if root.current == "feed" else "home-variant-outline"
        active: root.current == "feed"
        on_release: app.go_tab("feed")
    TabItem:
        icon: "forum" if root.current == "communities" else "forum-outline"
        active: root.current == "communities"
        on_release: app.go_tab("communities")
    TabItem:
        icon: "message-text" if root.current == "contacts" else "message-text-outline"
        active: root.current == "contacts"
        badge: app.unread_total
        on_release: app.go_tab("contacts")
    TabItem:
        icon: "account-circle" if root.current == "me" else "account-circle-outline"
        active: root.current == "me"
        on_release: app.go_tab("me")
    TabItem:
        icon: "menu"
        active: root.current == "settings"
        on_release: app.go_tab("settings")

<Chip>:
    size_hint: None, None
    height: dp(34)
    width: cl.texture_size[0] + dp(28)
    PassCard:
        radius: [dp(17)]
        elevation: 0
        md_bg_color: root.accent if root.selected else (0.91, 0.92, 0.94, 1)
        padding: dp(14), 0
        Label:
            id: cl
            text: root.text
            font_size: "13sp"
            bold: True
            color: WHITE if root.selected else INK
            size_hint: None, None
            size: self.texture_size
            pos_hint: {"center_y": .5}

<PersonRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(78)
    padding: dp(14), dp(10)
    spacing: dp(10)
    md_bg_color: (0.95, 0.96, 0.98, 1) if self.state == "down" else WHITE
    AvatarDot:
        size: dp(54), dp(54)
        pos_hint: {"center_y": .5}
        initial: root.initial
        color: root.color
        online: root.online
    MDBoxLayout:
        orientation: "vertical"
        adaptive_height: True
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.name
            font_style: "Subtitle1"
            bold: True
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
        TapBox:
            size_hint: None, None
            size: (pl.texture_size[0] + dp(30), dp(36)) if root.primary else (0, 0)
            pos_hint: {"center_y": .5}
            opacity: 1 if root.primary else 0
            on_release: app.person_primary(root)
            PassCard:
                radius: [dp(18)]
                elevation: 0
                md_bg_color: PRIMARY
                padding: dp(15), 0
                Label:
                    id: pl
                    text: root.primary
                    font_size: "13sp"
                    bold: True
                    color: WHITE
                    size_hint: None, None
                    size: self.texture_size
                    pos_hint: {"center_y": .5}
        TapBox:
            size_hint: None, None
            size: (sl.texture_size[0] + dp(30), dp(36)) if root.secondary else (0, 0)
            pos_hint: {"center_y": .5}
            opacity: 1 if root.secondary else 0
            on_release: app.person_secondary(root)
            PassCard:
                radius: [dp(18)]
                elevation: 0
                md_bg_color: (0.91, 0.92, 0.94, 1)
                padding: dp(15), 0
                Label:
                    id: sl
                    text: root.secondary
                    font_size: "13sp"
                    bold: True
                    color: INK
                    size_hint: None, None
                    size: self.texture_size
                    pos_hint: {"center_y": .5}

<ProfileHeader>:
    orientation: "vertical"
    adaptive_height: True
    md_bg_color: WHITE
    padding: dp(16), dp(22), dp(16), dp(16)
    spacing: dp(8)
    AvatarDot:
        size: dp(96), dp(96)
        pos_hint: {"center_x": .5}
        initial: root.initial
        color: root.color
    MDLabel:
        text: root.name
        halign: "center"
        font_style: "H6"
        bold: True
        theme_text_color: "Custom"
        text_color: INK
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
    MDLabel:
        text: "@" + root.username
        halign: "center"
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: MUTED
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
    MDLabel:
        text: root.bio
        halign: "center"
        font_style: "Body2"
        theme_text_color: "Custom"
        text_color: INK
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
        opacity: 1 if self.text else 0
    MDLabel:
        text: root.hint
        halign: "center"
        font_style: "Body2"
        theme_text_color: "Custom"
        text_color: MUTED
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
        opacity: 1 if self.text else 0
    MDLabel:
        text: root.stats
        halign: "center"
        font_style: "Caption"
        bold: True
        theme_text_color: "Custom"
        text_color: MUTED
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
        opacity: 1 if self.text else 0
    MDBoxLayout:
        size_hint_y: None
        height: dp(46) if (root.primary or root.secondary) else 0
        opacity: 1 if (root.primary or root.secondary) else 0
        spacing: dp(10)
        padding: dp(6), dp(4)
        Widget:
        TapBox:
            size_hint: None, None
            size: (pl.texture_size[0] + dp(30), dp(36)) if root.primary else (0, 0)
            pos_hint: {"center_y": .5}
            opacity: 1 if root.primary else 0
            on_release: root.dispatch("on_main_tap")
            PassCard:
                radius: [dp(18)]
                elevation: 0
                md_bg_color: PRIMARY
                padding: dp(15), 0
                Label:
                    id: pl
                    text: root.primary
                    font_size: "13sp"
                    bold: True
                    color: WHITE
                    size_hint: None, None
                    size: self.texture_size
                    pos_hint: {"center_y": .5}
        TapBox:
            size_hint: None, None
            size: (sl.texture_size[0] + dp(30), dp(36)) if root.secondary else (0, 0)
            pos_hint: {"center_y": .5}
            opacity: 1 if root.secondary else 0
            on_release: root.dispatch("on_alt_tap")
            PassCard:
                radius: [dp(18)]
                elevation: 0
                md_bg_color: (0.91, 0.92, 0.94, 1)
                padding: dp(15), 0
                Label:
                    id: sl
                    text: root.secondary
                    font_size: "13sp"
                    bold: True
                    color: INK
                    size_hint: None, None
                    size: self.texture_size
                    pos_hint: {"center_y": .5}
        Widget:

<ThreadCard>:
    orientation: "vertical"
    adaptive_height: True
    md_bg_color: (0.95, 0.96, 0.98, 1) if self.state == "down" else WHITE
    padding: dp(14), dp(12), dp(14), dp(4)
    spacing: dp(6)
    MDLabel:
        text: root.community
        font_style: "Caption"
        bold: True
        theme_text_color: "Custom"
        text_color: PRIMARY
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
    MDLabel:
        text: root.title
        font_style: "Subtitle1"
        bold: True
        theme_text_color: "Custom"
        text_color: INK
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
    MDLabel:
        text: root.snippet
        font_style: "Body2"
        theme_text_color: "Custom"
        text_color: MUTED
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
        opacity: 1 if self.text else 0
    MDBoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(4)
        TapBox:
            size_hint: None, None
            size: dp(70), dp(34)
            pos_hint: {"center_y": .5}
            on_release: app.vote_thread_card(root)
            MDIcon:
                icon: "arrow-up-bold" if root.voted else "arrow-up-bold-outline"
                size_hint: None, None
                size: dp(22), dp(22)
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: PRIMARY if root.voted else MUTED
            Label:
                text: " " + str(root.votes)
                font_size: "14sp"
                bold: True
                color: PRIMARY if root.voted else MUTED
                size_hint_x: None
                width: self.texture_size[0]
        MDIcon:
            icon: "comment-outline"
            size_hint: None, None
            size: dp(20), dp(20)
            pos_hint: {"center_y": .5}
            theme_text_color: "Custom"
            text_color: MUTED
        Label:
            text: " " + str(root.replies)
            font_size: "14sp"
            color: MUTED
            size_hint_x: None
            width: self.texture_size[0]
        Widget:
        MDLabel:
            text: root.name + " · " + root.meta
            font_style: "Caption"
            halign: "right"
            shorten: True
            max_lines: 1
            theme_text_color: "Custom"
            text_color: MUTED
            size_hint: None, None
            width: dp(150)
            text_size: self.width, None
            height: self.texture_size[1]
            pos_hint: {"center_y": .5}

<ReplyCard>:
    orientation: "vertical"
    adaptive_height: True
    md_bg_color: WHITE
    padding: dp(14), dp(10), dp(14), dp(2)
    spacing: dp(4)
    TapBox:
        size_hint_y: None
        height: dp(40)
        spacing: dp(10)
        on_release: app.open_user(root.author_id)
        AvatarDot:
            size: dp(32), dp(32)
            pos_hint: {"center_y": .5}
            initial: root.initial
            color: root.color
        MDLabel:
            text: root.name + " · " + root.meta
            font_style: "Caption"
            bold: True
            theme_text_color: "Custom"
            text_color: INK
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1]
            pos_hint: {"center_y": .5}
    MDLabel:
        text: root.body
        font_style: "Body1"
        theme_text_color: "Custom"
        text_color: INK
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
    MDBoxLayout:
        size_hint_y: None
        height: dp(38)
        TapBox:
            size_hint: None, None
            size: dp(70), dp(34)
            pos_hint: {"center_y": .5}
            on_release: app.vote_reply_card(root)
            MDIcon:
                icon: "arrow-up-bold" if root.voted else "arrow-up-bold-outline"
                size_hint: None, None
                size: dp(22), dp(22)
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: PRIMARY if root.voted else MUTED
            Label:
                text: " " + str(root.votes)
                font_size: "14sp"
                bold: True
                color: PRIMARY if root.voted else MUTED
                size_hint_x: None
                width: self.texture_size[0]
        Widget:
        TapBox:
            size_hint: None, None
            size: (dp(44), dp(34)) if root.can_delete else (0, 0)
            pos_hint: {"center_y": .5}
            opacity: 1 if root.can_delete else 0
            disabled: not root.can_delete
            on_release: app.confirm_delete_reply(root)
            MDIcon:
                icon: "delete-outline"
                size_hint: None, None
                size: dp(22), dp(22)
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: MUTED

<CommunityRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(78)
    padding: dp(14), dp(10)
    spacing: dp(12)
    md_bg_color: (0.95, 0.96, 0.98, 1) if self.state == "down" else WHITE
    AvatarDot:
        size: dp(52), dp(52)
        pos_hint: {"center_y": .5}
        initial: root.initial
        color: root.color
    MDBoxLayout:
        orientation: "vertical"
        adaptive_height: True
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.name
            font_style: "Subtitle1"
            bold: True
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
    TapBox:
        size_hint: None, None
        size: jl.texture_size[0] + dp(30), dp(36)
        pos_hint: {"center_y": .5}
        on_release: app.toggle_member(root)
        PassCard:
            radius: [dp(18)]
            elevation: 0
            md_bg_color: (0.91, 0.92, 0.94, 1) if root.joined else PRIMARY
            padding: dp(15), 0
            Label:
                id: jl
                text: root.action
                font_size: "13sp"
                bold: True
                color: INK if root.joined else WHITE
                size_hint: None, None
                size: self.texture_size
                pos_hint: {"center_y": .5}

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
    MDBoxLayout:
        size_hint: None, None
        size: (dp(44), dp(24)) if root.streak > 1 else (0, 0)
        opacity: 1 if root.streak > 1 else 0
        pos_hint: {"center_y": .5}
        spacing: dp(2)
        MDIcon:
            icon: "fire"
            size_hint: None, None
            size: dp(20), dp(20)
            pos_hint: {"center_y": .5}
            theme_text_color: "Custom"
            text_color: (0.98, 0.5, 0.1, 1)
        Label:
            text: str(root.streak)
            font_size: "13sp"
            bold: True
            color: (0.98, 0.5, 0.1, 1)
            size_hint: None, None
            size: self.texture_size
            pos_hint: {"center_y": .5}
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
    transition: NoTransition()

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
                    text: "Communities, threads and messages"
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
                                hint_text: "Display name (shown to other members)"
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
        name: "feed"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            TopBar:
            TabBar:
                current: "feed"
            ScrollView:
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(8)
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(66)
                        md_bg_color: WHITE
                        padding: dp(12), dp(10)
                        spacing: dp(10)
                        AvatarDot:
                            size: dp(42), dp(42)
                            pos_hint: {"center_y": .5}
                            initial: app.me_initial
                            color: app.me_color
                        TapBox:
                            on_release: app.open_compose()
                            PassCard:
                                radius: [dp(21)]
                                elevation: 0
                                md_bg_color: (0.94, 0.945, 0.955, 1)
                                padding: dp(16), 0
                                Label:
                                    text: "Start a thread..."
                                    font_size: "15sp"
                                    color: MUTED
                                    size_hint: None, None
                                    size: self.texture_size
                                    pos_hint: {"center_y": .5}
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(54)
                        md_bg_color: WHITE
                        padding: dp(12), dp(10)
                        spacing: dp(8)
                        Chip:
                            text: "New"
                            selected: app.feed_sort == "new"
                            on_release: app.set_sort("new")
                        Chip:
                            text: "Top"
                            selected: app.feed_sort == "top"
                            on_release: app.set_sort("top")
                        Widget:
                    MDBoxLayout:
                        id: feed_list
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(8)

    MDScreen:
        name: "communities"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            TopBar:
            TabBar:
                current: "communities"
            MDBoxLayout:
                size_hint_y: None
                height: dp(60)
                md_bg_color: WHITE
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
                        id: comm_search
                        hint_text: "Search communities"
                        multiline: False
                        background_color: 0, 0, 0, 0
                        background_normal: ""
                        background_active: ""
                        foreground_color: INK
                        hint_text_color: MUTED
                        cursor_color: PRIMARY
                        font_size: "16sp"
                        padding: [0, dp(12), 0, dp(12)]
                        on_text: app.render_communities()
            TapBox:
                size_hint_y: None
                height: dp(52)
                on_release: app.open_new_community()
                PassCard:
                    md_bg_color: WHITE
                    padding: dp(16), 0
                    spacing: dp(10)
                    MDIcon:
                        icon: "plus-circle-outline"
                        size_hint: None, None
                        size: dp(26), dp(26)
                        pos_hint: {"center_y": .5}
                        theme_text_color: "Custom"
                        text_color: PRIMARY
                    Label:
                        text: "Create a community"
                        font_size: "15sp"
                        bold: True
                        color: PRIMARY
                        size_hint: None, None
                        size: self.texture_size
                        pos_hint: {"center_y": .5}
            ScrollView:
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    id: comm_list
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(1)

    MDScreen:
        name: "contacts"
        md_bg_color: WHITE
        MDBoxLayout:
            orientation: "vertical"
            TopBar:
            TabBar:
                current: "contacts"
            MDBoxLayout:
                size_hint_y: None
                height: dp(60)
                padding: dp(16), dp(6), dp(8), dp(6)
                spacing: dp(4)
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
                        hint_text: "Search conversations"
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
                MDIconButton:
                    icon: "message-plus-outline"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: PRIMARY
                    on_release: app.open_people()
            ScrollView:
                bar_width: 0
                MDBoxLayout:
                    id: contact_list
                    orientation: "vertical"
                    adaptive_height: True

    MDScreen:
        name: "me"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            TopBar:
            TabBar:
                current: "me"
            ScrollView:
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(8)
                    ProfileHeader:
                        initial: app.me_initial
                        color: app.me_color
                        name: app.me_name
                        username: app.me_username
                        bio: app.me_bio
                        stats: app.me_stats
                        primary: "Edit profile"
                        secondary: "New thread"
                        on_main_tap: app.open_profile()
                        on_alt_tap: app.open_compose()
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(14), dp(8), dp(14), 0
                        SectionLabel:
                            text: "MY THREADS"
                    MDBoxLayout:
                        id: me_posts
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(8)

    MDScreen:
        name: "user"
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
                    on_release: app.close_user()
                MDLabel:
                    text: app.view_name
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
                    spacing: dp(8)
                    ProfileHeader:
                        initial: app.view_initial
                        color: app.view_color
                        name: app.view_name
                        username: app.view_username
                        bio: app.view_bio
                        hint: app.view_hint
                        stats: app.view_stats
                        primary: app.view_primary
                        secondary: app.view_secondary
                        on_main_tap: app.view_primary_tap()
                        on_alt_tap: app.view_secondary_tap()
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(14), dp(8), dp(14), 0
                        SectionLabel:
                            text: "THREADS"
                    MDBoxLayout:
                        id: user_posts
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(8)

    MDScreen:
        name: "settings"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            TopBar:
            TabBar:
                current: "settings"
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
                            subtitle: "Members can see when you are online"
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
                            text: "View error log"
                            theme_text_color: "Custom"
                            text_color: PRIMARY
                            on_release: app.view_error_log()
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
                        MDTextField:
                            id: bio_field
                            hint_text: "Bio (up to 150 characters)"
                            mode: "rectangle"
                        MDLabel:
                            text: "Your name and bio are visible to everyone on the forum."
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
        name: "people"
        md_bg_color: WHITE
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
                    on_release: app.close_people()
                MDLabel:
                    text: "New message"
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
                        id: people_search
                        hint_text: "Find people"
                        multiline: False
                        background_color: 0, 0, 0, 0
                        background_normal: ""
                        background_active: ""
                        foreground_color: INK
                        hint_text_color: MUTED
                        cursor_color: PRIMARY
                        font_size: "16sp"
                        padding: [0, dp(12), 0, dp(12)]
                        on_text: app.refresh_people()
            ScrollView:
                bar_width: 0
                MDBoxLayout:
                    id: people_list
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(1)

    MDScreen:
        name: "community"
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
                    on_release: app.close_community()
                MDLabel:
                    text: app.comm_name
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
                    spacing: dp(8)
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        padding: dp(16), dp(20), dp(16), dp(16)
                        spacing: dp(8)
                        AvatarDot:
                            size: dp(72), dp(72)
                            pos_hint: {"center_x": .5}
                            initial: app.comm_initial
                            color: app.comm_color
                        MDLabel:
                            text: app.comm_desc
                            font_style: "Body2"
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        MDLabel:
                            text: app.comm_members
                            font_style: "Caption"
                            bold: True
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: MUTED
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(46)
                            spacing: dp(10)
                            padding: dp(6), dp(4)
                            Widget:
                            TapBox:
                                size_hint: None, None
                                size: dp(104), dp(38)
                                pos_hint: {"center_y": .5}
                                on_release: app.comm_toggle()
                                PassCard:
                                    radius: [dp(19)]
                                    elevation: 0
                                    md_bg_color: (0.91, 0.92, 0.94, 1) if app.comm_joined else PRIMARY
                                    Label:
                                        text: app.comm_action
                                        font_size: "15sp"
                                        bold: True
                                        color: INK if app.comm_joined else WHITE
                                        text_size: self.size
                                        halign: "center"
                                        valign: "middle"
                            TapBox:
                                size_hint: None, None
                                size: dp(116), dp(38)
                                pos_hint: {"center_y": .5}
                                on_release: app.open_compose(app.comm_id)
                                PassCard:
                                    radius: [dp(19)]
                                    elevation: 0
                                    md_bg_color: PRIMARY
                                    Label:
                                        text: "New thread"
                                        font_size: "15sp"
                                        bold: True
                                        color: WHITE
                                        text_size: self.size
                                        halign: "center"
                                        valign: "middle"
                            Widget:
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(14), dp(8), dp(14), 0
                        SectionLabel:
                            text: "THREADS"
                    MDBoxLayout:
                        id: comm_threads
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(8)

    MDScreen:
        name: "thread"
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
                    on_release: app.close_thread()
                MDLabel:
                    text: "Thread"
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
                id: thread_scroll
                bar_width: 0
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(8)
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        padding: dp(16), dp(14), dp(16), dp(6)
                        spacing: dp(8)
                        TapBox:
                            size_hint_y: None
                            height: dp(22)
                            on_release: app.open_thread_community()
                            MDLabel:
                                text: app.thread_community
                                font_style: "Caption"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: PRIMARY
                                size_hint_y: None
                                text_size: self.width, None
                                height: self.texture_size[1]
                                pos_hint: {"center_y": .5}
                        MDLabel:
                            text: app.thread_title
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        TapBox:
                            size_hint_y: None
                            height: dp(44)
                            spacing: dp(10)
                            on_release: app.open_user(app.thread_author_id)
                            AvatarDot:
                                size: dp(36), dp(36)
                                pos_hint: {"center_y": .5}
                                initial: app.thread_initial
                                color: app.thread_color
                            MDLabel:
                                text: app.thread_name + " · " + app.thread_meta
                                font_style: "Caption"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: MUTED
                                size_hint_y: None
                                text_size: self.width, None
                                height: self.texture_size[1]
                                pos_hint: {"center_y": .5}
                        MDLabel:
                            text: app.thread_body
                            font_style: "Body1"
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(44)
                            spacing: dp(6)
                            TapBox:
                                size_hint: None, None
                                size: dp(84), dp(34)
                                pos_hint: {"center_y": .5}
                                on_release: app.vote_thread_page()
                                MDIcon:
                                    icon: "arrow-up-bold" if app.thread_voted else "arrow-up-bold-outline"
                                    size_hint: None, None
                                    size: dp(22), dp(22)
                                    pos_hint: {"center_y": .5}
                                    theme_text_color: "Custom"
                                    text_color: PRIMARY if app.thread_voted else MUTED
                                Label:
                                    text: " " + str(app.thread_votes)
                                    font_size: "14sp"
                                    bold: True
                                    color: PRIMARY if app.thread_voted else MUTED
                                    size_hint_x: None
                                    width: self.texture_size[0]
                            MDIcon:
                                icon: "comment-outline"
                                size_hint: None, None
                                size: dp(22), dp(22)
                                pos_hint: {"center_y": .5}
                                theme_text_color: "Custom"
                                text_color: MUTED
                            Label:
                                text: " " + str(app.thread_replies)
                                font_size: "14sp"
                                color: MUTED
                                size_hint_x: None
                                width: self.texture_size[0]
                            Widget:
                            TapBox:
                                size_hint: None, None
                                size: (dp(48), dp(34)) if app.thread_can_delete else (0, 0)
                                pos_hint: {"center_y": .5}
                                opacity: 1 if app.thread_can_delete else 0
                                disabled: not app.thread_can_delete
                                on_release: app.confirm_delete_thread()
                                MDIcon:
                                    icon: "delete-outline"
                                    size_hint: None, None
                                    size: dp(22), dp(22)
                                    pos_hint: {"center_y": .5}
                                    theme_text_color: "Custom"
                                    text_color: MUTED
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(14), dp(8), dp(14), 0
                        SectionLabel:
                            text: "REPLIES"
                    MDBoxLayout:
                        id: reply_list
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(1)
            MDBoxLayout:
                size_hint_y: None
                height: dp(68)
                md_bg_color: WHITE
                padding: dp(12), dp(10)
                spacing: dp(10)
                MDCard:
                    radius: [dp(24)]
                    elevation: 0
                    md_bg_color: (0.94, 0.945, 0.955, 1)
                    padding: dp(18), 0
                    TextInput:
                        id: reply_input
                        hint_text: "Write a reply..."
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
                        on_text_validate: app.send_reply()
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
                        on_release: app.send_reply()

    MDScreen:
        name: "compose"
        md_bg_color: WHITE
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                padding: dp(8), dp(10), dp(14), dp(10)
                MDIconButton:
                    icon: "close"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: INK
                    on_release: app.close_compose()
                MDLabel:
                    text: "New thread"
                    halign: "center"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                TapBox:
                    size_hint: None, None
                    size: dp(76), dp(40)
                    pos_hint: {"center_y": .5}
                    on_release: app.submit_thread()
                    PassCard:
                        radius: [dp(20)]
                        elevation: 0
                        md_bg_color: PRIMARY if app.thread_ready else (0.9, 0.91, 0.93, 1)
                        Label:
                            text: "Post"
                            font_size: "15sp"
                            bold: True
                            color: WHITE if app.thread_ready else (0.6, 0.62, 0.66, 1)
                            text_size: self.size
                            halign: "center"
                            valign: "middle"
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
                    padding: dp(14)
                    spacing: dp(10)
                    SectionLabel:
                        text: "COMMUNITY"
                    ScrollView:
                        size_hint_y: None
                        height: dp(34)
                        bar_width: 0
                        do_scroll_y: False
                        MDBoxLayout:
                            id: comp_comms
                            orientation: "horizontal"
                            adaptive_width: True
                            size_hint_y: None
                            height: dp(34)
                            spacing: dp(8)
                    SectionLabel:
                        text: "TITLE"
                    MDCard:
                        size_hint_y: None
                        height: dp(46)
                        radius: [dp(23)]
                        elevation: 0
                        md_bg_color: (0.94, 0.945, 0.955, 1)
                        padding: dp(16), dp(4)
                        TextInput:
                            id: thread_title_input
                            hint_text: "A clear, short title"
                            multiline: False
                            background_color: 0, 0, 0, 0
                            background_normal: ""
                            background_active: ""
                            foreground_color: INK
                            hint_text_color: MUTED
                            cursor_color: PRIMARY
                            font_size: "16sp"
                            padding: [0, dp(12), 0, dp(12)]
                            on_text: app.typed_title(self)
                    SectionLabel:
                        text: "DETAILS"
                    MDCard:
                        size_hint_y: None
                        height: dp(220)
                        radius: [dp(18)]
                        elevation: 0
                        md_bg_color: (0.94, 0.945, 0.955, 1)
                        padding: dp(16), dp(4)
                        TextInput:
                            id: thread_body_input
                            hint_text: "What do you want to talk about?"
                            multiline: True
                            background_color: 0, 0, 0, 0
                            background_normal: ""
                            background_active: ""
                            foreground_color: INK
                            hint_text_color: MUTED
                            cursor_color: PRIMARY
                            font_size: "16sp"
                            padding: [0, dp(12), 0, dp(12)]
                            on_text: app.typed_body(self)
                    MDLabel:
                        text: app.thread_chars
                        font_style: "Caption"
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]

    MDScreen:
        name: "newcommunity"
        md_bg_color: WHITE
        MDBoxLayout:
            orientation: "vertical"
            MDBoxLayout:
                size_hint_y: None
                height: dp(64)
                padding: dp(8), dp(10), dp(14), dp(10)
                MDIconButton:
                    icon: "close"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: INK
                    on_release: app.close_new_community()
                MDLabel:
                    text: "New community"
                    halign: "center"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                TapBox:
                    size_hint: None, None
                    size: dp(84), dp(40)
                    pos_hint: {"center_y": .5}
                    on_release: app.submit_community()
                    PassCard:
                        radius: [dp(20)]
                        elevation: 0
                        md_bg_color: PRIMARY if app.nc_ready else (0.9, 0.91, 0.93, 1)
                        Label:
                            text: "Create"
                            font_size: "15sp"
                            bold: True
                            color: WHITE if app.nc_ready else (0.6, 0.62, 0.66, 1)
                            text_size: self.size
                            halign: "center"
                            valign: "middle"
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
                    padding: dp(14)
                    spacing: dp(10)
                    SectionLabel:
                        text: "NAME"
                    MDCard:
                        size_hint_y: None
                        height: dp(46)
                        radius: [dp(23)]
                        elevation: 0
                        md_bg_color: (0.94, 0.945, 0.955, 1)
                        padding: dp(16), dp(4)
                        TextInput:
                            id: nc_name
                            hint_text: "For example: Photography"
                            multiline: False
                            background_color: 0, 0, 0, 0
                            background_normal: ""
                            background_active: ""
                            foreground_color: INK
                            hint_text_color: MUTED
                            cursor_color: PRIMARY
                            font_size: "16sp"
                            padding: [0, dp(12), 0, dp(12)]
                            on_text: app.typed_community(self, 30)
                    SectionLabel:
                        text: "DESCRIPTION (OPTIONAL)"
                    MDCard:
                        size_hint_y: None
                        height: dp(130)
                        radius: [dp(18)]
                        elevation: 0
                        md_bg_color: (0.94, 0.945, 0.955, 1)
                        padding: dp(16), dp(4)
                        TextInput:
                            id: nc_desc
                            hint_text: "What is this community about?"
                            multiline: True
                            background_color: 0, 0, 0, 0
                            background_normal: ""
                            background_active: ""
                            foreground_color: INK
                            hint_text_color: MUTED
                            cursor_color: PRIMARY
                            font_size: "16sp"
                            padding: [0, dp(12), 0, dp(12)]
                            on_text: app.typed_community(self, 200)
                    MDLabel:
                        text: "Anyone can join and read. You will be the moderator and can remove threads and replies in your community."
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]

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


def split_kv(kv):
    """Split the layout text into style rules and one block per page, so one bad part cannot stop the app."""
    root_at = kv.index("MDScreenManager:")
    head, body = kv[:root_at], kv[root_at:]
    directives = [ln for ln in head.splitlines() if ln.startswith("#:")]
    rules_text = "\n".join(ln for ln in head.splitlines() if not ln.startswith("#:"))
    rules = [r for r in re.split(r"(?m)^(?=<\w+>:)", rules_text) if r.strip()]
    starts = [m.start() for m in re.finditer(r"(?m)^    MDScreen:\n", body)]
    screens = []
    for i, st in enumerate(starts):
        block = body[st: starts[i + 1] if i + 1 < len(starts) else len(body)]
        name = re.search(r'name: "(\w+)"', block).group(1)
        text = "\n".join(ln[4:] if ln.startswith("    ") else ln for ln in block.rstrip("\n").splitlines()) + "\n"
        screens.append((name, text))
    return directives, rules, screens


KV_DIRECTIVES, KV_RULES, KV_SCREENS = split_kv(KV)
SCREEN_NAMES = [n for n, _ in KV_SCREENS]


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





def age_text(sec):
    if sec is None:
        return ""
    if sec < 60:
        return "Just now"
    m = int(sec // 60)
    if m < 60:
        return f"{m}m"
    h = m // 60
    return f"{h}h" if h < 24 else f"{h // 24}d"





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

    def users(self):
        """Everyone on the forum (for messaging), with 'active' status."""
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_people", json={})
            return [{"id": r["id"], "username": r["username"], "display_name": r.get("display_name"),
                     "seconds_ago": r.get("seconds_ago")} for r in rows or []]
        except RuntimeError:
            rows = self._req("GET", "/rest/v1/profiles", params={"select": "id,username", "order": "username"})
            return [{"id": r["id"], "username": r["username"], "display_name": None, "seconds_ago": None}
                    for r in rows if r["id"] != self.uid]

    def conversations(self):
        """{partner id: latest message} for everyone you have talked to."""
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_conversations", json={}) or []
        except RuntimeError:
            return {}
        return {r["partner"]: {"id": r["last_id"], "sender": r["sender"], "text": r["last_text"]} for r in rows}

    def communities(self):
        return self._req("POST", "/rest/v1/rpc/get_communities", json={}) or []

    def create_community(self, name, description):
        return self._req("POST", "/rest/v1/rpc/create_community", json={"p_name": name, "p_description": description or None})

    def join_community(self, cid):
        self._req("POST", "/rest/v1/rpc/join_community", json={"p_id": int(cid)})

    def leave_community(self, cid):
        self._req("POST", "/rest/v1/rpc/leave_community", json={"p_id": int(cid)})

    def threads(self, community=None, author=None, sort="new", joined_only=False):
        payload = {"p_sort": sort, "p_joined_only": bool(joined_only), "p_limit": 30}
        if community:
            payload["p_community"] = int(community)
        if author:
            payload["p_author"] = author
        return self._req("POST", "/rest/v1/rpc/get_threads", json=payload) or []

    def thread(self, tid):
        rows = self._req("POST", "/rest/v1/rpc/get_thread", json={"p_thread": int(tid)})
        return rows[0] if rows else None

    def replies(self, tid):
        return self._req("POST", "/rest/v1/rpc/get_replies", json={"p_thread": int(tid)}) or []

    def create_thread(self, cid, title, body):
        return self._req("POST", "/rest/v1/rpc/create_thread", json={"p_community": int(cid), "p_title": title, "p_body": body})

    def create_reply(self, tid, body):
        return self._req("POST", "/rest/v1/rpc/create_reply", json={"p_thread": int(tid), "p_body": body})

    def delete_thread(self, tid):
        self._req("POST", "/rest/v1/rpc/delete_thread", json={"p_thread": int(tid)})

    def delete_reply(self, rid):
        self._req("POST", "/rest/v1/rpc/delete_reply", json={"p_reply": int(rid)})

    def toggle_thread_vote(self, tid):
        rows = self._req("POST", "/rest/v1/rpc/toggle_thread_vote", json={"p_thread": int(tid)})
        return rows[0] if rows else {}

    def toggle_reply_vote(self, rid):
        rows = self._req("POST", "/rest/v1/rpc/toggle_reply_vote", json={"p_reply": int(rid)})
        return rows[0] if rows else {}

    def change_password(self, new_password):
        self._req("PUT", "/auth/v1/user", json={"password": new_password})

    def delete_account(self):
        self._req("POST", "/rest/v1/rpc/delete_my_account", json={})

    def profile(self, uid):
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_profile", json={"p_user": uid})
            return rows[0] if rows else {}
        except RuntimeError:
            return {}  # friends update not installed yet

    def set_bio(self, text):
        self._req("POST", "/rest/v1/rpc/set_bio", json={"p_bio": text})

    def streaks(self):
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_streaks", json={})
            return {r["friend"]: int(r["days"]) for r in rows or []}
        except RuntimeError:
            return {}  # the streaks update (update_v7.sql) has not been run

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
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT NOT NULL, display_name TEXT, status TEXT);
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY, sender TEXT NOT NULL, receiver TEXT NOT NULL,
                    text TEXT NOT NULL, created_at TEXT);
                CREATE INDEX IF NOT EXISTS idx_pair ON messages(sender, receiver, id);
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
            """)
            cols = [r[1] for r in self.conn.execute("PRAGMA table_info(users)")]
            if "display_name" not in cols:  # cache created by an older app version
                self.conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
            if "status" not in cols:
                self.conn.execute("ALTER TABLE users ADD COLUMN status TEXT")

    def save_users(self, users):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM users")
            self.conn.executemany("INSERT INTO users(id, username, display_name, status) VALUES(?, ?, ?, ?)",
                                  [(u["id"], u["username"], u.get("display_name"), u.get("status")) for u in users])

    def load_users(self):
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, username, display_name, status FROM users ORDER BY COALESCE(display_name, username)").fetchall()
        return [{"id": r["id"], "username": r["username"], "display_name": r["display_name"],
                 "seconds_ago": None, "status": r["status"] or "friends", "mutual": 0} for r in rows]

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
    """Keeps the app alive on unexpected errors, logs them, and shows each distinct error once a minute."""
    seen = {}

    def handle_exception(self, inst):
        import traceback
        tb = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
        try:
            app = MDApp.get_running_app()
            app.log_crash(tb)
            where = ""
            for fr in reversed(traceback.extract_tb(inst.__traceback__)):
                if fr.filename.endswith(("chatly_app.py", "main.py")):
                    where = f" (line {fr.lineno}, in {fr.name})"
                    break
            last = f"{type(inst).__name__}: {inst}{where}"
            now = time.time()
            if now - CrashCatcher.seen.get(last, 0) > 60:  # the same error repeating must not spam dialogs
                CrashCatcher.seen[last] = now
                Clock.schedule_once(lambda dt: app.notify(
                    "Unexpected error: " + last + "\n\nDetails: Menu > Settings > About > View error log."))
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


class DummyWidget(MDBoxLayout):
    """Stand-in for a widget on a page that failed to load, so the rest of the app keeps working."""
    text = ""
    active = False
    focus = False
    scroll_y = 0


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


class PersonRow(ButtonBehavior, MDBoxLayout):
    """A member in a list (for example New message), with up to two action buttons."""
    uid = StringProperty("")
    name = StringProperty("")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    subtitle = StringProperty("")
    online = BooleanProperty(False)
    status = StringProperty("none")
    primary = StringProperty("")
    secondary = StringProperty("")


class ProfileHeader(MDBoxLayout):
    """Avatar, name, bio, stats and two buttons; used for your own profile and for other people's."""
    __events__ = ("on_main_tap", "on_alt_tap")  # NOT on_primary/on_secondary: Kivy would treat those as handlers for the primary/secondary properties
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    name = StringProperty("")
    username = StringProperty("")
    bio = StringProperty("")
    hint = StringProperty("")
    stats = StringProperty("")
    primary = StringProperty("")
    secondary = StringProperty("")

    def on_main_tap(self):
        pass

    def on_alt_tap(self):
        pass


class TopBar(MDBoxLayout):
    """Blue Facebook-Lite-style bar with the app name and quick icons."""


class TabBar(MDBoxLayout):
    """Icon tab row under the top bar (Home, Chats, People, Menu)."""
    current = StringProperty("")


class TabItem(ButtonBehavior, MDFloatLayout):
    icon = StringProperty("")
    active = BooleanProperty(False)
    badge = NumericProperty(0)


class Chip(ButtonBehavior, MDBoxLayout):
    """Pill-shaped choice (sorting, picking a community)."""
    text = StringProperty("")
    selected = BooleanProperty(False)
    accent = ListProperty([0.094, 0.467, 0.949, 1])




class MenuRow(ButtonBehavior, MDBoxLayout):
    """A tappable settings row: icon, title, subtitle and a chevron."""
    icon = StringProperty("")
    title = StringProperty("")
    subtitle = StringProperty("")


class ThreadCard(ButtonBehavior, MDBoxLayout):
    """A thread in a list: community, title, snippet, votes, replies."""
    tid = NumericProperty(0)
    community_id = NumericProperty(0)
    community = StringProperty("")
    author_id = StringProperty("")
    name = StringProperty("")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    meta = StringProperty("")
    title = StringProperty("")
    snippet = StringProperty("")
    votes = NumericProperty(0)
    replies = NumericProperty(0)
    voted = BooleanProperty(False)


class ReplyCard(MDBoxLayout):
    rid = NumericProperty(0)
    author_id = StringProperty("")
    name = StringProperty("")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    meta = StringProperty("")
    body = StringProperty("")
    votes = NumericProperty(0)
    voted = BooleanProperty(False)
    can_delete = BooleanProperty(False)


class CommunityRow(ButtonBehavior, MDBoxLayout):
    cid = NumericProperty(0)
    name = StringProperty("")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    subtitle = StringProperty("")
    joined = BooleanProperty(False)
    action = StringProperty("Join")


class TapBox(ButtonBehavior, MDBoxLayout):
    """A plain tappable container."""



class ContactRow(ButtonBehavior, MDBoxLayout):
    name = StringProperty("")
    subtitle = StringProperty("")
    initial = StringProperty("?")
    avatar_color = ListProperty([0, 0.52, 1, 1])
    unread = NumericProperty(0)
    streak = NumericProperty(0)
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
    unread_total = NumericProperty(0)
    me_bio = StringProperty("")
    me_stats = StringProperty("")
    view_uid = StringProperty("")
    view_name = StringProperty("")
    view_username = StringProperty("")
    view_initial = StringProperty("?")
    view_color = ListProperty([0, 0.52, 1, 1])
    view_bio = StringProperty("")
    view_hint = StringProperty("")
    view_stats = StringProperty("")
    view_primary = StringProperty("")
    view_secondary = StringProperty("")
    feed_sort = StringProperty("new")
    comm_id = NumericProperty(0)
    comm_name = StringProperty("")
    comm_initial = StringProperty("?")
    comm_color = ListProperty([0, 0.52, 1, 1])
    comm_desc = StringProperty("")
    comm_members = StringProperty("")
    comm_joined = BooleanProperty(False)
    comm_action = StringProperty("Join")
    thread_id = NumericProperty(0)
    thread_comm_id = NumericProperty(0)
    thread_community = StringProperty("")
    thread_title = StringProperty("")
    thread_body = StringProperty("")
    thread_meta = StringProperty("")
    thread_author_id = StringProperty("")
    thread_name = StringProperty("")
    thread_initial = StringProperty("?")
    thread_color = ListProperty([0, 0.52, 1, 1])
    thread_votes = NumericProperty(0)
    thread_voted = BooleanProperty(False)
    thread_replies = NumericProperty(0)
    thread_can_delete = BooleanProperty(False)
    compose_comm = NumericProperty(0)
    thread_ready = BooleanProperty(False)
    thread_chars = StringProperty("0/2000")
    nc_ready = BooleanProperty(False)

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
        self.prefs = {"previews": True}
        if self.store.exists("prefs"):
            self.prefs.update(self.store.get("prefs"))
        self.feed_req, self.feed_loaded, self.chat_from, self.user_from = 0, False, "feed", "feed"
        self.comm_req, self.comm_from, self.thread_from = 0, "communities", "feed"
        self.compose_from, self.people_from = "feed", "contacts"
        self.communities, self.joined, self.forum_ready = [], set(), False
        self.convos, self.comp_chips, self.force_users = {}, [], False
        self.streaks = {}
        self.feed_sig = None
        self.ui_ok = True
        Window.softinput_mode = "below_target"
        Window.bind(on_keyboard=self._on_key)
        self.skip_screens = set(self.store.get("bad_screens").get("names", [])) if self.store.exists("bad_screens") else set()
        self.load_problems = []
        try:
            return self.build_ui()
        except Exception:
            import traceback
            tb = traceback.format_exc()
            self.ui_ok = False
            self.log_crash(tb)
            return make_error_widget(tb)  # show the real error instead of closing

    def on_start(self):
        if not self.ui_ok:
            return
        Clock.schedule_once(self.startup_report, 1.5)
        Clock.schedule_interval(self.poll, 2.5)
        Clock.schedule_interval(self.heartbeat, 30)
        if self.store.exists("session"):
            self.api.refresh = self.store.get("session")["refresh"]
            self.api.exp = 0
            self.loading = True
            self.bg(self.api.ensure, lambda _: self.enter_app(), self.restore_failed)

    # ---------- startup safety ----------
    def flag_path(self, name):
        return os.path.join(self.user_data_dir, name)

    def read_flag(self, name):
        try:
            with open(self.flag_path(name)) as f:
                return f.read().strip()
        except Exception:
            return ""

    def set_flag(self, name, value):
        try:
            with open(self.flag_path(name), "w") as f:
                f.write(value)
        except Exception:
            pass

    def clear_flag(self, name):
        try:
            os.remove(self.flag_path(name))
        except OSError:
            pass

    def build_ui(self):
        """Load every style rule and page separately. A failure (or a crash last time) only switches that part off."""
        # Plain Kivy ScreenManager on purpose: KivyMD's MDScreenManager silently swaps any non-KivyMD
        # transition for its own slide animation, so "no transition" never took effect with it.
        sm = ScreenManager(transition=NoTransition())
        self.load_problems = []
        login_error = None
        # A page that was loading or on screen when the app last died is switched off this time.
        for flag in ("loading.flag", "showing.flag"):
            name = self.read_flag(flag)
            if name:
                self.clear_flag(flag)
                if name in SCREEN_NAMES and name != "login":
                    self.skip_screens.add(name)
        self.store.put("bad_screens", names=sorted(self.skip_screens))
        head = "\n".join(KV_DIRECTIVES) + "\n"
        for rule in KV_RULES:
            try:
                Builder.load_string(head + rule)
            except Exception:
                import traceback
                self.log_crash(traceback.format_exc())
                self.load_problems.append("style " + rule.strip().splitlines()[0])
        for name, text in KV_SCREENS:
            if name in self.skip_screens:
                scr = self.placeholder_screen(
                    name, text, "This page is switched off because the app crashed while opening it.")
                self.load_problems.append(name + " (switched off)")
            else:
                self.set_flag("loading.flag", name)
                try:
                    scr = Builder.load_string(head + text)
                except Exception:
                    import traceback
                    tb = traceback.format_exc()
                    self.log_crash(tb)
                    self.load_problems.append(name)
                    if name == "login":
                        login_error = tb  # nobody could sign in: show the full error screen instead
                    scr = self.placeholder_screen(name, text, "This page could not load:\n" + tb.strip().splitlines()[-1])
                self.clear_flag("loading.flag")
            sm.add_widget(scr)
            sm.ids.update(scr.ids)  # the app looks widgets up by id through the manager
        if login_error:
            self.ui_ok = False
            return make_error_widget(login_error)
        sm.bind(current=self._screen_shown)
        self._screen_shown(sm, "login")
        return sm

    def placeholder_screen(self, name, text, message):
        scr = MDScreen(name=name)
        box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        box.add_widget(Label(text=f"[{name}]\n{message}", color=(0.1, 0.1, 0.14, 1), halign="center",
                             text_size=(Window.width - dp(40), None)))
        btn = Button(text="Try this page again", size_hint_y=None, height=dp(52))
        btn.bind(on_release=lambda *a: self.unskip(name))
        box.add_widget(btn)
        scr.add_widget(box)
        for wid in re.findall(r"(?m)^\s+id:\s*(\w+)", text):
            scr.ids[wid] = DummyWidget()
        return scr

    def unskip(self, name):
        self.skip_screens.discard(name)
        self.store.put("bad_screens", names=sorted(self.skip_screens))
        self.notify("Close the app completely and open it again to load this page.")

    def _screen_shown(self, sm, name):
        """Remember which page is on screen; if the app dies within seconds, that page is switched off next time."""
        self.set_flag("showing.flag", name)
        ev = getattr(self, "_showing_ev", None)
        if ev:
            ev.cancel()
        self._showing_ev = Clock.schedule_once(lambda dt: self.clear_flag("showing.flag"), 4)

    def startup_report(self, dt):
        if self.load_problems:
            self.notify("Some pages could not load: " + ", ".join(self.load_problems[:6]) +
                        ".\n\nThe rest of the app works. Details: Menu > Settings > About > View error log.")

    # ---------- tabs ----------
    def go_tab(self, name):
        self.root.current = name
        if name == "feed":
            self.refresh_feed()
        elif name == "communities":
            self.load_communities()
        elif name == "contacts":
            self.refresh_contacts()
            self.refresh_convos()
            self.refresh_streaks()
        elif name == "me":
            self.refresh_me()

    def open_search(self):
        self.go_tab("communities")
        Clock.schedule_once(lambda dt: setattr(self.root.ids.comm_search, "focus", True), 0.2)

    def _on_key(self, window, key, *args):
        """Android back button: back one screen; from a tab go Home; from Home leave the app."""
        if key == 27 and self.root:
            cur = self.root.current
            back = {"chat": self.back, "user": self.close_user, "thread": self.close_thread,
                    "community": self.close_community, "compose": self.close_compose,
                    "newcommunity": self.close_new_community, "people": self.close_people,
                    "profile": self.back_to_settings, "password": self.back_to_settings}
            if cur in back:
                back[cur]()
                return True
            if cur in ("communities", "contacts", "me", "settings"):
                self.go_tab("feed")
                return True
        return False

    def section_header(self, text):
        box = MDBoxLayout(size_hint_y=None, height=dp(34), padding=(dp(14), dp(8), dp(14), 0))
        box.add_widget(SectionLabel(text=text))
        return box

    def confirm(self, title, text, action, label="DELETE"):
        def close(*args):
            dlg.dismiss()

        def go(*args):
            dlg.dismiss()
            action()

        dlg = MDDialog(title=title, text=text,
                       buttons=[MDFlatButton(text="CANCEL", on_release=close),
                                MDFlatButton(text=label, theme_text_color="Custom",
                                             text_color=(0.86, 0.2, 0.25, 1), on_release=go)])
        dlg.open()

    def forum_error(self, e, box_id):
        """Show a message in a list instead of the content."""
        msg = str(e)
        if any(k in msg for k in ("get_communities", "get_threads", "schema cache")):
            text = "The forum is not set up in your Supabase project yet. Run update_v8.sql in the SQL Editor."
        else:
            text = "Could not load. Check your connection."
        box = self.root.ids[box_id]
        box.clear_widgets()
        box.add_widget(MDLabel(text=text, halign="center", theme_text_color="Hint",
                               size_hint_y=None, height=dp(120)))

    def forum_fail(self, e):
        self.loading = False
        msg = str(e)
        if "moderators cannot leave" in msg:
            msg = "You moderate this community, so you can't leave it."
        elif "communities_name_idx" in msg or "duplicate key" in msg:
            msg = "A community with that name already exists."
        elif "violates check constraint" in msg:
            msg = "Please check the length of what you entered."
        elif "not allowed" in msg:
            msg = "You are not allowed to do that."
        elif any(k in msg for k in ("create_", "join_community", "leave_community", "toggle_",
                                    "delete_", "get_thread", "get_replies", "schema cache")):
            msg = "The forum is not set up yet. Run update_v8.sql in the Supabase SQL Editor."
        self.notify(msg[:200])

    # ---------- communities ----------
    def load_communities(self, then=None):
        if not self.api.uid or not self.root:
            return
        self.comm_req += 1
        req = self.comm_req

        def done(rows):
            if req != self.comm_req:
                return
            self.set_communities(rows)
            if then:
                then()

        def fail(e):
            if req == self.comm_req:
                self.forum_error(e, "comm_list")

        self.bg(self.api.communities, done, fail)

    def set_communities(self, rows):
        self.communities = rows or []
        self.joined = {c["id"] for c in self.communities if c.get("joined")}
        self.forum_ready = True
        self.render_communities()

    def render_communities(self):
        if not self.root:
            return
        q = self.root.ids.comm_search.text.strip().lower()
        lst = self.root.ids.comm_list
        lst.clear_widgets()
        rows = [c for c in self.communities
                if not q or q in c["name"].lower() or q in (c.get("description") or "").lower()]
        mine = [c for c in rows if c.get("joined")]
        other = [c for c in rows if not c.get("joined")]
        for title, items in (("YOUR COMMUNITIES", mine), ("DISCOVER" if mine else "ALL COMMUNITIES", other)):
            if items:
                lst.add_widget(self.section_header(title))
                for c in items:
                    lst.add_widget(self.comm_row(c))
        if not rows:
            lst.add_widget(MDLabel(
                text="No matches" if q else "No communities yet. Tap Create to start one!",
                halign="center", theme_text_color="Hint", size_hint_y=None, height=dp(120)))

    def comm_row(self, c):
        n = int(c.get("members") or 0)
        sub = f"{n} member" + ("" if n == 1 else "s")
        if c.get("description"):
            sub += " · " + short(c["description"], 44)
        joined = bool(c.get("joined"))
        return CommunityRow(
            cid=c["id"], name=c["name"], initial=initial(c["name"]), color=avatar_color(c["name"]),
            subtitle=sub, joined=joined, action="Joined" if joined else "Join",
            on_release=lambda x, cid=c["id"]: self.open_community(cid))

    def toggle_member(self, row):
        self.set_membership(int(row.cid), not row.joined)

    def set_membership(self, cid, join):
        c = next((x for x in self.communities if x["id"] == cid), None)
        if c is None:
            return
        if not join and c.get("mine"):
            self.notify("You moderate this community, so you can't leave it.")
            return

        def apply(joined):
            c["members"] = max(0, int(c.get("members") or 0) + (1 if joined and not c.get("joined") else
                                                                  -1 if not joined and c.get("joined") else 0))
            c["joined"] = joined
            self.joined = {x["id"] for x in self.communities if x.get("joined")}
            self.render_communities()
            if int(self.comm_id) == cid:
                self.fill_comm(c)

        apply(join)  # instant; undone below if the server says no

        def fail(e):
            apply(not join)
            self.forum_fail(e)

        def work():
            return self.api.join_community(cid) if join else self.api.leave_community(cid)

        self.bg(work, lambda _: setattr(self, "feed_sig", None), fail)

    def open_community(self, cid):
        c = next((x for x in self.communities if x["id"] == cid), None)
        if c is None:
            return
        if self.root.current in ("feed", "communities", "thread", "user", "me"):
            self.comm_from = self.root.current
        self.fill_comm(c)
        self.root.current = "community"
        self.load_comm_threads()

    def fill_comm(self, c):
        self.comm_id = c["id"]
        self.comm_name = c["name"]
        self.comm_initial = initial(c["name"])
        self.comm_color = avatar_color(c["name"])
        self.comm_desc = c.get("description") or "No description yet."
        n = int(c.get("members") or 0)
        self.comm_members = f"{n} member" + ("" if n == 1 else "s")
        self.comm_joined = bool(c.get("joined"))
        self.comm_action = "Joined" if self.comm_joined else "Join"

    def comm_toggle(self):
        self.set_membership(int(self.comm_id), not self.comm_joined)

    def load_comm_threads(self):
        cid = int(self.comm_id)
        box = self.root.ids.comm_threads
        box.clear_widgets()

        def done(rows):
            if int(self.comm_id) == cid:
                self.fill_threads(box, rows, "No threads yet. Start the first one!")

        self.bg(lambda: self.api.threads(community=cid, sort="new"), done,
                lambda e: self.forum_error(e, "comm_threads"))

    def close_community(self):
        self.root.current = self.comm_from

    def open_new_community(self):
        ids = self.root.ids
        ids.nc_name.text = ""
        ids.nc_desc.text = ""
        self.nc_ready = False
        self.root.current = "newcommunity"
        Clock.schedule_once(lambda dt: setattr(ids.nc_name, "focus", True), 0.3)

    def close_new_community(self):
        self.root.ids.nc_name.focus = False
        self.root.ids.nc_desc.focus = False
        self.root.current = "communities"

    def typed_community(self, widget, limit):
        if len(widget.text) > limit:
            widget.text = widget.text[:limit]
            return
        self.nc_ready = len(self.root.ids.nc_name.text.strip()) >= 3

    def submit_community(self):
        ids = self.root.ids
        name, desc = ids.nc_name.text.strip(), ids.nc_desc.text.strip()
        if not self.nc_ready:
            return
        self.loading = True

        def done(new_id):
            self.loading = False
            self.close_new_community()
            target = int(new_id) if isinstance(new_id, (int, float)) else None
            self.load_communities(then=(lambda: self.open_community(target)) if target else None)

        self.bg(lambda: self.api.create_community(name, desc), done, self.forum_fail)

    # ---------- threads ----------
    def thread_card(self, r):
        name = (r.get("display_name") or r.get("username") or "?").strip()
        tid = r["id"]
        return ThreadCard(
            tid=tid, community_id=int(r.get("community_id") or 0), community=r.get("community_name") or "",
            author_id=r["author"], name=name, initial=initial(name),
            color=avatar_color(r.get("username") or name), meta=age_text(r.get("age_seconds")),
            title=r["title"], snippet=" ".join((r.get("snippet") or "").split()),
            votes=int(r.get("votes") or 0), replies=int(r.get("replies") or 0), voted=bool(r.get("voted")),
            on_release=lambda x, t=tid: self.open_thread(t))

    def reply_card(self, r):
        name = (r.get("display_name") or r.get("username") or "?").strip()
        return ReplyCard(
            rid=r["id"], author_id=r["author"], name=name, initial=initial(name),
            color=avatar_color(r.get("username") or name), meta=age_text(r.get("age_seconds")),
            body=r["body"], votes=int(r.get("votes") or 0), voted=bool(r.get("voted")),
            can_delete=bool(r.get("can_delete")))

    def fill_threads(self, box, rows, empty):
        box.clear_widgets()
        if not rows:
            box.add_widget(MDLabel(text=empty, halign="center", theme_text_color="Hint",
                                   size_hint_y=None, height=dp(100)))
            return
        for r in rows:
            box.add_widget(self.thread_card(r))

    def refresh_feed(self, silent=False):
        if not self.api.uid or not self.root:
            return
        self.feed_req += 1
        req, sort, joined_only = self.feed_req, self.feed_sort, bool(self.joined)

        def done(rows):
            if req != self.feed_req:
                return  # an older answer
            sig = (sort, joined_only, [(r["id"], r.get("votes"), r.get("replies"), r.get("title"), r.get("voted"))
                                       for r in rows])
            if sig == self.feed_sig and self.feed_loaded:
                return  # nothing changed: keep the cards we already have
            self.feed_sig = sig
            self.feed_loaded = True
            box = self.root.ids.feed_list
            box.clear_widgets()
            if not rows:
                box.add_widget(MDLabel(text="No threads yet. Join a community or start the first thread!",
                                       halign="center", theme_text_color="Hint", size_hint_y=None, height=dp(120)))
                return
            if not joined_only:
                box.add_widget(self.section_header("POPULAR THREADS"))
            for r in rows:
                box.add_widget(self.thread_card(r))

        def fail(e):
            if req != self.feed_req or (silent and self.feed_loaded):
                return
            self.feed_sig = None
            self.forum_error(e, "feed_list")

        self.bg(lambda: self.api.threads(sort=sort, joined_only=joined_only), done, fail)

    def set_sort(self, key):
        self.feed_sort = key
        self.feed_sig = None
        self.refresh_feed()

    def vote_thread_card(self, card):
        self.flip_vote(card, lambda: self.api.toggle_thread_vote(int(card.tid)))

    def vote_reply_card(self, card):
        self.flip_vote(card, lambda: self.api.toggle_reply_vote(int(card.rid)))

    def flip_vote(self, card, call):
        """Upvote instantly; the server's count replaces ours, and a failure puts things back."""
        card.voted = not card.voted
        card.votes = max(0, card.votes + (1 if card.voted else -1))

        def done(res):
            if res and "votes" in res:
                card.votes, card.voted = int(res["votes"]), bool(res.get("voted"))

        def fail(e):
            card.voted = not card.voted
            card.votes = max(0, card.votes + (1 if card.voted else -1))
            self.forum_fail(e)

        self.bg(call, done, fail)

    # ---------- one thread ----------
    def open_thread(self, tid):
        if self.root.current in ("feed", "community", "me", "user"):
            self.thread_from = self.root.current
        self.thread_id = int(tid)
        self.thread_title = self.thread_body = self.thread_meta = self.thread_community = ""
        self.thread_replies = self.thread_votes = 0
        self.thread_voted = self.thread_can_delete = False
        self.root.ids.reply_list.clear_widgets()
        self.root.ids.reply_input.text = ""
        self.root.current = "thread"
        self.load_thread()

    def load_thread(self):
        tid = int(self.thread_id)

        def work():
            return self.api.thread(tid), self.api.replies(tid)

        def done(res):
            t, replies = res
            if int(self.thread_id) != tid:
                return
            if not t:
                self.notify("This thread no longer exists.")
                self.close_thread()
                return
            name = (t.get("display_name") or t.get("username") or "?").strip()
            self.thread_title, self.thread_body = t["title"], t["body"]
            self.thread_community = t.get("community_name") or ""
            self.thread_comm_id = int(t.get("community_id") or 0)
            self.thread_author_id, self.thread_name = t["author"], name
            self.thread_initial = initial(name)
            self.thread_color = avatar_color(t.get("username") or name)
            self.thread_meta = age_text(t.get("age_seconds"))
            self.thread_votes, self.thread_voted = int(t.get("votes") or 0), bool(t.get("voted"))
            self.thread_replies, self.thread_can_delete = int(t.get("replies") or 0), bool(t.get("can_delete"))
            box = self.root.ids.reply_list
            box.clear_widgets()
            for r in replies:
                box.add_widget(self.reply_card(r))

        self.bg(work, done, self.forum_fail)

    def close_thread(self):
        self.root.current = self.thread_from
        if self.thread_from == "feed":
            self.refresh_feed(silent=True)
        elif self.thread_from == "community":
            self.load_comm_threads()
        elif self.thread_from == "me":
            self.refresh_me()

    def open_thread_community(self):
        if self.thread_comm_id:
            self.open_community(int(self.thread_comm_id))

    def vote_thread_page(self):
        tid = int(self.thread_id)
        self.thread_voted = not self.thread_voted
        self.thread_votes = max(0, self.thread_votes + (1 if self.thread_voted else -1))

        def done(res):
            if res and "votes" in res and int(self.thread_id) == tid:
                self.thread_votes, self.thread_voted = int(res["votes"]), bool(res.get("voted"))

        def fail(e):
            self.thread_voted = not self.thread_voted
            self.thread_votes = max(0, self.thread_votes + (1 if self.thread_voted else -1))
            self.forum_fail(e)

        self.bg(lambda: self.api.toggle_thread_vote(tid), done, fail)

    def send_reply(self):
        field = self.root.ids.reply_input
        text = field.text.strip()
        if not text or not self.thread_id:
            return
        tid = int(self.thread_id)
        field.text = ""
        Clock.schedule_once(lambda dt: setattr(field, "focus", True), 0.05)

        def done(_):
            if int(self.thread_id) == tid:
                self.load_thread()
                Clock.schedule_once(lambda dt: setattr(self.root.ids.thread_scroll, "scroll_y", 0), 0.4)

        def fail(e):
            if not field.text:
                field.text = text
            self.forum_fail(e)

        self.bg(lambda: self.api.create_reply(tid, text), done, fail)

    def confirm_delete_thread(self):
        self.confirm("Delete thread?", "This removes the thread and all of its replies.", self.delete_thread_now)

    def delete_thread_now(self):
        tid = int(self.thread_id)

        def done(_):
            self.feed_sig = None
            self.close_thread()

        self.bg(lambda: self.api.delete_thread(tid), done, self.forum_fail)

    def confirm_delete_reply(self, card):
        rid = int(card.rid)
        self.confirm("Delete reply?", "This removes the reply.",
                     lambda: self.bg(lambda: self.api.delete_reply(rid), lambda _: self.load_thread(), self.forum_fail))

    # ---------- writing a thread ----------
    def open_compose(self, community_id=None):
        ids = self.root.ids
        ids.thread_title_input.text = ""
        ids.thread_body_input.text = ""
        if self.root.current in ("feed", "community", "me", "communities"):
            self.compose_from = self.root.current
        cid = int(community_id or 0)
        if not cid and self.root.current == "community":
            cid = int(self.comm_id)
        if not cid and self.joined:
            cid = sorted(self.joined)[0]
        self.compose_comm = cid
        self.thread_ready, self.thread_chars = False, "0/2000"
        self.build_comm_chips()
        self.root.current = "compose"
        Clock.schedule_once(lambda dt: setattr(ids.thread_title_input, "focus", True), 0.3)

    def close_compose(self):
        self.root.ids.thread_title_input.focus = False
        self.root.ids.thread_body_input.focus = False
        self.root.current = self.compose_from

    def build_comm_chips(self):
        box = self.root.ids.comp_comms
        box.clear_widgets()
        self.comp_chips = []
        if not self.communities:
            if not self.forum_ready:
                self.load_communities(then=self.build_comm_chips)
            return
        ordered = sorted(self.communities, key=lambda c: (not c.get("joined"), -int(c.get("members") or 0),
                                                          c["name"].lower()))[:25]
        for c in ordered:
            chip = Chip(text=c["name"], selected=c["id"] == self.compose_comm,
                        on_release=lambda x, cid=c["id"]: self.select_comm(cid))
            self.comp_chips.append((c["id"], chip))
            box.add_widget(chip)

    def select_comm(self, cid):
        self.compose_comm = int(cid)
        for c_id, chip in self.comp_chips:
            chip.selected = c_id == self.compose_comm
        self.recalc_thread_ready()

    def recalc_thread_ready(self):
        ids = self.root.ids
        self.thread_ready = bool(self.compose_comm and len(ids.thread_title_input.text.strip()) >= 3
                                 and ids.thread_body_input.text.strip())
        self.thread_chars = f"{len(ids.thread_body_input.text)}/2000"

    def typed_title(self, widget):
        if len(widget.text) > 120:
            widget.text = widget.text[:120]
            return
        self.recalc_thread_ready()

    def typed_body(self, widget):
        if len(widget.text) > 2000:
            widget.text = widget.text[:2000]
            return
        self.recalc_thread_ready()

    def submit_thread(self):
        ids = self.root.ids
        title, body, cid = ids.thread_title_input.text.strip(), ids.thread_body_input.text.strip(), int(self.compose_comm)
        if not self.thread_ready:
            return
        self.loading = True

        def done(new_id):
            self.loading = False
            self.feed_sig = None
            self.close_compose()
            self.load_communities()
            if isinstance(new_id, (int, float)):
                self.open_thread(int(new_id))

        self.bg(lambda: self.api.create_thread(cid, title, body), done, self.forum_fail)

    # ---------- profiles ----------
    def stats_text(self, prof, n_threads):
        t, r, c = prof.get("threads_count"), prof.get("replies_count"), prof.get("communities_count")
        return f"{n_threads if t is None else t} threads · {r or 0} replies · {c or 0} communities"

    def refresh_me(self):
        if not self.api.uid or not self.root:
            return
        uid = self.api.uid

        def work():
            try:
                rows = self.api.threads(author=uid, sort="new")
            except RuntimeError:
                rows = []
            return self.api.profile(uid), rows

        def done(res):
            prof, rows = res
            self.me_bio = prof.get("bio") or ""
            self.me_stats = self.stats_text(prof, len(rows))
            self.fill_threads(self.root.ids.me_posts, rows, "You have not started a thread yet.")

        self.bg(work, done, lambda e: None)

    def open_user(self, uid):
        if uid == self.api.uid:
            self.go_tab("me")
            return
        if self.root.current in ("feed", "communities", "contacts", "me", "thread", "community", "people"):
            self.user_from = self.root.current
        u = self.user_by_id(uid) or {"id": uid, "username": "?", "display_name": None}
        self.fill_view(u)
        self.root.current = "user"
        self.load_view(uid)

    def fill_view(self, u):
        name = name_of(u)
        self.view_uid = u["id"]
        self.view_name, self.view_username = name, u["username"]
        self.view_initial, self.view_color = initial(name), avatar_color(u["username"])
        self.view_primary, self.view_secondary = "Message", ""
        self.view_bio, self.view_stats = "", ""
        self.view_hint = presence_text(u.get("seconds_ago"))

    def load_view(self, uid):
        box = self.root.ids.user_posts
        box.clear_widgets()

        def work():
            try:
                rows = self.api.threads(author=uid, sort="new")
            except RuntimeError:
                rows = []
            return self.api.profile(uid), rows

        def done(res):
            if self.view_uid != uid:
                return
            prof, rows = res
            self.view_bio = prof.get("bio") or ""
            self.view_stats = self.stats_text(prof, len(rows))
            self.fill_threads(box, rows, "No threads yet.")

        self.bg(work, done, lambda e: None)

    def close_user(self):
        self.root.current = self.user_from

    def view_primary_tap(self):
        self.open_chat(self.view_uid, self.view_name)

    def view_secondary_tap(self):
        pass

    # ---------- messaging: who you talk to ----------
    def open_people(self):
        if self.root.current in ("contacts", "communities", "feed", "me"):
            self.people_from = self.root.current
        self.root.ids.people_search.text = ""
        self.root.current = "people"
        self.refresh_people()
        Clock.schedule_once(lambda dt: setattr(self.root.ids.people_search, "focus", True), 0.3)

    def close_people(self):
        self.root.ids.people_search.focus = False
        self.root.current = self.people_from

    def refresh_people(self):
        if not self.root:
            return
        q = self.root.ids.people_search.text.strip().lower()
        lst = self.root.ids.people_list
        lst.clear_widgets()
        shown = 0
        for u in sorted(self.users, key=lambda u: (u.get("seconds_ago") is None, u.get("seconds_ago") or 0,
                                                    name_of(u).lower())):
            name, sec = name_of(u), u.get("seconds_ago")
            if q and q not in name.lower() and q not in u["username"].lower():
                continue
            lst.add_widget(PersonRow(
                uid=u["id"], name=name, initial=initial(name), color=avatar_color(u["username"]),
                subtitle=presence_text(sec) or "@" + u["username"], online=is_online(sec),
                status="member", primary="Message", secondary="",
                on_release=lambda x, uid=u["id"]: self.open_user(uid)))
            shown += 1
            if shown >= 60:
                break
        if not shown:
            lst.add_widget(MDLabel(text="No one found" if q else "No other members yet.", halign="center",
                                   theme_text_color="Hint", size_hint_y=None, height=dp(120)))

    def person_primary(self, row):
        self.open_chat(row.uid, row.name)

    def person_secondary(self, row):
        pass

    def users_key(self, users):
        return [(u["id"], name_of(u), is_online(u.get("seconds_ago"))) for u in users]

    def refresh_convos(self):
        """Who you have talked to, with the latest message of each conversation."""
        if not self.api.uid:
            return

        def done(found):
            merged = dict(found)
            for pid, c in self.convos.items():  # keep anything newer that we already know about
                if pid not in merged or c["id"] > merged[pid]["id"]:
                    merged[pid] = c
            if merged != self.convos:
                self.convos = merged
                self.refresh_contacts()

        self.bg(self.api.conversations, done, lambda e: None)

    def refresh_contacts(self):
        if not self.root:
            return
        self.unread_total = sum(self.unread.values())
        if self.root.current != "contacts":
            return  # the Chats list is only rebuilt while it is on screen (saves memory)
        q = self.root.ids.search_field.text.strip().lower()
        lst = self.root.ids.contact_list
        lst.clear_widgets()
        rows = []
        for pid in set(self.convos) | set(self.unread):
            u = self.user_by_id(pid)
            if not u:
                continue
            name = name_of(u)
            if q and q not in name.lower() and q not in u["username"].lower():
                continue
            c = self.convos.get(pid)
            rows.append((c["id"] if c else 0, name, u, c))
        rows.sort(key=lambda r: (-r[0], r[1].lower()))  # latest conversation first
        for _, name, u, c in rows:
            if c and self.prefs.get("previews", True):
                text = " ".join(c["text"].split())
                text = text if len(text) <= 38 else text[:36] + "..."
                sub = ("You: " if c["sender"] == self.api.uid else "") + text
            else:
                sub = "@" + u["username"]
            lst.add_widget(ContactRow(
                name=name, subtitle=sub, initial=initial(name), avatar_color=avatar_color(u["username"]),
                unread=self.unread.get(u["id"], 0), online=is_online(u.get("seconds_ago")),
                streak=self.streaks.get(u["id"], 0),
                on_release=lambda x, uid=u["id"], n=name: self.open_chat(uid, n)))
        if not rows:
            lst.add_widget(MDLabel(
                text="No matches" if q else "No conversations yet.\nTap the pencil icon to message someone.",
                halign="center", theme_text_color="Hint", size_hint_y=None, height=dp(140)))

    def enter_app(self):
        self.me_username = self.api.username
        self.me_name = self.api.username
        self.root.ids.pass_field.text = ""

        self.local = LocalDB(os.path.join(self.user_data_dir, f"chat_{self.api.uid}.db"))
        local = self.local
        self.users = local.load_users()
        self.msgs, self.seen, self.unread, self.convos = {}, set(), {}, {}
        cached_last = local.get_meta("last_id")
        resume_from = int(cached_last) if cached_last else None

        def init():
            users = self.api.users()
            me = self.api.me()
            last = resume_from if resume_from is not None else self.api.latest_incoming_id()
            convos = self.api.conversations()
            try:
                comms = self.api.communities()
            except RuntimeError:
                comms = None  # the forum update (update_v8.sql) has not been run yet
            local.save_users(users)
            local.set_meta("last_id", last)
            try:
                self.api.touch()
            except Exception:
                pass
            return users, last, me, convos, comms

        def done(res):
            self.users, self.last_id, me, self.convos, comms = res
            self.set_me(me)
            self.loading = False
            if comms is not None:
                self.set_communities(comms)
            self.root.current = "feed"
            self.refresh_feed()
            self.refresh_me()
            self.refresh_streaks()
            self.refresh_contacts()

        self.bg(init, done)

    def poll(self, dt):
        if not self.ui_ok or not self.api.uid or self.poll_busy or self.loading:
            return
        self.poll_busy = True
        self.tick += 1
        if self.tick % 12 == 0 and self.root.current == "feed":
            self.refresh_feed(silent=True)  # keep Home fresh (about every 30 seconds)
        if self.tick % 24 == 0:
            self.refresh_streaks()
            self.refresh_convos()
        local = self.local
        force_users, self.force_users = self.force_users, False

        def work():
            inc = self.api.incoming(self.last_id)
            users = self.api.users() if (self.tick % 6 == 0 or force_users) else None
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
                self.convos[peer] = {"id": m["id"], "sender": peer, "text": m["text"]}
                if not self.user_by_id(peer):
                    self.force_users = True  # a message from someone we have not listed yet
                if peer == self.peer and self.root.current == "chat":
                    self.add_bubble(m)
                else:
                    self.unread[peer] = self.unread.get(peer, 0) + 1
                changed = True
            self.unread_total = sum(self.unread.values())
            if changed and self.root.current == "contacts":
                self.refresh_contacts()
            elif changed and self.root.current == "people":
                self.refresh_people()

        def fail(e):
            self.poll_busy = False

        self.bg(work, done, fail)

    # ---------- error log ----------
    def log_crash(self, tb):
        try:
            path = os.path.join(self.user_data_dir, "crash.log")
            if os.path.exists(path) and os.path.getsize(path) > 60000:
                os.remove(path)  # keep the file small
            with open(path, "a") as f:
                f.write(time.ctime() + "\n" + tb + "\n")
        except Exception:
            pass

    def read_log(self):
        try:
            with open(os.path.join(self.user_data_dir, "crash.log")) as f:
                return f.read()
        except Exception:
            return ""

    def view_error_log(self):
        log = self.read_log()
        shown = log[-700:] if log else "No errors have been recorded."

        def copy(*args):
            Clipboard.copy(log or "No errors have been recorded.")

        def clear(*args):
            try:
                os.remove(os.path.join(self.user_data_dir, "crash.log"))
            except OSError:
                pass
            dlg.dismiss()

        def close(*args):
            dlg.dismiss()

        dlg = MDDialog(title="Error log", text=shown,
                       buttons=[MDFlatButton(text="COPY", on_release=copy),
                                MDFlatButton(text="CLEAR", on_release=clear),
                                MDFlatButton(text="CLOSE", on_release=close)])
        dlg.open()

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
        msg = str(e)
        self.notify(msg[:140])

    def toggle_mode(self):
        self.signup_mode = not self.signup_mode

    def set_me(self, me):
        self.me = me or {}
        self.me_email = self.api.email or ""
        self.me_username = self.me.get("username") or self.api.username
        self.me_name = self.me.get("display_name") or self.me_username
        self.me_initial = initial(self.me_name)
        self.me_color = avatar_color(self.me_username)

    def user_by_id(self, uid):
        return next((u for u in self.users if u["id"] == uid), None)

    def update_peer_status(self):
        u = self.user_by_id(self.peer) if self.peer else None
        if not u:
            return
        self.peer_name = name_of(u)
        self.peer_initial = initial(self.peer_name)
        self.peer_active = is_online(u.get("seconds_ago"))
        parts = [presence_text(u.get("seconds_ago"))]
        days = self.streaks.get(self.peer, 0)
        if days > 1:
            parts.append(f"{days}-day streak")
        self.peer_status = " · ".join(x for x in parts if x)

    def heartbeat(self, dt):
        """Tell the server we are active (others see 'Active now')."""
        if self.ui_ok and self.api.uid and not self.loading:
            self.bg(self.api.touch, None, lambda e: None)

    def on_resume(self):
        self.heartbeat(0)

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

    def logout(self):
        api = self.api
        threading.Thread(target=api.sign_out, daemon=True).start()
        if self.store.exists("session"):
            self.store.delete("session")
        if self.local:
            local, self.local = self.local, None
            threading.Thread(target=local.destroy, daemon=True).start()
        self.users, self.msgs, self.unread, self.seen = [], {}, {}, set()
        self.convos, self.communities, self.joined, self.forum_ready = {}, [], set(), False
        self.feed_sig = None
        self.feed_loaded = False
        self.peer, self.last_id = None, 0
        self.me, self.me_name, self.peer_status, self.peer_active = {}, "", "", False
        self.root.ids.contact_list.clear_widgets()
        self.root.current = "login"

    # ---------- polling for new messages ----------

    # ---------- contacts ----------

    # ---------- chat ----------
    def open_chat(self, uid, name):
        if uid == self.api.uid:
            return
        if self.root.current in ("feed", "contacts", "communities", "me", "user", "people", "thread", "community"):
            self.chat_from = self.root.current
        self.peer = uid
        self.unread.pop(uid, None)
        self.unread_total = sum(self.unread.values())
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
        if rows:
            last = rows[-1]
            self.convos[uid] = {"id": last["id"], "sender": last["sender"], "text": last["text"]}
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
        self.root.current = self.chat_from
        self.refresh_contacts()
        if self.chat_from == "feed":
            self.refresh_feed(silent=True)

    # ---------- profile ----------
    def open_settings(self):
        ids = self.root.ids
        self._profile_loading = True  # don't treat these programmatic changes as user taps
        ids.active_row.active = self.me.get("show_active") is not False
        ids.preview_row.active = bool(self.prefs.get("previews", True))
        self._profile_loading = False
        self.root.current = "settings"

    def open_profile(self):
        self.root.ids.name_field.text = self.me.get("display_name") or ""
        self.root.ids.bio_field.text = self.me_bio
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
        ids = self.root.ids
        name, bio = ids.name_field.text.strip(), ids.bio_field.text.strip()
        if len(name) > 40:
            self.notify("Display name can be up to 40 characters")
            return
        if len(bio) > 150:
            self.notify("Bio can be up to 150 characters")
            return
        old_bio = self.me_bio
        self.loading = True

        def work():
            self.api.set_display_name(name)
            if bio != old_bio:
                self.api.set_bio(bio)  # needs supabase/update_v6.sql

        def done(_):
            self.loading = False
            self.me["display_name"] = name or None
            self.me_bio = bio
            self.set_me(self.me)
            self.back_to_settings()

        def fail(e):
            self.loading = False
            msg = str(e)
            if "set_bio" in msg or "schema cache" in msg:
                msg = "Bios are not set up yet. Run update_v6.sql in the Supabase SQL Editor."
            self.notify(msg[:200])

        self.bg(work, done, fail)

    # ---------- tabs ----------

    # ---------- chat streaks ----------

    # ---------- other people's profiles ----------

    # ---------- my profile tab ----------

    # ---------- home feed ----------

    def refresh_streaks(self):
        """Chat streaks: days in a row both of you messaged (shown in Chats and the chat header)."""
        if not self.api.uid:
            return

        def done(found):
            if found != self.streaks:
                self.streaks = found
                self.update_peer_status()
                self.refresh_contacts()

        self.bg(self.api.streaks, done, lambda e: None)

    # ---------- composer ----------

    # ---------- notes (Messenger-style composer) ----------

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
            self.convos[peer] = {"id": m["id"], "sender": m["sender"], "text": m["text"]}
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
