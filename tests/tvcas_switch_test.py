"""Exercise real TvCas unload/reload without preloading WinSCard.dll.

Usage: python tvcas_switch_test.py TVTest-directory B-CAS-reader Premium-reader
The test sends only the module's normal card initialization commands.
"""
import ctypes as c
from pathlib import Path
import struct
import sys
import uuid
from _ctypes import FreeLibrary

directory = Path(sys.argv[1]).resolve()
guid = c.create_string_buffer(uuid.UUID('080EDD04-8215-4037-8B66-E03954FD81BD').bytes_le)
kernel = c.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleExW.argtypes = [c.c_ulong, c.c_void_p, c.POINTER(c.c_void_p)]
kernel.GetModuleFileNameW.argtypes = [c.c_void_p, c.c_wchar_p, c.c_ulong]

def imported_winscard(module):
    base = module._handle
    header = c.string_at(base, 4096)
    pe = struct.unpack_from('<I', header, 60)[0]
    imports = struct.unpack_from('<I', header, pe+24+112+8)[0]
    for i in range(100):
        original, _, _, name, iat = struct.unpack('<5I', c.string_at(base+imports+i*20, 20))
        if not name:
            break
        if c.string_at(base+name).lower() != b'winscard.dll':
            continue
        address = c.c_void_p.from_address(base+iat).value
        owner = c.c_void_p()
        assert kernel.GetModuleHandleExW(6, address, c.byref(owner))
        path = c.create_unicode_buffer(32768)
        assert kernel.GetModuleFileNameW(owner, path, len(path))
        return Path(path.value).resolve()
    raise AssertionError('WinSCard import not found')

def check(module_name, reader):
    module = c.WinDLL(str(directory/module_name))
    owner = imported_winscard(module)
    print(module_name, 'imports', owner, flush=True)
    assert str(owner).casefold() == str(directory/'winscard.dll').casefold(), 'Module bypassed SCardHub'
    create = module.TVCAS_CreateInstance
    create.argtypes, create.restype = [c.c_void_p], c.c_void_p
    manager = create(guid)
    assert manager
    vt = c.cast(manager, c.POINTER(c.POINTER(c.c_void_p))).contents
    def method(index, result, *args):
        return c.WINFUNCTYPE(result, c.c_void_p, *args)(vt[index])
    try:
        assert method(20, c.c_bool, c.c_int, c.c_wchar_p)(manager, 0, reader), 'OpenCasCard failed'
        assert method(22, c.c_bool)(manager), 'Card not open'
        assert method(21, c.c_bool)(manager)
        print(module_name, 'card open/close: PASS', flush=True)
    finally:
        method(1, None)(manager)
        FreeLibrary(module._handle)

for cycle in range(3):
    print('Cycle', cycle+1, flush=True)
    check('TVCAS_B25.tvcas', sys.argv[2])
    check('TVCAS_B1.tvcas', sys.argv[3])
print('PASS: B25/B1 module switching retained SCardHub and both cards opened', flush=True)
