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
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog

import config

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
        icon: "message-text" if root.current == "contacts" else "message-text-outline"
        active: root.current == "contacts"
        badge: app.unread_total
        on_release: app.go_tab("contacts")
    TabItem:
        icon: "account-multiple" if root.current == "people" else "account-multiple-outline"
        active: root.current == "people"
        badge: app.request_count
        on_release: app.go_tab("people")
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

<PostCard>:
    orientation: "vertical"
    adaptive_height: True
    md_bg_color: WHITE
    padding: dp(14), dp(12), dp(14), dp(2)
    spacing: dp(8)
    TapBox:
        size_hint_y: None
        height: dp(46)
        spacing: dp(10)
        on_release: app.open_user(root.author_id)
        AvatarDot:
            size: dp(42), dp(42)
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
                text: root.meta
                font_style: "Caption"
                theme_text_color: "Custom"
                text_color: MUTED
                size_hint_y: None
                text_size: self.width, None
                height: self.texture_size[1]
        MDIconButton:
            icon: "delete-outline"
            pos_hint: {"center_y": .5}
            opacity: 1 if root.mine else 0
            disabled: not root.mine
            theme_icon_color: "Custom"
            icon_color: MUTED
            on_release: app.confirm_delete_post(root)
    MDLabel:
        text: root.prompt
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: PRIMARY
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
        opacity: 1 if self.text else 0
    MDLabel:
        text: root.body
        font_style: "Body1"
        theme_text_color: "Custom"
        text_color: INK
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
    MDBoxLayout:
        id: poll_box
        orientation: "vertical"
        adaptive_height: True
        spacing: dp(6)
    MDLabel:
        text: root.votes_text
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: MUTED
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
    MDLabel:
        text: (str(root.likes) + (" like" if root.likes == 1 else " likes")) if root.likes else ""
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: MUTED
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1] if self.text else 0
    MDBoxLayout:
        size_hint_y: None
        height: dp(1)
        md_bg_color: LINE
    MDBoxLayout:
        size_hint_y: None
        height: dp(44)
        TapBox:
            on_release: app.toggle_like(root)
            Widget:
            MDIcon:
                icon: "thumb-up" if root.liked else "thumb-up-outline"
                size_hint: None, None
                size: dp(22), dp(22)
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: PRIMARY if root.liked else MUTED
            Label:
                text: "  Like"
                font_size: "14sp"
                bold: True
                color: PRIMARY if root.liked else MUTED
                size_hint_x: None
                width: self.texture_size[0]
            Widget:
        TapBox:
            disabled: root.mine
            opacity: 0 if root.mine else 1
            on_release: app.reply_to_post(root)
            Widget:
            MDIcon:
                icon: "message-text-outline"
                size_hint: None, None
                size: dp(22), dp(22)
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: MUTED
            Label:
                text: "  Reply privately"
                font_size: "14sp"
                bold: True
                color: MUTED
                size_hint_x: None
                width: self.texture_size[0]
            Widget:

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
            on_release: root.dispatch("on_primary")
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
            on_release: root.dispatch("on_secondary")
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

