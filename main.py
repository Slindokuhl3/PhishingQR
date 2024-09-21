"""
Developer: SS NGCOBO 
Lastest Frontend functions for QR code app for the Andrord phone
"""
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics.texture import Texture
from kivy.uix.camera import Camera
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivy import platform
import cv2
import os
from pyzbar import pyzbar
import requests
import asyncio
import threading
from jnius import autoclass

# Add this at the top of your file
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path

Camerax = autoclass('androidx.hardware.Camera')
CameraInfo = autoclass('android.hardware.Camera$CameraInfo')

Builder.load_string("""
<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20

        MDLabel:
            text: 'Welcome'
            font_size: '34sp'
            bold: True
            halign: 'center'

        MDTextField:
            id: username
            mode: "outlined"
            size_hint_x: None
            width: "240dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            MDTextFieldLeadingIcon:
                icon: "account"
            MDTextFieldHintText:
                text: "Username"
            MDTextFieldHelperText:
                text: "Enter your username"
                mode: "persistent"
            MDTextFieldTrailingIcon:
                icon: "information"

        MDTextField:
            id: password
            mode: "outlined"
            size_hint_x: None
            width: "240dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            password: True
            MDTextFieldLeadingIcon:
                icon: "lock"
            MDTextFieldHintText:
                text: "Password"
            MDTextFieldHelperText:
                text: "Enter your password"
                mode: "persistent"
            MDTextFieldTrailingIcon:
                icon: "eye-off"

        MDButton:
            on_release: app.login()
            size_hint_x: 1
            MDButtonText:
                text: "Login"

        MDButton:
            on_release: app.show_signup()
            size_hint_x: 1
            MDButtonText:
                text: "Sign Up"

<SignupScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20

        MDLabel:
            text: 'Sign Up'
            font_size: '34sp'
            bold: True
            halign: 'center'
        
        MDTextField:
            id: new_username
            mode: "outlined"
            size_hint_x: None
            width: "240dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            MDTextFieldLeadingIcon:
                icon: "account"
            MDTextFieldHintText:
                text: "New Username"
            MDTextFieldHelperText:
                text: "Choose a username"
                mode: "persistent"
        
        MDTextField:
            id: new_password
            mode: "outlined"
            size_hint_x: None
            width: "240dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            password: True
            MDTextFieldLeadingIcon:
                icon: "lock"
            MDTextFieldHintText:
                text: "New Password"
            MDTextFieldHelperText:
                text: "Choose a password"
                mode: "persistent"

        MDButton:
            on_release: app.register()
            size_hint_x: 1
            MDButtonText:
                text: "Register"

        MDButton:
            on_release: app.switch_screen('login')
            size_hint_x: 1
            MDButtonText:
                text: "Back to Login"

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20

        MDLabel:
            text: 'Main Screen'
            font_size: '34sp'
            bold: True
            halign: 'center'

        MDLabel:
            text: 'You are logged in!'
            halign: 'center'

        MDButton:
            on_release: app.switch_screen('qrscan')
            size_hint_x: 1
            MDButtonText:
                text: "Scan QR Code Or Provide URL"
    
        MDButton:
            on_release: app.logout()
            size_hint_x: 1
            MDButtonText:
                text: "Logout"

<QRScanScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20

        Image:
            id: camera_feed

        MDLabel:
            id: qr_result
            text: ''
            halign: 'center'
        
        MDTextField:
            id: manual_url
            mode: "outlined"
            size_hint_x: None
            width: "240dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            MDTextFieldHintText:
                text: "Or type URL here"
            MDTextFieldHelperText:
                text: "Enter URL manually"
                mode: "on_focus"

        MDButton:
            id: model_menu
            text: "Select Model"
            on_release: root.open_menu()
            MDButtonText:
                text: "Select Model"
                
        MDLabel:
            id: model_type
            text: 'Model Type: Random Forest'
            halign: 'center'

        MDButton:
            on_release: root.check_url()
            size_hint_x: 1
            MDButtonText:
                text: "Check URL"

        MDButton:
            on_release: app.switch_screen('main')
            size_hint_x: 1
            MDButtonText:
                text: "Back to Main"
""")

class LoginScreen(Screen):
    pass

class SignupScreen(Screen):
    pass

class MainScreen(Screen):
    pass

