C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python fix5.py
write candidate: None
selftest candidate: None
still unresolved: ['f_set_write_mode', 'f_selftest']

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python -m py_compile "Q11.py"

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python "Q11.py" --selftest
Traceback (most recent call last):
  File "C:\Users\Project Zero\Desktop\Pegasus Pro 1.2\Q11.py", line 3835, in <module>
    14: f_set_write_mode,
        ^^^^^^^^^^^^^^^^
NameError: name 'f_set_write_mode' is not defined

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>
C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python show4.py > defs.txt

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>type defs.txt
-- all def f_* --
  894| def f_wipe():
 1206| def f_help():
 1210| def f_trouble():
 1220| def f_connect():
 1236| def f_list():
 1246| def f_disconnect():
 1254| def f_kill_server():
 1262| def f_scan():
 1283| def f_reconnect():
 1309| def f_forget():
 1321| def f_shell():
 1329| def f_oneshot():
 1343| def f_info():
 1365| def f_battery():
 1374| def f_identity():
 1395| def f_screenshot():
 1408| def f_record_screen():
 1425| def f_record_mic():
 1446| def f_mirror():
 1464| def f_show_image():
 1473| def f_play_audio():
 1482| def f_play_video():
 1494| def f_pull():
 1503| def f_push():
 1513| def f_ls():
 1521| def f_delete():
 1531| def f_third_party():
 1542| def f_launch():
 1553| def f_install():
 1573| def f_uninstall():
 1583| def f_extract_apk():
 1602| def f_reboot():
 1609| def f_poweroff():
 1616| def f_keyevent():
 1625| def f_reboot_bootloader():
 1641| def f_reboot_recovery():
 1652| def f_fb_devices():
 1666| def f_fb_getvar():
 1684| def f_fb_unlock():
 1709| def f_fb_flash_boot():
 1746| def f_fb_vbmeta():
 1772| def f_tap():
 1785| def f_swipe():
 1804| def f_type():
 1814| def f_unlock():
 1826| def f_lock():
 1833| def f_url():
 1846| def f_send_sms():
 1871| def f_dump_sms():
 1875| def f_dump_contacts():
 1879| def f_dump_calls():
 1883| def f_calendar():
 1895| def f_whatsapp():
 1905| def f_screenshots():
 1912| def f_camera_photos():
 1918| def f_harvest():
 1939| def f_privesc():
 1998| def f_frp():
 2048| def f_frp_chain():
 2092| def f_playprotect():
 2122| def f_metasploit():
 2163| def f_reverse():
 2189| def f_pair():
 2212| def f_pair_qr():
 2229| def f_mdns():
 2399| def f_wasm_stage():
 2434| def f_mp4_poc():
 2452| def f_gif_polyglot():
 2471| def f_embedded():
 2512| def f_ask_model():
 2552| def f_focus_watcher():
 2575| def f_shot_burst():
 2611| def f_fb_flash_part():
 2631| def f_fb_temp_boot():
 2646| def f_fb_update():
 2664| def f_fb_slot():
 2684| def f_fb_oem():
 2712| def f_fb_erase():
 2781| def f_kernel():
 2842| def f_zero_click():
 2887| def f_callback():
 2987| def f_frp_workflows():
 3076| def f_usb_bridge():
 3119| def f_inferor():
 3157| def f_calendar_harvest():
 3682| def f_auto():
 3715| def f_loot():
 3732| def f_logs():
 3762| def f_cam_live():
 3787| def f_cam_photo():
 3804| def f_mic():

