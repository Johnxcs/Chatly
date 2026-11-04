import os
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

<Bubble>:
    orientation: "horizontal"
    adaptive_height: True
    padding: dp(10), dp(2)
    Widget:
        size_hint_x: 1 if root.mine else None
        width: 0
    MDCard:
        orientation: "vertical"
        size_hint: None, None
        width: max(lbl.width, tlbl.width) + dp(28)
        height: lbl.height + tlbl.height + dp(20)
        radius: [20, 20, 6, 20] if root.mine else [20, 20, 20, 6]
        padding: dp(14), dp(8)
        spacing: dp(2)
        elevation: 0
        md_bg_color: PRIMARY if root.mine else WHITE
        MDLabel:
            id: lbl
            text: root.text
            size_hint: None, None
            text_size: min(root.width * .74, dp(300)), None
            size: self.texture_size
            theme_text_color: "Custom"
            text_color: WHITE if root.mine else INK
        MDLabel:
            id: tlbl
            text: root.time
            size_hint: None, None
            size: self.texture_size
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: (1, 1, 1, .75) if root.mine else MUTED
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
    MDCard:
        size_hint: None, None
        size: dp(54), dp(54)
        radius: [dp(27)]
        elevation: 0
        pos_hint: {"center_y": .5}
        md_bg_color: root.avatar_color
        MDLabel:
            text: root.initial
            text_size: self.size
            halign: "center"
            valign: "middle"
            bold: True
            font_style: "H6"
            theme_text_color: "Custom"
            text_color: WHITE
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
    MDCard:
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
                padding: dp(24), dp(34), dp(24), dp(10)
                spacing: dp(8)
                MDCard:
                    size_hint: None, None
                    size: dp(76), dp(76)
                    radius: [dp(26)]
                    elevation: 0
                    md_bg_color: WHITE
                    pos_hint: {"center_x": .5}
                    MDIcon:
                        icon: "message-text"
                        font_size: "40sp"
                        halign: "center"
                        valign: "middle"
                        text_size: self.size
                        theme_text_color: "Custom"
                        text_color: PRIMARY
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
                padding: dp(24), dp(24), dp(24), dp(16)
                spacing: dp(12)
                MDLabel:
                    text: "Create your account" if app.signup_mode else "Welcome back"
                    font_style: "H5"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: INK
                    size_hint_y: None
                    height: dp(40)
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(64) if app.signup_mode else 0
                    opacity: 1 if app.signup_mode else 0
                    disabled: not app.signup_mode
                    MDTextField:
                        id: username_field
                        hint_text: "Username (3-24 characters)"
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
                Widget:

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
                    icon: "logout"
                    pos_hint: {"center_y": .5}
                    theme_icon_color: "Custom"
                    icon_color: MUTED
                    on_release: app.logout()
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
        name: "chat"
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
                    on_release: app.back()
                MDCard:
                    size_hint: None, None
                    size: dp(42), dp(42)
                    radius: [dp(21)]
                    elevation: 0
                    pos_hint: {"center_y": .5}
                    md_bg_color: app.peer_color
                    MDLabel:
                        text: app.peer_initial
                        text_size: self.size
                        halign: "center"
                        valign: "middle"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: WHITE
                MDLabel:
                    text: app.peer_name
                    font_style: "Subtitle1"
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


