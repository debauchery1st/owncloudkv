# ownCloudkv

this kivy app will

- connect to your ownCloud instance (pyocclient)
- walk the specified path, gathering information
- create or reference a local record per file (sqlalchemy)
- download the file if 'last modified' differs from local record
- write the retrieval datetime to the local record upon successful download


it successfully compiles to android apk on the kivy/buildozer vm
 (under the old toolchain)

    
    buildozer android debug
    

