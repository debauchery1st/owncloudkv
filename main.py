from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.lib import osc
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty, NumericProperty
from kivy.utils import platform
from kivy.uix.popup import Popup
import json
from service.main import activityport, serviceport, DEFAULT_LOCAL
from owncloudkv import KV
import os
Builder.load_string(KV)


class OwnCloudPopup(BoxLayout):
    pass


class OwnCloudLayout(BoxLayout):
    oc_update = ObjectProperty(None)
    oc_backup = ObjectProperty(None)
    oc_progress = ObjectProperty(None)
    oc_progress_total = NumericProperty(0)
    oc_progress_current = NumericProperty(0)
    status_label = StringProperty('OFFLINE.')

    def download(self, btn):
        btn.disabled = True
        self.oc_backup.disabled = True
        app = App.get_running_app()
        if not app.login_success:
            btn.disabled = True
            btn.text = "ownCloud offline"
            self.oc_backup.text = "check settings and restart app"
            return False
        self.status_label = "update"
        Clock.schedule_once(app.cloud_update, 1)

    def upload(self, btn):
        btn.disabled = True
        self.oc_update.disabled = True
        app = App.get_running_app()
        if not app.login_success:
            btn.disabled = True
            self.oc_update.text = "ownCloud offline"
            btn.text = "check settings and restart app"
            return False
        self.status_label = "backup"
        Clock.schedule_once(app.cloud_backup, 1)

    def update_progress(self, total, current):
        self.oc_progress_total = total
        self.oc_progress_current = current

    def popup(self):
        def my_callback():
            print("dismiss")
        popup = Popup(content=OwnCloudPopup(), title="Finished.")
        popup.bind(on_dismiss=my_callback)
        popup.open()


class owncloudApp(App):
    oc = None
    service = None
    waiting_for_reply = False
    retries = 0
    oscid = None
    layout = None
    login_success = BooleanProperty(False)
    fin_pic = 'goodbye.jpg'

    def __init__(self, **kwargs):
        super(owncloudApp, self).__init__(**kwargs)

    def build_settings(self, settings):
        with open('config.json', 'r') as settings_json:
            settings.add_json_panel('ownCloud', self.config, data=settings_json.read())

    def build_config(self, config):
        config.setdefaults('General', {
            'own_cloud_server': '',
            'own_cloud_user': '',
            'own_cloud_pass': '',
            'own_cloud_local_dir': DEFAULT_LOCAL,
            'own_cloud_remote_dir': '/backup/test'
        })

    def build(self):
        if platform == 'android':
            import android
            # Logger.info('BUILD: Starting services')
            service = android.AndroidService('ownCloud-kv')
            service.start('service started')
            self.service = service
        else:
            Window.size = (1920, 1080)
        osc.init()
        oscid = osc.listen('127.0.0.1', activityport)
        osc.bind(oscid, self.osc_callback, '/own_cloud_ui')
        Clock.schedule_interval(lambda *x: osc.readQueue(oscid), 0)
        Clock.schedule_once(self.cloud_status)
        self.layout = OwnCloudLayout()
        return self.layout

    def cloud_status(self, dt):
        print("Checking internet status")
        msg_data = {
            'q': 'status',
        }
        osc.sendMsg('/own_cloud_service', [json.dumps(msg_data)], '127.0.0.1', serviceport)

    def osc_callback(self, message, *args):
        msg_data = json.loads(message[2])
        msg_q = msg_data['q']
        msg_a = msg_data['a']
        if msg_q == 'status':
            self.layout.status_label = msg_a
            if msg_a == 'OFFLINE':
                if self.retries < 3:
                    self.retries += 1
                self.login_success = False
                # try to reconnect
                self.send_config()
            elif msg_a == 'ONLINE':
                self.login_success = True
                self.retries = 0
        if msg_q == 'update':
            self.layout.status_label = msg_a
            self.layout.oc_backup.disabled = False
            self.layout.oc_update.disabled = False
        if msg_q == 'backup':
            self.layout.status_label = msg_a
            self.layout.oc_backup.disabled = False
            self.layout.oc_update.disabled = False
        if msg_q == 'progress':
            t, c, msg = msg_a.split(',')
            try:
                total, current = int(t), int(c)
            except Exception as e:
                print(e)
                print("bad cast?")
                total, current = 0, 0
            self.layout.update_progress(total, current)
            self.layout.status_label = msg
        if msg_q == 'popup':
            if msg_a == 'finished':
                local_dir = self.config.get('General', 'own_cloud_local_dir')
                fin_pic = os.path.join(local_dir, 'finished.jpg')
                if os.path.isfile(fin_pic):
                    self.fin_pic = fin_pic
                self.layout.popup()
        if msg_q == 'config':
                self.send_config()

    def send_config(self):
        # send config to service thread
        s = self.config.get('General', 'own_cloud_server')
        u = self.config.get('General', 'own_cloud_user')
        p = self.config.get('General', 'own_cloud_pass')
        g = self.config.get('General', 'own_cloud_local_dir')
        b = self.config.get('General', 'own_cloud_remote_dir')
        msg_data = {
            "q": "connect",
            "s": s,
            "u": u,
            "p": p,
            "g": g,
            "b": b
        }
        osc.sendMsg('/own_cloud_service', [json.dumps(msg_data)], '127.0.0.1', serviceport)

    def cloud_backup(self, dt):
        print('calling ownCloud - backup')
        msg_data = {
            "q": "backup",
            "path": "default"
        }
        osc.sendMsg('/own_cloud_service', [json.dumps(msg_data)], '127.0.0.1', serviceport)

    def cloud_update(self, dt):
        print('calling ownCloud - update')
        msg_data = {
            "q": "update",
            "path": "default"
        }
        osc.sendMsg('/own_cloud_service', [json.dumps(msg_data)], '127.0.0.1', serviceport)


if __name__ == "__main__":
    owncloudApp().run()
