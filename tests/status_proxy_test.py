"""Run with 64-bit Python against a staged Hub and the mock reader DLL."""
import ctypes as c
from ctypes import wintypes as w
import os
import sys

H = c.c_size_t
hub = c.WinDLL(sys.argv[1])
legacy = '--legacy' in sys.argv
def bind(name, args):
    f = getattr(hub, name)
    f.argtypes, f.restype = args, w.LONG
    return f
establish = bind('SCardEstablishContext', [w.DWORD, c.c_void_p, c.c_void_p, c.POINTER(H)])
release = bind('SCardReleaseContext', [H])
connect = bind('SCardConnectA', [H, c.c_char_p, w.DWORD, w.DWORD, c.POINTER(H), c.POINTER(w.DWORD)])
disconnect = bind('SCardDisconnect', [H, w.DWORD])
free = bind('SCardFreeMemory', [H, c.c_void_p])
premium = bytes.fromhex('3b b0 33 00 91 81 31 6b 35 fc')
bcas = bytes.fromhex('3b f0 12 00 ff 91 81 b1 7c 45 1f 03 99')
ctx, card, proto = H(), H(), w.DWORD()
assert establish(0, None, None, c.byref(ctx)) == 0
try:
    assert connect(ctx, b'Hub Status Test Reader', 2, 2, c.byref(card), c.byref(proto)) == 0
    try:
        for suffix, name_type in [('A', c.c_char_p), ('W', c.c_wchar_p)]:
            status = bind('SCardStatus'+suffix, [H, c.c_void_p, c.POINTER(w.DWORD), c.POINTER(w.DWORD), c.POINTER(w.DWORD), c.c_void_p, c.POINTER(w.DWORD)])
            for mode, expected in [('p',premium), ('b',bcas)]:
                os.environ['HUB_TEST_MODE'] = mode
                if legacy: expected = bcas
                state, protocol, size = w.DWORD(), w.DWORD(), w.DWORD(36)
                atr = (c.c_ubyte*36)()
                assert status(card,None,None,c.byref(state),c.byref(protocol),atr,c.byref(size)) == 0
                assert bytes(atr[:size.value]) == expected
                assert state.value == 6 and protocol.value == 2
                size.value = 0
                assert status(card,None,None,None,None,None,c.byref(size)) == 0
                assert size.value == len(expected)
                size.value = 1
                assert status(card,None,None,None,None,atr,c.byref(size)) & 0xffffffff == 0x80100008
                assert size.value == len(expected)
                # Both allocations belong to Hub, including the public reader alias.
                names, autoatr = c.c_void_p(), c.c_void_p()
                nn, na = w.DWORD(0xffffffff), w.DWORD(0xffffffff)
                assert status(card,c.byref(names),c.byref(nn),None,None,c.byref(autoatr),c.byref(na)) == 0
                assert c.string_at(autoatr,na.value) == expected
                reader = c.cast(names, name_type).value
                assert reader == (b'Hub Status Test Reader' if suffix=='A' else 'Hub Status Test Reader')
                assert free(ctx,names)==0 and free(ctx,autoatr)==0
            if not legacy:
                os.environ['HUB_TEST_MODE']='e'
                size.value=36
                assert status(card,None,None,None,None,atr,c.byref(size)) & 0xffffffff == 0x80100069
            class ReaderState(c.Structure):
                _fields_=[('reader',name_type),('user',c.c_void_p),('current',w.DWORD),('event',w.DWORD),('size',w.DWORD),('atr',c.c_ubyte*36)]
            change = bind('SCardGetStatusChange'+suffix,[H,w.DWORD,c.POINTER(ReaderState),w.DWORD])
            for mode, expected, event in [('p',premium,0x20),('b',bcas,0x20),('n',b'',0x10)]:
                os.environ['HUB_TEST_MODE']=mode
                if legacy: expected,event=bcas,0x20
                rs=ReaderState()
                rs.reader=b'Hub Status Test Reader' if suffix=='A' else 'Hub Status Test Reader'
                assert change(ctx,0,c.byref(rs),1)==0
                assert rs.event & event and rs.event & 2
                assert bytes(rs.atr[:rs.size])==expected
                rs.current=rs.event & ~2
                assert change(ctx,0,c.byref(rs),1) & 0xffffffff == 0x8010000a
            if not legacy:
                os.environ['HUB_TEST_MODE']='e'
                assert change(ctx,0,c.byref(rs),1) & 0xffffffff == 0x80100017
    finally:
        assert disconnect(card,0)==0
finally:
    assert release(ctx)==0
print('PASS: A/W status, actual ATR, lengths, allocations, status changes, errors' if not legacy else 'PASS: legacy DLL fallback for A/W status and status changes',flush=True)
