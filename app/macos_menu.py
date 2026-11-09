"""Ukrywanie systemowej pozycji Services w menu tej aplikacji na macOS."""
from __future__ import annotations

import ctypes
import ctypes.util


def hide_services_menu() -> bool:
    """Ukryj pozycję zawierającą NSApplication.servicesMenu, jeśli już istnieje."""
    objc = ctypes.CDLL(ctypes.util.find_library("objc"))
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    get_object = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
    get_item = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(address)
    get_count = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(address)
    set_hidden = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)(address)

    def call(receiver, selector):
        return get_object(receiver, objc.sel_registerName(selector)) if receiver else None

    app = call(objc.objc_getClass(b"NSApplication"), b"sharedApplication")
    main_menu = call(app, b"mainMenu")
    services = call(app, b"servicesMenu")
    if not main_menu or not services or get_count(main_menu, objc.sel_registerName(b"numberOfItems")) < 1:
        return False
    app_item = get_item(main_menu, objc.sel_registerName(b"itemAtIndex:"), 0)
    app_menu = call(app_item, b"submenu")
    if not app_menu:
        return False
    for index in range(get_count(app_menu, objc.sel_registerName(b"numberOfItems"))):
        item = get_item(app_menu, objc.sel_registerName(b"itemAtIndex:"), index)
        if call(item, b"submenu") == services:
            set_hidden(item, objc.sel_registerName(b"setHidden:"), True)
            return True
    return False
