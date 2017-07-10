import json
from time import sleep
from kivy.app import App
from kivy.lib import osc
from kivy.logger import Logger
import owncloud
from tools import ocwalk, parent_dir
from cloud_alchemy import CloudUser, CloudFile, load_sql_session, create_new_db
import os
import datetime

db_file = os.path.join(parent_dir, 'ocb.db')
if os.path.isfile(db_file):
    Logger.info("found database, loading...")
    db_session = load_sql_session(db_file)
else:
    Logger.info("creating new database")
    db_session = create_new_db(db_file)

cfg_file = os.path.join(parent_dir, 'ocb.ini')
if os.path.isfile(cfg_file):
    Logger.info("found config file")


DEFAULT_LOCAL = os.path.join(parent_dir, "updates")
DEFAULT_CLOUD = 'http://localhost'

serviceport = 42535
activityport = 42533


def test_connection():
    # send connect message to ourself.
    msg_data = {
        'q': 'connect'
    }
    osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', serviceport)


class CloudServiceApp(App):
    status_label = "OFFLINE"
    login_success = False
    keep_running = True
    busy = False
    oc = None
    OWN_CLOUD_SERVER = ''
    OWN_CLOUD_USER = ''
    OWN_CLOUD_PASS = ''
    OWN_LOCAL_DIR = ''
    BUILD_DIR = ''

    def __init__(self, **kwargs):
        super(CloudServiceApp, self).__init__(**kwargs)
        if len(DEFAULT_LOCAL) > 0:
            self.OWN_LOCAL_DIR = DEFAULT_LOCAL
        Logger.info("hello")

    def osc_callback(self, message, *args):
        msg_data = json.loads(message[2])
        msg_q = msg_data['q']
        Logger.info('got message : {}'.format(msg_q))
        if msg_q == 'status':
            Logger.info('send back the status')
            msg_data = {
                'q': 'status',
                'a': str(self.status_label)
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        if msg_q == 'update':
            Logger.info('check for update')
            msg_data = {
                'q': 'status',
                'a': 'checking for updates'
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
            # call function
            self.check_updates()
        if msg_q == 'logout':
            Logger.info('logging out')
            self.oc.logout()
            self.keep_running = False
        if msg_q == 'backup':
            Logger.info('requested backup...')
            msg_data = {
                'q': 'backup',
                'a': 'backup feature is unavailable at this time.'
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        if msg_q == 'connect':
            self.OWN_CLOUD_SERVER = msg_data['s']
            self.OWN_CLOUD_USER = msg_data['u']
            self.OWN_CLOUD_PASS = msg_data['p']
            self.OWN_LOCAL_DIR = msg_data['g']
            self.BUILD_DIR = msg_data['b']
            self.connect_to_cloud(self.OWN_CLOUD_SERVER, self.OWN_CLOUD_USER, self.OWN_CLOUD_PASS)

    def connect_to_cloud(self, s, u, p, reply=True):
        if s is None:
            Logger.info('error reading server info from config, using default')
        if u is None:
            Logger.info('error reading user info from config, using default')
        if p is None:
            Logger.info('error reading user info from config, using default')
        Logger.info('connecting to {}'.format(s))
        if s is None:
            return False
        self.oc = owncloud.Client(s)
        try:
            Logger.info("logging in...")
            self.oc.login(u, p)
            self.status_label = "ONLINE"
            self.login_success = True
            Logger.info("ok. logged in")
        except Exception as e:
            self.status_label = str(e) + '\n' + 'OWN_CLOUD_LOGIN_ERROR'
            self.login_success = False
        if reply:
            msg_data = {
                'q': 'status',
                'a': str(self.status_label)
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)

    def check_updates(self):
        Logger.info(' - check for updates...')
        # check for user in db
        q = db_session.query(CloudUser).\
            filter(CloudUser.own_cloud_server.like(self.OWN_CLOUD_SERVER)).\
            filter(CloudUser.own_cloud_user.like(self.OWN_CLOUD_USER)).first()
        if q is None:
            u = CloudUser(own_cloud_server=self.OWN_CLOUD_SERVER,
                          own_cloud_user=self.OWN_CLOUD_USER)
            db_session.add(u)
            db_session.commit()
        else:
            u = q
        # call ocwalk
        new_files = []
        new_dirs = []
        file_updates = []
        categories = dict()
        top = self.BUILD_DIR
        for root, dirs, files in ocwalk(self.oc, top, topdown=False):
            for name in files:
                etag = json.loads(name.attributes['{DAV:}getetag'])
                lm = name.attributes['{DAV:}getlastmodified']
                # check for a record of this file
                q = db_session.query(CloudFile).\
                    filter(CloudFile.attr_etag.like(etag)).first()
                # determine category from path name
                full_path = name.path
                # cut the top off
                relative_path = full_path.split(top)[1]
                category = relative_path.split('/')[1]
                if category not in categories.keys():
                    # create the category
                    categories[category] = {
                        "total": 0,
                        "new": 0
                    }
                    msg_data = {
                        'q': 'status',
                        'a': 'checking {} for updates...'.format(category)
                    }
                    osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
                # increase file count for category
                categories[category]["total"] += 1
                if q is None:
                    # add a new record for this file
                    new_files.append(CloudFile(date_format=name._DATE_FORMAT, attr_etag=etag,
                                               attr_modified=lm,
                                               file_type=name.file_type,
                                               file_name=name.name, file_path=name.path,
                                               user_id=u.user_id, category=category, rel_path=relative_path))
                    categories[category]["new"] += 1
                else:
                    # found file in db
                    file_record = q
                    last_modified = file_record.attr_modified
                    retrieved = file_record.retrieved
                    if "never" in retrieved:
                        print("never retrieved")
                        file_updates.append(file_record)
                    elif last_modified == lm:
                        print("unmodified")
                        # file hasn't been modified
                        Logger.info('skipping duplicate file, ' + ''.join([root, name.name]))
                    else:
                        print("modified")
                        file_updates.append(file_record)
            for name in dirs:
                etag = json.loads(name.attributes['{DAV:}getetag'])
                lm = name.attributes['{DAV:}getlastmodified']
                # check for a record of this directory
                q = db_session.query(CloudFile).\
                    filter(CloudFile.attr_etag.like(etag)).first()
                if q is None:
                    new_dirs.append(name)
                Logger.info('D - {}'.format(name.path))
                msg_data = {
                    'q': 'status',
                    'a': 'checking dir {} for updates...'.format(name.name)
                }
                osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        num_new = len(new_files)
        num_dirs = len(new_dirs)
        num_updated = len(file_updates)
        if num_new > 0:
            db_session.add_all(new_files)
            db_session.commit()
        a = "{} new files".format(num_new)
        a += '\n{} folders'.format(num_dirs)
        if num_updated > 0:
            a += '\n{} existing files to be updated'.format(num_updated)
        Logger.info(' - send result')
        msg_data = {
            'q': 'status',
            'a': a
        }
        # send notification
        osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        sleep(3)
        a = ""
        for cat in categories.keys():
            if len(a) > 0:
                a += "\n"
            a += "{} - total: {} | new: {}".format(cat, categories[cat]["total"], categories[cat]["new"])
        msg_data = {
            'q': 'status',
            'a': a
        }
        # send notification
        osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        if num_new + num_updated > 0:
            sleep(3)
            msg_data = {
                'q': 'status',
                'a': 'Downloading files...'
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
            sleep(3)
            # SYNC FILES
            self.sync(top, new_files, file_updates)
        else:
            msg_data = {
                'q': 'update',
                'a': 'no updates to download.'
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)

    def sync(self, top, new_files, file_updates):
        def cloud_notify(a):
            msg_data = {
                'q': 'status',
                'a': a
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)

        def cloud_progress(total, current=0, msg=''):
            a = "{},{},{}".format(total, current, msg)
            msg_data = {
                'q': 'progress',
                'a': a
            }
            osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        cloud_notify('ready to sync...')
        # get new files
        dl_total = len(new_files) + len(file_updates)
        dl_current = 0
        msg = ""
        for f in new_files:
            if f.file_type == 'file':
                try:
                    rel_dir = DEFAULT_LOCAL + f.rel_path.split(f.file_name)[0][:-1]
                except Exception as e:
                    print(e)

                if not os.path.isdir(rel_dir):
                    Logger.info('creating relative dir : {}'.format(rel_dir))
                    os.makedirs(rel_dir)
                f_local = os.path.join(rel_dir, f.file_name)
                try:
                    self.oc.get_file(f.file_path, f_local)
                    msg = 'Downloaded {} of {} new files...\n - {}'.format(dl_current, dl_total, f_local)
                    dl_current += 1
                    # file_record retrieved
                    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
                    date_str = now.strftime(f.date_format)
                    f.retrieved = date_str
                    db_session.commit()
                except Exception as e:
                    if 'dir' in e:
                        Logger.info('dir')
                        dl_current += 1
                        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
                        date_str = now.strftime(f.date_format)
                        f.retrieved = date_str
                        db_session.commit()
                    Logger.info(e)
            cloud_progress(dl_total, dl_current, msg)
        msg = ""
        for f in file_updates:
            if f.file_type == 'file':
                rel_dir = DEFAULT_LOCAL + f.rel_path.split(f.file_name)[0][:-1]
                if not os.path.isdir(rel_dir):
                    Logger.info('creating relative dir : {}'.format(rel_dir))
                    os.makedirs(rel_dir)
                f_local = os.path.join(rel_dir, f.file_name)
                try:
                    self.oc.get_file(f.file_path, f_local)
                    msg = 'Updated {} of {} files...\n - {}'.format(dl_current, dl_total, f_local)
                    dl_current += 1
                    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
                    date_str = now.strftime(f.date_format)
                    f.retrieved = date_str
                    # save db changes
                    db_session.commit()
                except Exception as e:
                    if 'dir' in e:
                        Logger.info('dir')
                        dl_current += 1
                        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
                        date_str = now.strftime(f.date_format)
                        f.retrieved = date_str
                        # save db changes
                        db_session.commit()
                    Logger.info(e)
            cloud_progress(dl_total, dl_current, msg)
        a = 'Downloaded {} of {} files.'.format(dl_current, dl_total)
        msg_data = {
            'q': 'update',
            'a': a
        }
        osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)
        sleep(3)
        msg_data = {
            'q': 'popup',
            'a': 'finished'
        }
        osc.sendMsg('/own_cloud_ui', [json.dumps(msg_data)], '127.0.0.1', activityport)

    def logout(self):
        try:
            self.oc.logout()
        except Exception as e:
            # not logged in yet?
            Logger.info(e)

    def walk_folder(self):
        # walk our live folder
        if self.oc is not None:
            for root, dirs, files in ocwalk(self.oc, self.BUILD_DIR, topdown=False):
                for name in files:
                    Logger.info(''.join([root, name.name]))
                for name in dirs:
                    Logger.info(''.join([name.path]))

    def on_stop(self):
        self.logout()
        Logger.info("logged out")

    def status(self, m):
        Logger.info(m)
        # send the status back
        msg_data = {
            "text": self.status_label
        }
        osc.sendMsg('/own_cloud', [json.dumps(msg_data)], '127.0.0.1', activityport)


if __name__ == "__main__":
    osc.init()
    oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    cloud_service = CloudServiceApp()
    osc.bind(oscid, cloud_service.osc_callback, '/own_cloud_service')
    while cloud_service.keep_running:
        osc.readQueue(oscid)
        sleep(.1)
    Logger.info("good-bye")
