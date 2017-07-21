#!/bin/bash


pip install -t site-packages/ artifacts functools32 oauth2client==4.1.0
pip install -t site-packages/ 'git+https://github.com/google/rekall.git#egg=rekall-lib&subdirectory=rekall-lib'