<PollOption>:
    size_hint_y: None
    height: dp(42)
    PassCard:
        size_hint: 1, 1
        pos_hint: {"x": 0, "y": 0}
        radius: [dp(12)]
        elevation: 0
        md_bg_color: (0.93, 0.94, 0.96, 1)
    PassCard:
        size_hint: root.fill, 1
        pos_hint: {"x": 0, "y": 0}
        radius: [dp(12)]
        elevation: 0
        md_bg_color: (0.74, 0.85, 1.0, 1) if root.mine else (0.84, 0.87, 0.92, 1)
    Label:
        text: root.text
        font_size: "14sp"
        bold: root.mine
        color: INK
        halign: "left"
        valign: "middle"
        shorten: True
        max_lines: 1
        text_size: self.size
        size_hint: .72, 1
        pos_hint: {"x": .04, "y": 0}
    Label:
        text: root.pct_text
        font_size: "13sp"
        bold: True
        color: MUTED
        halign: "right"
        valign: "middle"
        text_size: self.size
        size_hint: .2, 1
        pos_hint: {"right": .97, "y": 0}

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
                                    text: "What's on your mind?"
                                    font_size: "15sp"
                                    color: MUTED
                                    size_hint: None, None
                                    size: self.texture_size
                                    pos_hint: {"center_y": .5}
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
                        padding: dp(14), dp(12)
                        spacing: dp(6)
                        SectionLabel:
                            text: "QUESTION OF THE DAY"
                        MDLabel:
                            text: app.prompt_text
                            font_style: "Subtitle1"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                        TapBox:
                            size_hint: None, None
                            size: dp(110), dp(36)
                            on_release: app.answer_prompt()
                            PassCard:
                                radius: [dp(18)]
                                elevation: 0
                                md_bg_color: PRIMARY
                                Label:
                                    text: "Answer"
                                    font_size: "14sp"
                                    bold: True
                                    color: WHITE
                                    text_size: self.size
                                    halign: "center"
                                    valign: "middle"
                    MDBoxLayout:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: WHITE
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
                    MDBoxLayout:
                        id: feed_list
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(8)

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
                bar_width: 0
                MDBoxLayout:
                    id: contact_list
                    orientation: "vertical"
                    adaptive_height: True

    MDScreen:
        name: "people"
        md_bg_color: BG
        MDBoxLayout:
            orientation: "vertical"
            TopBar:
            TabBar:
                current: "people"
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
                do_scroll_x: False
                MDBoxLayout:
                    id: people_list
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(1)

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
                        secondary: "New post"
                        on_primary: app.open_profile()
                        on_secondary: app.open_compose()
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(14), dp(8), dp(14), 0
                        SectionLabel:
                            text: "MY POSTS"
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
                        on_primary: app.view_primary_tap()
                        on_secondary: app.view_secondary_tap()
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(14), dp(8), dp(14), 0
                        SectionLabel:
                            text: "POSTS"
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
                        MDTextField:
                            id: bio_field
                            hint_text: "Bio (up to 150 characters)"
                            mode: "rectangle"
                        MDLabel:
                            text: "Your name and bio are shown to your friends."
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
                    text: "Create post"
                    halign: "center"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                TapBox:
                    size_hint: None, None
                    size: dp(76), dp(40)
                    pos_hint: {"center_y": .5}
                    on_release: app.share_post()
                    PassCard:
                        radius: [dp(20)]
                        elevation: 0
                        md_bg_color: PRIMARY if app.post_ready else (0.9, 0.91, 0.93, 1)
                        Label:
                            text: "Post"
                            font_size: "15sp"
                            bold: True
                            color: WHITE if app.post_ready else (0.6, 0.62, 0.66, 1)
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
                    spacing: dp(12)
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(10)
                        AvatarDot:
                            size: dp(42), dp(42)
                            pos_hint: {"center_y": .5}
                            initial: app.me_initial
                            color: app.me_color
                        MDLabel:
                            text: app.me_name
                            font_style: "Subtitle1"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: INK
                            size_hint_y: None
                            text_size: self.width, None
                            height: self.texture_size[1]
                            pos_hint: {"center_y": .5}
                    MDLabel:
                        text: ("Question of the day: " + app.post_prompt) if app.post_prompt else ""
                        font_style: "Body2"
                        theme_text_color: "Custom"
                        text_color: PRIMARY
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1] if self.text else 0
                    TextInput:
                        id: post_input
                        hint_text: "What's on your mind?"
                        multiline: True
                        size_hint_y: None
                        height: dp(170)
                        background_color: 0, 0, 0, 0
                        background_normal: ""
                        background_active: ""
                        foreground_color: INK
                        hint_text_color: MUTED
                        cursor_color: PRIMARY
                        font_size: "18sp"
                        padding: [0, dp(6), 0, dp(6)]
                        on_text: app.on_post_text(self)
                    MDLabel:
                        text: app.post_chars
                        halign: "right"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: MUTED
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                    SectionLabel:
                        text: "POLL"
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        Chip:
                            text: "Ask your friends"
                            selected: app.post_poll_on
                            on_release: app.toggle_poll()
                    MDBoxLayout:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(194) if app.post_poll_on else 0
                        opacity: 1 if app.post_poll_on else 0
                        disabled: not app.post_poll_on
                        spacing: dp(6)
                        MDCard:
                            size_hint_y: None
                            height: dp(44)
                            radius: [dp(22)]
                            elevation: 0
                            md_bg_color: (0.94, 0.945, 0.955, 1)
                            padding: dp(16), 0
                            TextInput:
                                id: poll_opt0
                                hint_text: "Option 1"
                                multiline: False
                                background_color: 0, 0, 0, 0
                                background_normal: ""
                                background_active: ""
                                foreground_color: INK
                                hint_text_color: MUTED
                                cursor_color: PRIMARY
                                font_size: "16sp"
                                padding: [0, dp(12), 0, dp(12)]
                                on_text: app.on_poll_text(self)
                        MDCard:
                            size_hint_y: None
                            height: dp(44)
                            radius: [dp(22)]
                            elevation: 0
                            md_bg_color: (0.94, 0.945, 0.955, 1)
                            padding: dp(16), 0
                            TextInput:
                                id: poll_opt1
                                hint_text: "Option 2"
                                multiline: False
                                background_color: 0, 0, 0, 0
                                background_normal: ""
                                background_active: ""
                                foreground_color: INK
                                hint_text_color: MUTED
                                cursor_color: PRIMARY
                                font_size: "16sp"
                                padding: [0, dp(12), 0, dp(12)]
                                on_text: app.on_poll_text(self)
                        MDCard:
                            size_hint_y: None
                            height: dp(44)
                            radius: [dp(22)]
                            elevation: 0
                            md_bg_color: (0.94, 0.945, 0.955, 1)
                            padding: dp(16), 0
                            TextInput:
                                id: poll_opt2
                                hint_text: "Option 3 (optional)"
                                multiline: False
                                background_color: 0, 0, 0, 0
                                background_normal: ""
                                background_active: ""
                                foreground_color: INK
                                hint_text_color: MUTED
                                cursor_color: PRIMARY
                                font_size: "16sp"
                                padding: [0, dp(12), 0, dp(12)]
                                on_text: app.on_poll_text(self)
                        MDCard:
                            size_hint_y: None
                            height: dp(44)
                            radius: [dp(22)]
                            elevation: 0
                            md_bg_color: (0.94, 0.945, 0.955, 1)
                            padding: dp(16), 0
                            TextInput:
                                id: poll_opt3
                                hint_text: "Option 4 (optional)"
                                multiline: False
                                background_color: 0, 0, 0, 0
                                background_normal: ""
                                background_active: ""
                                foreground_color: INK
                                hint_text_color: MUTED
                                cursor_color: PRIMARY
                                font_size: "16sp"
                                padding: [0, dp(12), 0, dp(12)]
                                on_text: app.on_poll_text(self)

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


