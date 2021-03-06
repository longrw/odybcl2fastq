import os
import stat
import logging
import shutil
import json
import re

def chmod_rec(path, d_permissions, f_permissions):
    '''
    chmod recursively assigning permissions by type
    '''
    for root, dirs, files in os.walk(path):
        if d_permissions:
            chmod_list(_join_root(root, dirs), d_permissions)
        if f_permissions:
            chmod_list(_join_root(root, files), f_permissions)

def chmod_list(items, permissions):
    for item in items:
        os.chmod(item, permissions)

def _join_root(root, items):
    return [os.path.join(root, i) for i in items]

def copy(src, dest):
    # if is directory remove before copy, copytree errors when dir exists
    logging.info('Copying %s to %s' % (src, dest))
    if os.path.isdir(src):
        if os.path.exists(dest):
            logging.warn('%s exists, overwritting with copy of %s' % (dest,
                src))
            print('deleting' + dest)
            shutil.rmtree(dest)
        # copy src dir to dest
        shutil.copytree(src, dest)
        print('copytree')
    else:
        if os.path.exists(dest):
            logging.warn('%s exists, overwritting with copy of %s' % (dest,
                src))
            print('deleting' + dest)
            os.remove(dest)
        shutil.copy(src, dest)
        print('copyfile')
    logging.info('Successfully copied %s to %s' % (src, dest))

def load_json(path):
    obj = {}
    with open(path, 'r') as data:
        obj = json.load(data)
    return obj

def touch(run_dir, file):
    # touch a processed file in the run_dir
    path = run_dir + file
    with open(path, 'w+'):
        os.utime(path, None)

def alphanumeric(str):
    if str:
        return re.match(r"^[\w-]+$", str)
    else:
        return True

def contains_whitespace(str):
    return (str and re.search(r"\s", str))
