# helpful procedures prone to re-use
#
import os
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


def ocwalk(oc, top, topdown=True, onerror=None, followlinks=False):
    """(os.walk - 'hacked' for owncloud.Client
    """
    try:
        names = oc.list(top)
    except error, err:
        if onerror is not None:
            onerror(err)
        return
    dirs, nondirs = [], []
    for name in names:
        if name.is_dir():
            dirs.append(name)
        else:
            nondirs.append(name)
    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        new_path = name.path
        if name.is_dir():
            for x in ocwalk(oc, new_path, topdown, onerror, followlinks):
                yield x
    if not topdown:
        yield top, dirs, nondirs


if __name__ == "__main__":
    import owncloud
    # fill these out
    OWN_CLOUD_SERVER = ''
    OWN_CLOUD_USER = ''
    OWN_CLOUD_PASS = ''
    oc = owncloud.Client(OWN_CLOUD_SERVER)
    oc.login(OWN_CLOUD_USER, OWN_CLOUD_PASS)
    for root, dirs, files in ocwalk(oc, '/', topdown=False):
        for name in files:
            print("  - {}".format(name.path))
        for name in dirs:
            print("D - {}".format(name.path))
    oc.logout()
