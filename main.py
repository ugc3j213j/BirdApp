import json, os, shutil, traceback
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.image import AsyncImage
from kivy.utils import platform as kivy_platform
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField

# Камера и галерея (будут работать только на Android/iOS)
try:
    from plyer import camera, gallery
    PLYER_AVAILABLE = True
except:
    PLYER_AVAILABLE = False

DATA_FILE = "bird_data.json"
SETTINGS_FILE = "settings.json"
PHOTOS_DIR = "photos"
BIRDS_JSON_NAME = "birds.json"


def load_birds_db(user_data_dir):
    """Копирует birds.json в надёжную папку при первом запуске."""
    target_path = os.path.join(user_data_dir, BIRDS_JSON_NAME)
    try:
        if not os.path.exists(target_path):
            try:
                from kivy.resources import resource_find
                original = resource_find(BIRDS_JSON_NAME)
                if original and os.path.exists(original):
                    shutil.copy2(original, target_path)
                elif os.path.exists(BIRDS_JSON_NAME):
                    shutil.copy2(BIRDS_JSON_NAME, target_path)
            except:
                if os.path.exists(BIRDS_JSON_NAME):
                    shutil.copy2(BIRDS_JSON_NAME, target_path)
        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Ошибка загрузки базы птиц: {e}")
        traceback.print_exc()
        return {}


def extract_size_cm(size_str):
    try:
        return float(size_str.split("–")[0].replace(" см", "").strip())
    except:
        return 0


def extract_wingspan_cm(ws_str):
    try:
        return float(ws_str.split("–")[0].replace(" см", "").strip())
    except:
        return 0


