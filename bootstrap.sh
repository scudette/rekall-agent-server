#!/bin/bash


pip install -t site-packages/ artifacts functools32 oauth2client==4.1.0 humanize
pip install -t site-packages/ PyCrypto httplib2.ca_certs_locater

# This installs the latest distribution version.
pip install -t site-packages/ rekall-lib

# If you want to install rekall-lib from a develop directory you will
# need to symlink the directory manually. This is sadly because pip
# does not support the --target and --editable flags at the same time
# (https://github.com/pypa/pip/issues/4390). Assuming your rekall
# development directory is ~/projects/rekall:

# rm -rf site-packages/rekall_lib
# ln -s ~/projects/rekall/rekall-lib/rekall_lib site-packages/rekall_lib