PROMPTS = [
    "What made you smile today?", "What is one small win you had this week?",
    "What song is stuck in your head right now?", "Describe your day in three words.",
    "What is the best thing you ate recently?", "Who made your day better lately?",
    "What are you looking forward to this weekend?", "What is something new you learned recently?",
    "What would you do with a free day tomorrow?", "What is your go-to comfort food?",
    "What is a place you want to visit someday?", "What habit are you trying to build?",
    "What is the best advice you ever got?", "What is on your playlist this week?",
    "What is a hobby you would love to pick up?", "What is one thing you are grateful for today?",
    "Which movie could you watch again and again?", "What is your favorite way to relax?",
    "What is a skill you wish you had?", "What was the highlight of your morning?",
    "If today had a theme song, what would it be?", "What is a tiny thing that always cheers you up?",
    "What is your favorite memory from this year?", "What would your perfect rainy day look like?",
    "What is something you are proud of?", "Which app can you not live without?",
    "What is the kindest thing someone did for you lately?", "What is your dream job for one day?",
    "What do you do when you cannot sleep?", "What is a goal you are working on right now?",
    "What is a food you could eat every day?",
]


def today_prompt():
    return PROMPTS[date.today().toordinal() % len(PROMPTS)]


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


def is_friend(u):
    return (u.get("status") or "friends") == "friends"  # old databases (no friends update) count as friends


def buttons_for(status):
    """(primary, secondary) button labels for a relationship."""
    return {"none": ("Add friend", ""), "outgoing": ("", "Cancel request"),
            "incoming": ("Confirm", "Delete"), "friends": ("Message", "Unfriend")}.get(status, ("", ""))


def mutual_text(n):
    return "" if not n else ("1 mutual friend" if n == 1 else f"{n} mutual friends")


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
                     "seconds_ago": r.get("seconds_ago"), "note": r.get("note"),
                     "status": r.get("status") or "friends", "mutual": int(r.get("mutual") or 0)} for r in rows]
        except RuntimeError:
            rows = self._req("GET", "/rest/v1/profiles", params={"select": "id,username", "order": "username"})
            return [{"id": r["id"], "username": r["username"], "display_name": None, "seconds_ago": None,
                     "note": None, "status": "friends", "mutual": 0} for r in rows if r["id"] != self.uid]

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

    def profile(self, uid):
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_profile", json={"p_user": uid})
            return rows[0] if rows else {}
        except RuntimeError:
            return {}  # friends update not installed yet

    def send_request(self, uid):
        return self._req("POST", "/rest/v1/rpc/send_friend_request", json={"p_user": uid})

    def respond_request(self, uid, accept):
        return self._req("POST", "/rest/v1/rpc/respond_friend_request", json={"p_user": uid, "p_accept": bool(accept)})

    def remove_friend(self, uid):
        return self._req("POST", "/rest/v1/rpc/remove_friend", json={"p_user": uid})

    def set_bio(self, text):
        self._req("POST", "/rest/v1/rpc/set_bio", json={"p_bio": text})

    def feed(self, author=None):
        payload = {"p_limit": 40}
        if author:
            payload["p_author"] = author
        return self._req("POST", "/rest/v1/rpc/get_feed", json=payload) or []

    def create_post(self, body, prompt, poll=None):
        payload = {"p_body": body, "p_prompt": prompt or None}
        if poll:
            payload["p_poll"] = poll
        self._req("POST", "/rest/v1/rpc/create_post", json=payload)

    def vote_poll(self, post_id, option):
        return self._req("POST", "/rest/v1/rpc/vote_poll", json={"p_post": post_id, "p_option": int(option)}) or {}

    def streaks(self):
        try:
            rows = self._req("POST", "/rest/v1/rpc/get_streaks", json={})
            return {r["friend"]: int(r["days"]) for r in rows or []}
        except RuntimeError:
            return {}  # polls/streaks update not installed yet

    def toggle_like(self, post_id):
        rows = self._req("POST", "/rest/v1/rpc/toggle_like", json={"p_post": post_id})
        return rows[0] if rows else {}

    def delete_post(self, post_id):
        self._req("DELETE", "/rest/v1/posts", params={"id": f"eq.{post_id}"})

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


