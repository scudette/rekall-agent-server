## Readme

This directory contains the Rekall Agent Server software. It is written using
the web2py framework and so for convenience it is also checked into the
tree. The only directory which contains Rekall code is applications/Rekall/...

There are currently no other modifications from the prestine web2py sources
wnich can be found at https://github.com/web2py/web2py other than removing of
web2py docs, examples and sample application.


## Getting started.

If you have not yet installed the project dependencies, run
./bootstrap.sh now to download depenencies into the site-packages
directory.

To develop, first install the gcloud SDK as described here:
https://cloud.google.com/sdk/downloads

You can now run the application locally using the AppEngine
delevelopment server. This has some nice features:

1) You can easily log in and log out from different user accounts to
   simulate how Rekall behaves for different users (with different per
   missions granted).

2) The server will automatically pick any changes in the files in this
   directory and reimport the relevant files seemlessly.


### Deploying to AppEngine.

gcloud app deploy . --project rekall-test-site