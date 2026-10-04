"""Binary-safe access to the current user's macOS preferences (no PyObjC)."""

import ctypes as ct
import plistlib


class Preferences:
    """Read a domain and update only specified keys through CFPreferences."""

    def __init__(self):
        self.cf = ct.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        pointer, index = ct.c_void_p, ct.c_long
        signatures = {
            "CFStringCreateWithCString": ([pointer, ct.c_char_p, ct.c_uint32], pointer),
            "CFPreferencesCopyMultiple": ([pointer] * 4, pointer),
            "CFPreferencesSetMultiple": ([pointer] * 5, None),
            "CFPreferencesSynchronize": ([pointer] * 3, ct.c_bool),
            "CFPropertyListCreateData": ([pointer, pointer, index, ct.c_ulong, pointer], pointer),
            "CFDataGetLength": ([pointer], index),
            "CFDataGetBytePtr": ([pointer], pointer),
            "CFDataCreate": ([pointer, ct.c_char_p, index], pointer),
            "CFPropertyListCreateWithData": ([pointer, pointer, ct.c_ulong, pointer, pointer], pointer),
            "CFRelease": ([pointer], None),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.cf, name)
            function.argtypes, function.restype = arguments, result
        self.user = pointer.in_dll(self.cf, "kCFPreferencesCurrentUser")
        self.host = pointer.in_dll(self.cf, "kCFPreferencesAnyHost")

    def _string(self, value):
        return self.cf.CFStringCreateWithCString(None, value.encode(), 0x08000100)

    def read(self, domain):
        app = self._string(domain)
        value = data = None
        try:
            value = self.cf.CFPreferencesCopyMultiple(None, app, self.user, self.host)
            if not value:
                return {}
            data = self.cf.CFPropertyListCreateData(None, value, 200, 0, None)
            if not data:
                raise RuntimeError(f"Cannot serialize preferences: {domain}")
            raw = ct.string_at(self.cf.CFDataGetBytePtr(data), self.cf.CFDataGetLength(data))
            return plistlib.loads(raw)
        finally:
            for item in (data, value, app):
                if item:
                    self.cf.CFRelease(item)

    def write(self, domain, updates):
        raw = plistlib.dumps(updates, fmt=plistlib.FMT_BINARY)
        app = self._string(domain)
        data = self.cf.CFDataCreate(None, raw, len(raw))
        value = None
        try:
            value = self.cf.CFPropertyListCreateWithData(None, data, 0, None, None)
            if not value:
                raise RuntimeError(f"Cannot encode preferences: {domain}")
            self.cf.CFPreferencesSetMultiple(value, None, app, self.user, self.host)
            if not self.cf.CFPreferencesSynchronize(app, self.user, self.host):
                raise RuntimeError(f"Cannot save preferences: {domain}")
        finally:
            for item in (value, data, app):
                if item:
                    self.cf.CFRelease(item)