class PersonRow(ButtonBehavior, MDBoxLayout):
    """A person in the Friends tab, with action buttons that depend on the friendship state."""
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
    __events__ = ("on_primary", "on_secondary")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    name = StringProperty("")
    username = StringProperty("")
    bio = StringProperty("")
    hint = StringProperty("")
    stats = StringProperty("")
    primary = StringProperty("")
    secondary = StringProperty("")

    def on_primary(self):
        pass

    def on_secondary(self):
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
    """Pill-shaped choice (for example: add a poll)."""
    text = StringProperty("")
    selected = BooleanProperty(False)
    accent = ListProperty([0.094, 0.467, 0.949, 1])


class PollOption(ButtonBehavior, MDFloatLayout):
    """One answer in a poll: a bar that fills according to its share of the votes."""
    text = StringProperty("")
    idx = NumericProperty(0)
    fill = NumericProperty(0)
    pct_text = StringProperty("")
    mine = BooleanProperty(False)
    card = ObjectProperty(None)


class PostCard(MDBoxLayout):
    pid = NumericProperty(0)
    author_id = StringProperty("")
    name = StringProperty("")
    initial = StringProperty("?")
    color = ListProperty([0, 0.52, 1, 1])
    meta = StringProperty("")
    prompt = StringProperty("")
    body = StringProperty("")
    my_vote = NumericProperty(-1)
    counts = ListProperty([])
    poll_rows = ListProperty([])
    votes_text = StringProperty("")
    likes = NumericProperty(0)
    liked = BooleanProperty(False)
    mine = BooleanProperty(False)


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
    note_ready = BooleanProperty(False)
    has_note = BooleanProperty(False)
    unread_total = NumericProperty(0)
    request_count = NumericProperty(0)
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
    view_status = StringProperty("none")
    view_primary = StringProperty("")
    view_secondary = StringProperty("")
    post_poll_on = BooleanProperty(False)
    post_prompt = StringProperty("")
    post_ready = BooleanProperty(False)
    post_chars = StringProperty("0/500")
    prompt_text = StringProperty("")

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
        self.feed_req, self.feed_loaded, self.chat_from, self.user_from = 0, False, "feed", "people"
        self.streaks = {}
        self.prompt_text = today_prompt()
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
        msg = str(e)
        if "row-level security" in msg and "messages" in msg:
            msg = "You can only message people who are your friends."
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

    def users_key(self, users):
        return [(u["id"], name_of(u), is_online(u.get("seconds_ago")), u.get("note"),
                 badge_text(u.get("seconds_ago")), u.get("status"), u.get("mutual")) for u in users]

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
        if self.api.uid and not self.loading:
            self.bg(self.api.touch, None, lambda e: None)

    def on_resume(self):
        self.heartbeat(0)

    def _on_key(self, window, key, *args):
        """Android back button: back one screen; from a tab go Home; from Home leave the app."""
        if key == 27 and self.root:
            cur = self.root.current
            if cur == "chat":
                self.back()
                return True
            if cur == "user":
                self.close_user()
                return True
            if cur in ("profile", "password"):
                self.back_to_settings()
                return True
            if cur == "note":
                self.close_note()
                return True
            if cur == "compose":
                self.close_compose()
                return True
            if cur in ("contacts", "people", "me", "settings"):
                self.go_tab("feed")
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
            self.request_count = sum(1 for u in self.users if u.get("status") == "incoming")
            self.set_me(me)
            self.loading = False
            self.refresh_contacts()
            self.root.current = "feed"
            self.refresh_feed()
            self.refresh_me()
            self.refresh_streaks()

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
        if self.tick % 12 == 0 and self.root.current == "feed":
            self.refresh_feed(silent=True)  # keep Home fresh (about every 30 seconds)
        if self.tick % 24 == 0:
            self.refresh_streaks()

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
                self.request_count = sum(1 for u in users if u.get("status") == "incoming")
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
            self.unread_total = sum(self.unread.values())
            if changed and self.root.current in ("contacts", "people", "feed"):
                self.refresh_contacts()

        def fail(e):
            self.poll_busy = False

        self.bg(work, done, fail)

    # ---------- contacts ----------
    def refresh_contacts(self):
        if not self.root:
            return
        self.unread_total = sum(self.unread.values())
        q = self.root.ids.search_field.text.strip().lower()
        lst = self.root.ids.contact_list
        lst.clear_widgets()
        rows = []
        for u in self.users:
            if not is_friend(u):
                continue  # only friends can be chatted with
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
                online=is_online(u.get("seconds_ago")), streak=self.streaks.get(u["id"], 0),
                on_release=lambda x, uid=u["id"], n=name: self.open_chat(uid, n)))
        if not rows:
            lst.add_widget(MDLabel(
                text="No matches" if q else "No one else has joined yet.\nInvite a friend to create an account!",
                halign="center", theme_text_color="Hint", size_hint_y=None, height=dp(140)))
        sv = self.root.ids.rail_sv
        hide = not self.prefs.get("rail", True)  # the notes strip now lives on Home
        sv.height, sv.opacity = (0, 0) if hide else (dp(126), 1)
        if not hide:
            self.refresh_rail()
        self.refresh_people()

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
            if not is_friend(u):
                continue
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
        other = self.user_by_id(uid)
        if other and not is_friend(other):
            self.notify(f"Add {name} as a friend to start a conversation.")
            return
        if self.root.current in ("feed", "contacts", "people", "me", "user"):
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
        ids.rail_row.active = bool(self.prefs.get("rail", True))
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
    def go_tab(self, name):
        self.root.current = name
        if name == "feed":
            self.refresh_feed()
        elif name == "people":
            self.refresh_people()
        elif name == "contacts":
            self.refresh_contacts()
            self.refresh_streaks()
        elif name == "me":
            self.refresh_me()

    def open_search(self):
        self.go_tab("people")
        Clock.schedule_once(lambda dt: setattr(self.root.ids.people_search, "focus", True), 0.2)

    # ---------- friends ----------
    def section_header(self, text):
        box = MDBoxLayout(size_hint_y=None, height=dp(34), padding=(dp(14), dp(8), dp(14), 0))
        box.add_widget(SectionLabel(text=text))
        return box

    def refresh_people(self):
        """Friends tab: requests, suggestions, your friends (or search results)."""
        if not self.root:
            return
        q = self.root.ids.people_search.text.strip().lower()
        lst = self.root.ids.people_list
        lst.clear_widgets()

        def row(u):
            name, st, sec = name_of(u), u.get("status") or "friends", u.get("seconds_ago")
            if st == "friends":
                sub = presence_text(sec) or "@" + u["username"]
            elif st == "outgoing":
                sub = "Request sent"
            elif st == "incoming":
                sub = mutual_text(u.get("mutual")) or "Wants to be your friend"
            else:
                sub = mutual_text(u.get("mutual")) or "New on Chatly"
            primary, secondary = buttons_for(st)
            return PersonRow(
                uid=u["id"], name=name, initial=initial(name), color=avatar_color(u["username"]),
                subtitle=sub, online=is_online(sec), status=st, primary=primary, secondary=secondary,
                on_release=lambda x, uid=u["id"]: self.open_user(uid))

        def add_section(title, users, empty=""):
            lst.add_widget(self.section_header(title))
            for u in users:
                lst.add_widget(row(u))
            if not users and empty:
                lst.add_widget(MDLabel(text=empty, halign="center", theme_text_color="Hint",
                                       size_hint_y=None, height=dp(70)))

        def by_name(u):
            return name_of(u).lower()

        if q:
            hits = [u for u in self.users if q in name_of(u).lower() or q in u["username"].lower()]
            if hits:
                add_section("SEARCH RESULTS", sorted(hits, key=by_name))
            else:
                lst.add_widget(MDLabel(text="No one found", halign="center", theme_text_color="Hint",
                                       size_hint_y=None, height=dp(120)))
            return
        incoming = [u for u in self.users if u.get("status") == "incoming"]
        sent = [u for u in self.users if u.get("status") == "outgoing"]
        friends = [u for u in self.users if is_friend(u)]
        suggestions = sorted((u for u in self.users if u.get("status") == "none"),
                             key=lambda u: (-int(u.get("mutual") or 0), by_name(u)))[:15]
        if incoming:
            add_section(f"FRIEND REQUESTS ({len(incoming)})", sorted(incoming, key=by_name))
        if suggestions:
            add_section("PEOPLE YOU MAY KNOW", suggestions)
        if sent:
            add_section("REQUESTS YOU SENT", sorted(sent, key=by_name))
        friends.sort(key=lambda u: (u.get("seconds_ago") is None, u.get("seconds_ago") or 0, by_name(u)))
        add_section(f"YOUR FRIENDS ({len(friends)})" if friends else "YOUR FRIENDS", friends,
                    empty="No friends yet. Send a request to someone above." if suggestions else
                          "No friends yet. Use search to find people.")

    def person_primary(self, row):
        self.do_primary(row.uid, row.status, row.name)

    def person_secondary(self, row):
        self.do_secondary(row.uid, row.status, row.name)

    def do_primary(self, uid, status, name):
        if status == "none":
            self.friend_action(uid, "add")
        elif status == "incoming":
            self.friend_action(uid, "accept")
        elif status == "friends":
            self.open_chat(uid, name)

    def do_secondary(self, uid, status, name):
        if status == "outgoing":
            self.friend_action(uid, "cancel")
        elif status == "incoming":
            self.friend_action(uid, "decline")
        elif status == "friends":
            self.confirm_unfriend(uid, name)

    def friend_action(self, uid, kind):
        """kind: add | cancel | accept | decline | unfriend"""
        def work():
            if kind == "add":
                return self.api.send_request(uid)
            if kind == "accept":
                return self.api.respond_request(uid, True)
            if kind == "decline":
                return self.api.respond_request(uid, False)
            return self.api.remove_friend(uid)  # cancel or unfriend

        self.bg(work, lambda status: self.set_status(uid, status), self.friends_fail)

    def friends_fail(self, e):
        self.loading = False
        msg = str(e)
        if any(k in msg for k in ("friend", "schema cache", "set_bio")):
            msg = "Friends are not set up in your Supabase project yet. Run update_v6.sql in the SQL Editor."
        self.notify(msg[:200])

    def set_status(self, uid, status):
        status = status if isinstance(status, str) else "none"
        for u in self.users:
            if u["id"] == uid:
                u["status"] = status
        self.request_count = sum(1 for u in self.users if u.get("status") == "incoming")
        self.refresh_contacts()  # also redraws the Friends tab and the notes strip
        if self.root.current == "user" and self.view_uid == uid:
            self.fill_view(self.user_by_id(uid))
            self.load_view(uid)

    def confirm_unfriend(self, uid, name):
        def close(*args):
            dlg.dismiss()

        def go(*args):
            dlg.dismiss()
            self.friend_action(uid, "unfriend")

        dlg = MDDialog(
            title="Unfriend?", text=f"{name} will no longer be able to see your posts or message you.",
            buttons=[MDFlatButton(text="CANCEL", on_release=close),
                     MDFlatButton(text="UNFRIEND", theme_text_color="Custom",
                                  text_color=(0.86, 0.2, 0.25, 1), on_release=go)])
        dlg.open()

    # ---------- other people's profiles ----------
    def open_user(self, uid):
        if uid == self.api.uid:
            self.go_tab("me")
            return
        if self.root.current in ("feed", "contacts", "people", "me"):
            self.user_from = self.root.current
        u = self.user_by_id(uid) or {"id": uid, "username": "?", "display_name": None,
                                     "status": "none", "mutual": 0}
        self.fill_view(u)
        self.root.current = "user"
        self.load_view(uid)

    def fill_view(self, u):
        if not u:
            return
        name, st = name_of(u), u.get("status") or "friends"
        self.view_uid = u["id"]
        self.view_name, self.view_username = name, u["username"]
        self.view_initial, self.view_color = initial(name), avatar_color(u["username"])
        self.view_status = st
        self.view_primary, self.view_secondary = buttons_for(st)
        self.view_bio = ""
        if st == "friends":
            self.view_hint, self.view_stats = "", ""
        else:
            first = name.split()[0] if name.split() else name
            self.view_hint = f"Add {first} as a friend to see their profile and posts."
            self.view_stats = mutual_text(u.get("mutual"))

    def load_view(self, uid):
        """Bio, counts and posts: the server only returns them for friends."""
        st = self.view_status
        box = self.root.ids.user_posts
        box.clear_widgets()
        if st != "friends":
            return

        def work():
            try:
                rows = self.api.feed(uid)
            except RuntimeError:
                rows = []
            return self.api.profile(uid), rows

        def done(res):
            if self.view_uid != uid:
                return
            prof, rows = res
            self.view_bio = prof.get("bio") or ""
            fc = prof.get("friends_count")
            pc = prof.get("posts_count") if prof.get("posts_count") is not None else len(rows)
            self.view_stats = f"{fc or 0} friends · {pc} posts"
            self.fill_posts(box, rows, "No posts yet.")

        self.bg(work, done, lambda e: None)

    def close_user(self):
        self.root.current = self.user_from
        if self.user_from == "feed":
            self.refresh_feed(silent=True)
        elif self.user_from == "people":
            self.refresh_people()

    def view_primary_tap(self):
        self.do_primary(self.view_uid, self.view_status, self.view_name)

    def view_secondary_tap(self):
        self.do_secondary(self.view_uid, self.view_status, self.view_name)

    # ---------- my profile tab ----------
    def refresh_me(self):
        if not self.api.uid or not self.root:
            return
        uid = self.api.uid

        def work():
            try:
                rows = self.api.feed(uid)
            except RuntimeError:
                rows = []
            return self.api.profile(uid), rows

        def done(res):
            prof, rows = res
            self.me_bio = prof.get("bio") or ""
            fc = prof.get("friends_count")
            if fc is None:
                fc = sum(1 for u in self.users if is_friend(u))
            pc = prof.get("posts_count") if prof.get("posts_count") is not None else len(rows)
            self.me_stats = f"{fc} friends · {pc} posts"
            self.fill_posts(self.root.ids.me_posts, rows, "You have not posted yet.")

        self.bg(work, done, lambda e: None)

    def fill_posts(self, box, rows, empty):
        box.clear_widgets()
        if not rows:
            box.add_widget(MDLabel(text=empty, halign="center", theme_text_color="Hint",
                                   size_hint_y=None, height=dp(100)))
            return
        for r in rows:
            box.add_widget(self.post_card(r))

    # ---------- home feed ----------
    def refresh_feed(self, silent=False):
        if not self.api.uid or not self.root:
            return
        self.feed_req += 1
        req = self.feed_req

        def done(rows):
            if req == self.feed_req:  # ignore answers to an outdated filter
                self.render_feed(rows)

        def fail(e):
            if req != self.feed_req or (silent and self.feed_loaded):
                return
            msg = str(e)
            if "get_feed" in msg or "schema cache" in msg:
                self.feed_message("Posts need a database update. Run update_v5.sql in the Supabase SQL Editor.")
            else:
                self.feed_message("Could not load posts. Check your connection.")

        self.bg(self.api.feed, done, fail)

    def feed_message(self, text):
        box = self.root.ids.feed_list
        box.clear_widgets()
        box.add_widget(MDLabel(text=text, halign="center", theme_text_color="Hint",
                               size_hint_y=None, height=dp(120)))

    def post_card(self, r):
        name = (r.get("display_name") or r.get("username") or "?").strip()
        card = PostCard(
            pid=r["id"], author_id=r["author"], name=name, initial=initial(name),
            color=avatar_color(r.get("username") or name), meta=age_text(r.get("age_seconds")),
            prompt=("Question of the day: " + r["prompt"]) if r.get("prompt") else "",
            body=r["body"], likes=int(r.get("likes") or 0), liked=bool(r.get("liked")),
            mine=r["author"] == self.api.uid)
        poll = r.get("poll") or []
        if poll:
            votes = r.get("votes") or {}
            card.counts = [int(votes.get(str(i), 0)) for i in range(len(poll))]
            mv = r.get("my_vote")
            card.my_vote = -1 if mv is None else int(mv)
            rows = []
            for i, text in enumerate(poll):
                opt = PollOption(text=str(text), idx=i, card=card, on_release=lambda x: self.vote(x))
                card.ids.poll_box.add_widget(opt)
                rows.append(opt)
            card.poll_rows = rows
            self.update_poll_rows(card)
        return card

    def update_poll_rows(self, card):
        total = sum(card.counts)
        for opt in card.poll_rows:
            n = card.counts[opt.idx] if opt.idx < len(card.counts) else 0
            opt.fill = (n / total) if total else 0
            opt.pct_text = f"{round(100 * n / total)}%" if total else ""
            opt.mine = card.my_vote == opt.idx
        card.votes_text = (f"{total} vote" + ("" if total == 1 else "s")) if card.poll_rows else ""

    def vote(self, opt):
        card = opt.card
        old, new = int(card.my_vote), int(opt.idx)
        if old == new:
            return
        counts = list(card.counts)
        if 0 <= old < len(counts):
            counts[old] = max(0, counts[old] - 1)
        counts[new] += 1
        card.counts, card.my_vote = counts, new  # show the vote instantly
        self.update_poll_rows(card)
        pid = int(card.pid)

        def done(res):
            if isinstance(res, dict) and res is not None:
                card.counts = [int(res.get(str(i), 0)) for i in range(len(card.counts))]
                self.update_poll_rows(card)

        def fail(e):  # put the previous vote back
            back = list(card.counts)
            back[new] = max(0, back[new] - 1)
            if 0 <= old < len(back):
                back[old] += 1
            card.counts, card.my_vote = back, old
            self.update_poll_rows(card)
            self.show_err(e)

        self.bg(lambda: self.api.vote_poll(pid, new), done, fail)

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

    def render_feed(self, rows):
        self.feed_loaded = True
        if not rows:
            self.feed_message("No posts yet. Add friends to see their posts, or share your own!")
            return
        box = self.root.ids.feed_list
        box.clear_widgets()
        for r in rows:
            box.add_widget(self.post_card(r))

    def toggle_like(self, card):
        card.liked = not card.liked
        card.likes = max(0, card.likes + (1 if card.liked else -1))
        pid = int(card.pid)

        def done(res):
            if res and "likes" in res:
                card.likes, card.liked = int(res["likes"]), bool(res.get("liked"))

        def fail(e):  # undo the instant change
            card.liked = not card.liked
            card.likes = max(0, card.likes + (1 if card.liked else -1))
            self.show_err(e)

        self.bg(lambda: self.api.toggle_like(pid), done, fail)

    def confirm_delete_post(self, card):
        pid = int(card.pid)

        def close(*args):
            dlg.dismiss()

        def go(*args):
            dlg.dismiss()
            self.bg(lambda: self.api.delete_post(pid), lambda _: self.refresh_feed(), self.show_err)

        dlg = MDDialog(
            title="Delete post?", text="This removes your post for everyone.",
            buttons=[MDFlatButton(text="CANCEL", on_release=close),
                     MDFlatButton(text="DELETE", theme_text_color="Custom",
                                  text_color=(0.86, 0.2, 0.25, 1), on_release=go)])
        dlg.open()

    def reply_to_post(self, card):
        """Unique to Chatly: answer a post privately, in a chat that quotes it."""
        self.open_chat(card.author_id, card.name)
        field = self.root.ids.msg_field
        field.text = 'Re: "' + short(card.body, 40) + '" '
        Clock.schedule_once(lambda dt: setattr(field, "focus", True), 0.3)

    # ---------- composer ----------
    def open_compose(self, prompt=""):
        ids = self.root.ids
        ids.post_input.text = ""
        self.post_prompt, self.post_poll_on = prompt, False
        for i in range(4):
            ids[f"poll_opt{i}"].text = ""
        self.post_ready, self.post_chars = False, "0/500"
        self.root.current = "compose"
        Clock.schedule_once(lambda dt: setattr(ids.post_input, "focus", True), 0.3)

    def answer_prompt(self):
        self.open_compose(self.prompt_text)

    def close_compose(self):
        self.root.ids.post_input.focus = False
        self.root.current = "feed"

    def on_post_text(self, widget):
        text = widget.text
        if len(text) > 500:
            widget.text = text[:500]
            return
        self.post_chars = f"{len(text)}/500"
        self.recalc_post_ready()

    def poll_options(self):
        ids = self.root.ids
        return [o for o in (ids[f"poll_opt{i}"].text.strip()[:40] for i in range(4)) if o]

    def recalc_post_ready(self):
        ok = bool(self.root.ids.post_input.text.strip())
        if ok and self.post_poll_on:
            opts = self.poll_options()
            ok = len(opts) >= 2 and len({o.lower() for o in opts}) == len(opts)
        self.post_ready = ok

    def toggle_poll(self):
        self.post_poll_on = not self.post_poll_on
        self.recalc_post_ready()

    def on_poll_text(self, widget):
        if len(widget.text) > 40:
            widget.text = widget.text[:40]
            return
        self.recalc_post_ready()

    def share_post(self):
        text = self.root.ids.post_input.text.strip()
        if not text or not self.post_ready:
            return
        prompt = self.post_prompt
        poll = self.poll_options() if self.post_poll_on else []
        self.loading = True

        def done(_):
            self.loading = False
            self.close_compose()
            self.refresh_feed()

        def fail(e):
            self.loading = False
            msg = str(e)
            if poll and ("p_poll" in msg or "create_post" in msg or "schema cache" in msg):
                msg = "Polls are not set up yet. Run update_v7.sql in the Supabase SQL Editor."
            elif "create_post" in msg or "schema cache" in msg:
                msg = "Posts are not set up yet. Run update_v5.sql in the Supabase SQL Editor."
            self.notify(msg[:200])

        self.bg(lambda: self.api.create_post(text, prompt, poll), done, fail)

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
        self.root.current = "feed"
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