class QRScanScreen(Screen):
    is_scanning = BooleanProperty(False)
    model_type = StringProperty("Random Forest")
    scanned_url = StringProperty("")
    camera = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = None
        self.capture = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()
        Clock.schedule_once(self.setup_menu)

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def setup_menu(self, *args):
        menu_items = [
            {
                "text": f"{item}",
                "on_release": lambda x=item: self.set_model_type(x),
            } for item in ["Random Forest", "Logistic Regression", "SVM"]
        ]
        self.menu = MDDropdownMenu(
            caller=self.ids.model_menu,
            items=menu_items,
            width_mult=4,
        )

    def on_enter(self):
        if platform == 'android':
            request_permissions([Permission.CAMERA])
        face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update, 1.0/30.0)
        self.is_scanning = True

    def on_leave(self):
        Clock.unschedule(self.update)
        if self.capture:
            self.capture.release()
        self.is_scanning = False

    def update(self, dt):
        if self.capture:
            ret, frame = self.capture.read()
            if ret:
                # Convert it to texture
                buf1 = cv2.flip(frame, 0)
                buf = buf1.tostring()
                image_texture = Texture.create(
                    size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                # Display image from the texture
                self.ids.camera_feed.texture = image_texture

                # Scan for QR codes
                barcodes = pyzbar.decode(frame)
                for barcode in barcodes:
                    barcode_data = barcode.data.decode("utf-8")
                    self.scanned_url = barcode_data
                    self.ids.qr_result.text = f"Scanned URL: {barcode_data}"
                    self.ids.manual_url.text = barcode_data
                    Clock.unschedule(self.update)
                    if self.capture:
                        self.capture.release()
                    self.is_scanning = False
                    break

    def set_model_type(self, model_type):
        self.model_type = model_type
        self.ids.model_type.text = f"Model Type: {model_type}"

    def check_url(self, *args):
        url = self.ids.manual_url.text or self.scanned_url

        if url and url != "Scanning...":
            self.show_message("Checking URL...")
            asyncio.run_coroutine_threadsafe(self.check_url_async(url), self.loop)

    async def check_url_async(self, url):
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post('http://localhost:5000/check_url', json={'url': url, 'model_type': self.model_type}, timeout=10)
            )
            response.raise_for_status()

            result = response.json()
            Clock.schedule_once(lambda dt: self.show_result(url, result['is_phishing']))
        except requests.exceptions.RequestException as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)))
                                    
    def show_result(self, url, is_phishing):
        result_text = f"Warning: The URL {url} is likely to be a phishing site." if is_phishing else f"The URL {url} appears to be safe."
        self.show_message(result_text)

    def show_error(self, error_message):
        self.show_message(f"Error checking URL: {error_message}")

    def show_message(self, message):
        popup = Popup(title='Message',
                      content=Label(text=message),
                      size_hint=(None, None), size=(400, 200))
        popup.open()

    def open_menu(self):
        self.menu.open()

class PhishingApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.async_tasks = []

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Darkblue"
        self.sm = ScreenManager()
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(SignupScreen(name='signup'))
        self.sm.add_widget(MainScreen(name='main'))
        self.sm.add_widget(QRScanScreen(name='qrscan'))
        return self.sm
    
    def on_start(self):
        if platform == 'android':
            request_permissions([Permission.INTERNET, Permission.CAMERA])
        Clock.schedule_interval(self.asyncio_loop, 0)
    
    def on_stop(self):
        for task in self.async_tasks:
            task.cancel()

    def asyncio_loop(self, dt):
        loop = asyncio.get_event_loop()
        loop.call_soon(loop.stop)
        loop.run_forever()

    def switch_screen(self, screen_name):
        self.sm.current = screen_name

    def show_signup(self):
        self.switch_screen('signup')

    def show_message(self, message):
        popup = Popup(title='Message',
                      content=Label(text=message),
                      size_hint=(None, None), size=(400, 200))
        popup.open()

    def login(self):
        self.sm.current = 'qrscan'
        """
        username = login_screen.ids.username.text
        password = login_screen.ids.password.text

        if not username or not password:
            self.show_message("Please enter a username and password")
            return
        
        try:
            response = requests.post('http://localhost:5000/login', 
                                     json={'username': username, 'password': password})
            if response.status_code == 200:
                self.switch_screen('main')
            else:
                self.show_message(response.json()['message'])
        except requests.exceptions.RequestException:
            self.show_message("Failed to connect to the server")"""

    def register(self):
        signup_screen = self.sm.get_screen('signup')
        username = signup_screen.ids.new_username.text
        password = signup_screen.ids.new_password.text

        if not username or not password:
            self.show_message("Please enter a username and password")
            return
        
        try:
            response = requests.post('http://localhost:5000/register', 
                                     json={'username': username, 'password': password})
            self.show_message(response.json()['message'])
            if response.status_code == 201:
                self.switch_screen('login')
        except requests.exceptions.RequestException:
            self.show_message("Failed to connect to the server")

    def logout(self):
        self.switch_screen('login')

    def get_application_config(self):
        if platform == 'android':
            return os.path.join(primary_external_storage_path(), '%(appname)s.ini')
        return super(PhishingApp, self).get_application_config()

if __name__ == '__main__':
    PhishingApp().run()
