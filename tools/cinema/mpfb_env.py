"""Enable MPFB 2 (the MakeHuman plugin for Blender) inside bpy, from a checkout at $MPFB_DIR
(default /opt/chars/mpfb2). See setup_realistic.sh."""
import importlib
import os
import sys

import addon_utils
import bpy

MPFB_DIR = os.environ.get('MPFB_DIR', '/opt/chars/mpfb2')


def enable_mpfb():
    repo = bpy.utils.user_resource('EXTENSIONS', path='user_default', create=True)
    link = os.path.join(repo, 'mpfb')
    if not os.path.exists(link):
        os.symlink(os.path.join(MPFB_DIR, 'src', 'mpfb'), link)
    if repo not in sys.path:
        sys.path.append(repo)
    addon_utils.enable('bl_ext.user_default.mpfb', default_set=True,
                       handle_error=lambda e: print('enable error', e))
    return importlib.import_module('bl_ext.user_default.mpfb')