-- SET_NUM / SELFTEST_NUM / write refs --
   78| WRITE_MODES = ("root", "shell")
  118| WRITE_MODE = ""
  689|     global WRITE_MODE
  691|         WRITE_MODE = "root"
  692|         return WRITE_MODE
  700|                 WRITE_MODE = "root"
  701|                 return WRITE_MODE
  726|     if not WRITE_MODE:
  727|         WRITE_MODE = "shell"
  728|     return WRITE_MODE
  732|     global WRITE_MODE
  733|     if WRITE_MODE and not force:
  734|         return WRITE_MODE
  739|     if saved in WRITE_MODES and not force:
  740|         WRITE_MODE = saved
  742|         WRITE_MODE = "root"
  743|     elif force or not WRITE_MODE:
  745|     if not WRITE_MODE:
  746|         WRITE_MODE = "shell"
  747|     if WRITE_MODE == "root" and not _probe_write():
  749|         WRITE_MODE = "shell"
  752|         WRITE_FILE.write_text(WRITE_MODE + "\n", encoding="utf-8")
  755|     return WRITE_MODE
  762|     if WRITE_MODE == "root" or _device_root():
  782|     if escalate and WRITE_MODE != "root":
  785|         if WRITE_MODE == "root":
  793|     if WRITE_MODE == "root" or _device_root():
 1976|     findings.append(("write mode", mode, mode == "root"))
 2053|     note(f"write mode: {mode}")
 2097|     note(f"write mode: {mode}")
 3835|     14: f_set_write_mode,
 3916| SELFTEST_NUM = 15
 3969|     global SESSION, WRITE_MODE, AUTO_REBOOT, WIPE_ON_EXIT
 3988|             WRITE_MODE = sys.argv[i + 1]
 3990|             WRITE_MODE = arg.split("=", 1)[1]
 3993|     if WRITE_MODE and WRITE_MODE not in WRITE_MODES:
 3994|         warn(f"invalid --write-mode {WRITE_MODE}; using auto")
 3995|         WRITE_MODE = ""
 4021|                 note(f"write mode: {WRITE_MODE or 'unresolved'}")
 4025|             if choice == str(SELFTEST_NUM):

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python fix6.py
ok    pseudo-actions defined
ok    SET_NUM = 14
selftest exists: True

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python -m py_compile "Q11.py"

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>python "Q11.py" --selftest

==========================================================================================
ADB RESOLUTION
==========================================================================================

[*] PATH: C:\Program Files\platform-tools\adb.EXE
[*] found: C:\Program Files\platform-tools\adb.exe
[*] found: C:\Users\Project Zero\AppData\Local\Android\Sdk\platform-tools\adb.exe
[*] found: C:\Users\Project Zero\AppData\Local\Android\Sdk\platform-tools\adb.exe
[*] found: C:\Android\platform-tools\adb.exe
[*] found: C:\Android\platform-tools\adb.exe
[*] glob: C:\Users\Project Zero\Local Settings\Android\Sdk\platform-tools\adb.exe
[+] adb: C:\Program Files\platform-tools\adb.EXE
[*] Android Debug Bridge version 1.0.41

==========================================================================================
FASTBOOT RESOLUTION
==========================================================================================

[*] PATH: C:\Program Files\platform-tools\fastboot.EXE
[*] found: C:\Program Files\platform-tools\fastboot.exe
[*] found: C:\Users\Project Zero\AppData\Local\Android\Sdk\platform-tools\fastboot.exe
[*] found: C:\Users\Project Zero\AppData\Local\Android\Sdk\platform-tools\fastboot.exe
[*] found: C:\Android\platform-tools\fastboot.exe
[*] found: C:\Android\platform-tools\fastboot.exe
[*] glob: C:\Users\Project Zero\Local Settings\Android\Sdk\platform-tools\fastboot.exe
[+] fastboot: C:\Program Files\platform-tools\fastboot.EXE

==========================================================================================
SELF TEST
==========================================================================================

[+] crypto roundtrip
[+] wasm build+validate
[+] mp4 build+validate
[+] gif build+validate
[+] qr escaping
[+] pure helpers
[+] menu wiring
[+] tcp probe
[+] license hash shape
[+] adb banner validation
[*] 10/10 passed

C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>
C:\Users\Project Zero\Desktop\Pegasus Pro 1.2>