class Supa:
    """Minimal Supabase client (Auth + PostgREST) using plain HTTPS requests."""

    def __init__(self, on_tokens=None):
        self.base = config.SUPABASE_URL.rstrip("/")
        self.key = config.SUPABASE_ANON_KEY
        self.access = self.refresh = self.uid = None
        self.username = ""
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
        self.username = (user.get("user_metadata") or {}).get("username", "")
        if self.on_tokens:
            self.on_tokens(self.refresh)

    def ensure(self):
        if self.refresh and time.time() > self.exp:
            self._set(self._req("POST", "/auth/v1/token?grant_type=refresh_token", auth=False,
                                json={"refresh_token": self.refresh}))

    # ----- auth -----
    def sign_up(self, email, password, username):
        d = self._req("POST", "/auth/v1/signup", auth=False,
                      json={"email": email, "password": password, "data": {"username": username}})
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
        rows = self._req("GET", "/rest/v1/profiles", params={"select": "id,username", "order": "username"})
        return [r for r in rows if r["id"] != self.uid]

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
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY, sender TEXT NOT NULL, receiver TEXT NOT NULL,
                    text TEXT NOT NULL, created_at TEXT);
                CREATE INDEX IF NOT EXISTS idx_pair ON messages(sender, receiver, id);
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
            """)

    def save_users(self, users):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM users")
            self.conn.executemany("INSERT INTO users(id, username) VALUES(?, ?)",
                                  [(u["id"], u["username"]) for u in users])

    def load_users(self):
        with self.lock:
            rows = self.conn.execute("SELECT id, username FROM users ORDER BY username").fetchall()
        return [dict(r) for r in rows]

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


class ContactRow(ButtonBehavior, MDBoxLayout):
    name = StringProperty("")
    subtitle = StringProperty("")
    initial = StringProperty("?")
    avatar_color = ListProperty([0, 0.52, 1, 1])
    unread = NumericProperty(0)


class ChatApp(MDApp):
    signup_mode = BooleanProperty(False)
    loading = BooleanProperty(False)
    me_name = StringProperty("")
    peer_name = StringProperty("")
    peer_initial = StringProperty("")
    peer_color = ListProperty([0, 0.52, 1, 1])

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
        Window.softinput_mode = "below_target"
        return Builder.load_string(KV)

    def on_start(self):
        Clock.schedule_interval(self.poll, 2.5)
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
            if not 3 <= len(name) <= 24:
                self.loading = False
                self.notify("Username must be 3-24 characters")
                return
            self.bg(lambda: self.api.sign_up(email, pw, name), self.signed_up, self.auth_fail)
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
        if self.store.exists("session"):
            self.store.delete("session")

    def enter_app(self):
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
            last = resume_from if resume_from is not None else self.api.latest_incoming_id()
            local.save_users(users)
            local.set_meta("last_id", last)
            return users, last

        def done(res):
            self.users, self.last_id = res
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
            if users is not None and users != self.users:
                self.users, changed = users, True
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
            if q and q not in u["username"].lower():
                continue
            last = self.local.last_message(self.api.uid, u["id"]) if self.local and self.api.uid else None
            rows.append((last["id"] if last else 0, u, last))
        rows.sort(key=lambda r: (-r[0], r[1]["username"].lower()))  # recent chats first
        for _, u, last in rows:
            if last:
                text = " ".join(last["text"].split())
                text = text if len(text) <= 38 else text[:36] + "..."
                sub = ("You: " if last["sender"] == self.api.uid else "") + text
            else:
                sub = "Tap to start chatting"
            lst.add_widget(ContactRow(
                name=u["username"], subtitle=sub, initial=initial(u["username"]),
                avatar_color=avatar_color(u["username"]), unread=self.unread.get(u["id"], 0),
                on_release=lambda x, uid=u["id"], name=u["username"]: self.open_chat(uid, name)))
        if not rows:
            lst.add_widget(MDLabel(
                text="No matches" if q else "No one else has joined yet.\nInvite a friend to create an account!",
                halign="center", theme_text_color="Hint", size_hint_y=None, height=dp(140)))

    # ---------- chat ----------
    def open_chat(self, uid, name):
        self.peer = uid
        self.unread.pop(uid, None)
        self.peer_name, self.peer_initial, self.peer_color = name, initial(name), avatar_color(name)
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

        def done(rows):
            if self.peer != uid:
                return
            self.msgs[uid] = rows
            self.seen.update(m["id"] for m in rows)
            self.rebuild_chat()

        self.bg(fetch, done)

    def back(self):
        self.peer = None
        self.root.current = "contacts"
        self.refresh_contacts()

    def rebuild_chat(self):
        box = self.root.ids.msg_list
        box.clear_widgets()
        for m in self.msgs.get(self.peer, []):
            self.add_bubble(m, scroll=False)
        self.scroll_down()

    def add_bubble(self, m, scroll=True):
        self.root.ids.msg_list.add_widget(Bubble(
            text=m["text"], mine=m["sender"] == self.api.uid, time=fmt_time(m.get("created_at"))))
        if scroll:
            self.scroll_down()

    def scroll_down(self):
        Clock.schedule_once(lambda dt: setattr(self.root.ids.scroll, "scroll_y", 0), 0.1)

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

        self.bg(push, done)


if __name__ == "__main__":
    ChatApp().run()