class BirdDetailScreen(MDScreen):
    bird = None
    prev_screen = ""
    photo_enabled = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # На Android даём доступ к камере/галерее, на ПК отключаем кнопки
        self.photo_enabled = PLYER_AVAILABLE and kivy_platform == 'android'

    def on_pre_enter(self):
        self.update_info()

    def update_info(self):
        if not self.bird:
            return
        self.ids.name_label.text = self.bird.get("name", "Неизвестная птица")
        self.ids.latin_label.text = self.bird.get("latin", "")
        self.ids.size_label.text = f"Размер: {self.bird.get('size', '')}"
        self.ids.wingspan_label.text = f"Размах крыльев: {self.bird.get('wingspan', '')}"
        self.ids.desc_label.text = self.bird.get("desc", "")
        self.ids.habitat_label.text = f"Среда: {self.bird.get('среда', 'неизвестно')}"
        self.ids.season_label.text = f"Сезон: {self.bird.get('сезон', 'неизвестно')}"
        self.ids.status_label.text = f"Статус: {self.bird.get('статус', 'неизвестно')}"
        self.ids.color_label.text = f"Окрас: {self.bird.get('окрас', 'неизвестно')}"

        app = MDApp.get_running_app()
        saved = app.get_saved_data(self.bird["name"])
        self.ids.photo_checkbox.active = saved.get("photographed", False)
        if saved.get("photo_path") and os.path.exists(saved["photo_path"]):
            self.ids.photo_preview.source = saved["photo_path"]
            self.ids.photo_status.text = "📷 Есть фото"
        else:
            self.ids.photo_preview.source = ""
            self.ids.photo_status.text = "❌ Нет фото"

    def on_checkbox_active(self, checkbox, value):
        if not self.bird:
            return
        try:
            app = MDApp.get_running_app()
            app.update_bird_data(self.bird["name"], photographed=value)
            self.ids.photo_status.text = "📷 Есть фото" if value else "❌ Нет фото"
            main = app.root.get_screen("main")
            if main.manager.current == "main":
                main.update_counter()
        except Exception as e:
            print(f"Ошибка обновления данных: {e}")

    def take_photo(self):
        if not self.photo_enabled or not self.bird:
            Snackbar(text="Камера недоступна").open()
            return
        try:
            camera.take_picture(
                filename=os.path.join(PHOTOS_DIR, f"{self.bird['name']}_camera.jpg"),
                on_complete=lambda filepath: self.save_photo(filepath)
            )
        except Exception as e:
            Snackbar(text=f"Ошибка камеры: {e}").open()

    def choose_photo(self):
        if not self.photo_enabled or not self.bird:
            Snackbar(text="Галерея недоступна").open()
            return
        try:
            gallery.get_file(on_complete=lambda filepath: self.save_photo(filepath))
        except Exception as e:
            Snackbar(text=f"Ошибка галереи: {e}").open()

    def save_photo(self, original_path):
        if not original_path or not os.path.exists(original_path):
            return
        bird_name = self.bird.get("name", "unknown")
        app = MDApp.get_running_app()
        dest_dir = os.path.join(app.user_data_dir, PHOTOS_DIR)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            safe_name = "".join(c for c in bird_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            dest_path = os.path.join(dest_dir, f"{safe_name}.jpg")
            shutil.copy2(original_path, dest_path)
            app.update_bird_data(bird_name, photo_path=dest_path)
            self.ids.photo_preview.source = dest_path
            self.ids.photo_status.text = "📷 Есть фото"
            main = app.root.get_screen("main")
            if main.manager.current == "main":
                main.update_counter()
            Snackbar(text="Фото сохранено").open()
        except Exception as e:
            Snackbar(text=f"Ошибка сохранения: {e}").open()

    def go_back(self):
        self.manager.current = self.prev_screen if self.prev_screen else "main"


class MainScreen(MDScreen):
    sort_mode = StringProperty("order")
    sort_reverse = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._search_trigger = None

    def on_enter(self):
        self.show_orders()
        self.update_counter()

    def show_orders(self):
        self.ids.main_list.clear_widgets()
        app = MDApp.get_running_app()
        orders = list(app.BIRDS_DB.keys())
        if not orders:
            self.ids.main_list.add_widget(OneLineListItem(text="База не загружена"))
            return
        for order in orders:
            item = OneLineListItem(text=order)
            item.bind(on_release=lambda x, o=order: self.open_order(o))
            self.ids.main_list.add_widget(item)

    def update_counter(self):
        app = MDApp.get_running_app()
        total = len(app.ALL_BIRDS)
        photographed = sum(1 for b in app.ALL_BIRDS if app.get_saved_data(b["name"]).get("photographed", False))
        self.ids.counter_label.text = f"Снято: {photographed} / {total}"

    def on_search_text(self, text):
        if self._search_trigger:
            self._search_trigger.cancel()
        self._search_trigger = Clock.schedule_once(lambda dt: self.do_search(text), 0.2)

    def do_search(self, text):
        if not text or not text.strip():
            self.show_orders()
            self.ids.sort_button.opacity = 1
            return
        self.ids.sort_button.opacity = 0
        search = text.strip().lower()
        app = MDApp.get_running_app()
        results = []
        for bird in app.ALL_BIRDS:
            if search in bird.get("name", "").lower() or search in bird.get("latin", "").lower():
                results.append(bird)
                if len(results) >= 100:
                    break

        if self.sort_mode == "name":
            results.sort(key=lambda b: b.get("name", "").lower(), reverse=self.sort_reverse)
        elif self.sort_mode == "size":
            results.sort(key=lambda b: extract_size_cm(b.get("size", "")), reverse=self.sort_reverse)
        elif self.sort_mode == "wingspan":
            results.sort(key=lambda b: extract_wingspan_cm(b.get("wingspan", "")), reverse=self.sort_reverse)
        elif self.sort_mode == "photographed":
            results.sort(key=lambda b: app.get_saved_data(b["name"]).get("photographed", False),
                         reverse=self.sort_reverse)

        self.ids.main_list.clear_widgets()
        for bird in results[:50]:
            item = OneLineListItem(text=bird.get("name", ""))
            item.bind(on_release=lambda x, b=bird: self.open_detail(b))
            self.ids.main_list.add_widget(item)
        if len(results) > 50:
            self.ids.main_list.add_widget(
                OneLineListItem(text=f"Показано 50 из {len(results)}. Уточните запрос.",
                                theme_text_color="Error")
            )

    def open_order(self, order):
        self.manager.current = "order_screen"
        self.manager.get_screen("order_screen").set_order(order)

    def open_detail(self, bird):
        detail = self.manager.get_screen("detail_screen")
        detail.bird = bird
        detail.prev_screen = self.name
        self.manager.current = "detail_screen"

    def theme_dialog(self):
        dialog = MDDialog(
            title="Тема",
            type="simple",
            buttons=[
                MDFlatButton(text="Светлая", on_release=lambda x: self._set_theme("light", dialog)),
                MDFlatButton(text="Тёмная", on_release=lambda x: self._set_theme("dark", dialog)),
                MDFlatButton(text="Системная", on_release=lambda x: self._set_theme("system", dialog)),
            ],
        )
        dialog.open()

    def _set_theme(self, mode, dialog):
        app = MDApp.get_running_app()
        app.save_setting("theme_mode", mode)
        dialog.dismiss()
        # Задержка для стабильного показа Snackbar
        Clock.schedule_once(lambda dt: Snackbar(text="Тема изменится после перезапуска").open(), 0.3)

    def sort_dialog(self):
        items = [
            {"text": "По порядку отрядов", "on_release": lambda: self._set_sort("order")},
            {"text": "По алфавиту (А-Я)", "on_release": lambda: self._set_sort("name", False)},
            {"text": "По алфавиту (Я-А)", "on_release": lambda: self._set_sort("name", True)},
            {"text": "По размеру (меньше→больше)", "on_release": lambda: self._set_sort("size", False)},
            {"text": "По размеру (больше→меньше)", "on_release": lambda: self._set_sort("size", True)},
            {"text": "По размаху (меньше→больше)", "on_release": lambda: self._set_sort("wingspan", False)},
            {"text": "По размаху (больше→меньше)", "on_release": lambda: self._set_sort("wingspan", True)},
            {"text": "С фото в начале", "on_release": lambda: self._set_sort("photographed", False)},
            {"text": "Без фото в начале", "on_release": lambda: self._set_sort("photographed", True)},
        ]
        self.sort_menu = MDDropdownMenu(caller=self.ids.sort_button, items=items, width_mult=5)
        self.sort_menu.open()

    def _set_sort(self, mode, reverse=False):
        self.sort_mode = mode
        self.sort_reverse = reverse
        if hasattr(self, 'sort_menu'):
            self.sort_menu.dismiss()
        if self.ids.search_field.text.strip():
            self.do_search(self.ids.search_field.text)
        else:
            self.show_orders()


class OrderScreen(MDScreen):
    sort_mode = StringProperty("name")
    sort_reverse = BooleanProperty(False)

    def set_order(self, order_name):
        self.order_name = order_name
        self.ids.order_title.text = order_name
        self.show_birds()

    def show_birds(self):
        app = MDApp.get_running_app()
        birds = app.BIRDS_DB.get(self.order_name, [])
        if self.sort_mode == "name":
            birds = sorted(birds, key=lambda b: b.get("name", "").lower(), reverse=self.sort_reverse)
        elif self.sort_mode == "size":
            birds = sorted(birds, key=lambda b: extract_size_cm(b.get("size", "")), reverse=self.sort_reverse)
        elif self.sort_mode == "wingspan":
            birds = sorted(birds, key=lambda b: extract_wingspan_cm(b.get("wingspan", "")), reverse=self.sort_reverse)
        elif self.sort_mode == "photographed":
            birds = sorted(birds, key=lambda b: app.get_saved_data(b["name"]).get("photographed", False),
                           reverse=self.sort_reverse)

        self.ids.birds_list.clear_widgets()
        for bird in birds:
            saved = app.get_saved_data(bird["name"])
            text = bird.get("name", "")
            if saved.get("photographed") or saved.get("photo_path"):
                text += "  📷"
            item = OneLineListItem(text=text)
            item.bind(on_release=lambda x, b=bird: self.open_detail(b))
            self.ids.birds_list.add_widget(item)

    def open_detail(self, bird):
        detail = self.manager.get_screen("detail_screen")
        detail.bird = bird
        detail.prev_screen = self.name
        self.manager.current = "detail_screen"

    def sort_dialog(self):
        items = [
            {"text": "По алфавиту (А-Я)", "on_release": lambda: self._set_sort("name", False)},
            {"text": "По алфавиту (Я-А)", "on_release": lambda: self._set_sort("name", True)},
            {"text": "По размеру (меньше→больше)", "on_release": lambda: self._set_sort("size", False)},
            {"text": "По размеру (больше→меньше)", "on_release": lambda: self._set_sort("size", True)},
            {"text": "По размаху (меньше→больше)", "on_release": lambda: self._set_sort("wingspan", False)},
            {"text": "По размаху (больше→меньше)", "on_release": lambda: self._set_sort("wingspan", True)},
            {"text": "С фото в начале", "on_release": lambda: self._set_sort("photographed", False)},
            {"text": "Без фото в начале", "on_release": lambda: self._set_sort("photographed", True)},
        ]
        self.sort_menu = MDDropdownMenu(caller=self.ids.sort_button_order, items=items, width_mult=5)
        self.sort_menu.open()

    def _set_sort(self, mode, reverse=False):
        self.sort_mode = mode
        self.sort_reverse = reverse
        if hasattr(self, 'sort_menu'):
            self.sort_menu.dismiss()
        self.show_birds()

    def go_back(self):
        self.manager.current = "main"


class BirdApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.saved_data = {}
        self.settings = {}
        self.BIRDS_DB = {}
        self.ALL_BIRDS = []

    def build(self):
        settings_path = os.path.join(self.user_data_dir, SETTINGS_FILE)
        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            else:
                self.settings = {"theme_mode": "system"}
        except:
            self.settings = {"theme_mode": "system"}

        theme_style = "Light" if self.settings.get("theme_mode") == "light" else (
            "Dark" if self.settings.get("theme_mode") == "dark" else "Light")
        self.theme_cls.theme_style = theme_style
        self.theme_cls.primary_palette = "Teal"

        self.BIRDS_DB = load_birds_db(self.user_data_dir)
        self.ALL_BIRDS = [b for birds in self.BIRDS_DB.values() for b in birds]

        os.makedirs(os.path.join(self.user_data_dir, PHOTOS_DIR), exist_ok=True)

        data_path = os.path.join(self.user_data_dir, DATA_FILE)
        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    self.saved_data = json.load(f)
            except:
                self.saved_data = {}

        kv = """
<MainScreen>:
    name: "main"
    MDBoxLayout:
        orientation: "vertical"
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(6)
            padding: [dp(8), dp(2), dp(8), dp(2)]
            MDTextField:
                id: search_field
                hint_text: "Поиск птицы…"
                mode: "rectangle"
                size_hint_x: 0.7
                size_hint_y: None
                height: dp(40)
                font_size: "13sp"
                pos_hint: {"center_y": .5}
            MDIconButton:
                id: sort_button
                icon: "sort"
                size_hint_x: None
                width: dp(40)
                pos_hint: {"center_y": .5}
                on_release: root.sort_dialog()
            MDIconButton:
                icon: "theme-light-dark"
                size_hint_x: None
                width: dp(40)
                pos_hint: {"center_y": .5}
                on_release: root.theme_dialog()
        MDLabel:
            id: counter_label
            text: "Снято: 0 / 0"
            halign: "right"
            size_hint_y: None
            height: dp(20)
            padding: [0, 0, dp(12), 0]
            theme_text_color: "Secondary"
            font_style: "Caption"
        ScrollView:
            MDList:
                id: main_list

<OrderScreen>:
    name: "order_screen"
    MDBoxLayout:
        orientation: "vertical"
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            padding: [dp(8), dp(2), dp(8), dp(2)]
            MDIconButton:
                icon: "arrow-left"
                on_release: root.go_back()
            MDLabel:
                id: order_title
                font_style: "H6"
                size_hint_x: 0.7
            MDIconButton:
                id: sort_button_order
                icon: "sort"
                size_hint_x: None
                width: dp(40)
                on_release: root.sort_dialog()
        ScrollView:
            MDList:
                id: birds_list

<BirdDetailScreen>:
    name: "detail_screen"
    prev_screen: ""
    photo_enabled: False
    ScrollView:
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(12)
            spacing: dp(10)
            MDBoxLayout:
                size_hint_y: None
                height: dp(40)
                MDFlatButton:
                    text: "Назад"
                    size_hint_x: None
                    width: dp(80)
                    on_release: root.go_back()
                MDLabel:
                    id: name_label
                    font_style: "H5"
                    size_hint_x: 0.8
            AsyncImage:
                id: photo_preview
                size_hint_y: None
                height: dp(200)
                allow_stretch: True
                keep_ratio: True
            MDBoxLayout:
                size_hint_y: None
                height: dp(48)
                MDRaisedButton:
                    text: "Сделать фото"
                    on_release: root.take_photo()
                    disabled: not root.photo_enabled
                MDRaisedButton:
                    text: "Выбрать из галереи"
                    on_release: root.choose_photo()
                    disabled: not root.photo_enabled
            MDBoxLayout:
                size_hint_y: None
                height: dp(48)
                MDCheckbox:
                    id: photo_checkbox
                    size_hint: None, None
                    size: dp(48), dp(48)
                    on_active: root.on_checkbox_active(self, self.active)
                MDLabel:
                    id: photo_status
                    text: "❌ Нет фото"
            MDLabel:
                id: latin_label
                font_style: "Subtitle2"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: size_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: wingspan_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: desc_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: habitat_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: season_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: status_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            MDLabel:
                id: color_label
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
        """
        Builder.load_string(kv)

        sm = MDScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(OrderScreen(name="order_screen"))
        sm.add_widget(BirdDetailScreen(name="detail_screen"))
        return sm

    def save_setting(self, key, value):
        self.settings[key] = value
        try:
            path = os.path.join(self.user_data_dir, SETTINGS_FILE)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def get_saved_data(self, bird_name):
        if bird_name not in self.saved_data:
            self.saved_data[bird_name] = {"photographed": False, "photo_path": ""}
        return self.saved_data[bird_name]

    def update_bird_data(self, bird_name, photographed=None, photo_path=None):
        try:
            data = self.get_saved_data(bird_name)
            if photographed is not None:
                data["photographed"] = photographed
            if photo_path is not None:
                data["photo_path"] = photo_path
            self.save_all_data()
        except Exception as e:
            print(f"Ошибка обновления данных: {e}")

    def save_all_data(self):
        try:
            path = os.path.join(self.user_data_dir, DATA_FILE)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.saved_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")


if __name__ == "__main__":
    BirdApp().run()