import os
import time

import pyalpm
from pycman.config import PacmanConfig

from up2date_client import up2dateLog
from up2date_client import config
from up2date_client import pacmanUtils
from up2date_client import rhnPackageInfo

log = up2dateLog.initLog()

# file used to keep track of the next time rhn_check
# is allowed to update the package list on the server
LAST_UPDATE_FILE = "/var/lib/up2date/dbtimestamp"

# mark this module as acceptable
__rhnexport__ = [
    'update',
    'remove',
    'refresh_list',
    'fullUpdate',
    'checkNeedUpdate',
    'runTransaction',
    'verify'
]


def remove(package_list, cache_only=None):
    """We have been told that we should remove packages"""
    if cache_only:
        return (0, "no-ops for caching", {})

    if not isinstance(package_list, list):
        return (13, "Invalid arguments passed to function", {})

    log.log_debug("Called remove_packages", package_list)

    conf = PacmanConfig('/etc/pacman.conf')
    handle = conf.initialize_alpm()

    db = handle.get_localdb()
    for package in package_list:
        if db.get_pkg(package) is None:
            return 1, package + " is not installed so it cannot be removed", {}

    t = handle.init_transaction()
    for package in package_list:
        t.remove_pkg(package)

    try:
        t.prepare()
        t.commit()
    except pyalpm.error:
        t.release()
        return 1, "packages.remove failed", {}
    t.release()

    return 0, "packages.remove OK", {}


def update(package_list, cache_only=None):
    """We have been told that we should retrieve/install packages"""
    if not isinstance(package_list, list):
        return (13, "Invalid arguments passed to function", {})

    # Partial updates are not supported on Arch, so just do a full upgrade
    fullUpdate()


def runTransaction(transaction_data, cache_only=None):
    """ Run a transaction on a group of packages.
        This was historicaly meant as generic call, but
        is only called for rollback.
    """
    return 1, "packages.runTransaction not implemented", {}


def fullUpdate(force=0, cache_only=None):
    """ Update all packages on the system. """
    conf = PacmanConfig('/etc/pacman.conf')
    handle = conf.initialize_alpm()

    for db in handle.get_syncdbs():
        t = handle.init_transaction()
        db.update(force)
        t.release()

    t = handle.init_transaction()
    downgrade = False
    t.sysupgrade(downgrade)
    if len(t.to_add) + len(t.to_remove) > 0:
        try:
            t.prepare()
            t.commit()
        except pyalpm.error:
            t.release()
            return 1, "packages.fullUpdate failed", {}
    t.release()
    return 0, "packages.fullUpdate OK", {}


# The following functions are the same as the old up2date ones.
def checkNeedUpdate(rhnsd=None, cache_only=None):
    """ Check if the locally installed package list changed, if
        needed the list is updated on the server
        In case of error avoid pushing data to stay safe
    """
    if cache_only:
        return (0, "no-ops for caching", {})

    data = {}
    dbpath = "/var/lib/rpm"
    cfg = config.initUp2dateConfig()
    if cfg['dbpath']:
        dbpath = cfg['dbpath']
    RPM_PACKAGE_FILE = "%s/Packages" % dbpath

    try:
        dbtime = os.stat(RPM_PACKAGE_FILE)[8]  # 8 is st_mtime
    except:
        return (0, "unable to stat the rpm database", data)
    try:
        last = os.stat(LAST_UPDATE_FILE)[8]
    except:
        last = 0

    # Never update the package list more than once every 1/2 hour
    if last >= (dbtime - 10):
        return (0, "rpm database not modified since last update (or package "
                "list recently updated)", data)

    if last == 0:
        try:
            file = open(LAST_UPDATE_FILE, "w+")
            file.close()
        except:
            return (0, "unable to open the timestamp file", data)

    # call the refresh_list action with a argument so we know it's
    # from rhnsd
    return refresh_list(rhnsd=1)


def refresh_list(rhnsd=None, cache_only=None):
    """ push again the list of rpm packages to the server """
    if cache_only:
        return (0, "no-ops for caching", {})
    log.log_debug("Called refresh_rpmlist")

    ret = None

    try:
        rhnPackageInfo.updatePackageProfile()
    except:
        print("ERROR: refreshing remote package list for System Profile")
        return (20, "Error refreshing package list", {})

    touch_time_stamp()
    return (0, "rpmlist refreshed", {})


def touch_time_stamp():
    try:
        file_d = open(LAST_UPDATE_FILE, "w+")
        file_d.close()
    except:
        return (0, "unable to open the timestamp file", {})
    # Never update the package list more than once every hour.
    t = time.time()
    try:
        os.utime(LAST_UPDATE_FILE, (t, t))

    except:
        return (0, "unable to set the time stamp on the time stamp file %s"
                % LAST_UPDATE_FILE, {})


def verify(packages, cache_only=None):
    log.log_debug("Called packages.verify")
    if cache_only:
        return (0, "no-ops for caching", {})

    data = {}
    data['name'] = "packages.verify"
    data['version'] = 0
    ret, missing_packages = pacmanUtils.verifyPackages(packages)

    data['verify_info'] = ret

    if len(missing_packages):
        data['name'] = "packages.verify.missing_packages"
        data['version'] = 0
        data['missing_packages'] = missing_packages
        return(43, "packages requested to be verified are missing", data)

    return (0, "packages verified", data)
