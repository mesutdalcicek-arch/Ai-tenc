[app]
title = AI Forge
package.name = aiforge
package.domain = org.aiforge
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0.0

requirements = python3==3.11.6,kivy==2.3.0,httpx==0.27.0,anyio,sniffio,h11,httpcore,certifi,idna

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.gradle_dependencies = 

p4a.bootstrap = sdl2
p4a.branch = master

[buildozer]
log_level = 2
warn_on_error = 1
