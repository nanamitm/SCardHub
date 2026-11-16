/* 実カードを操作せず、Hub の状態取得と旧式 DLL 互換を検証する。 */
#include <windows.h>
#include <winscard.h>
#include <string.h>

static const BYTE premium[] = {0x3b,0xb0,0x33,0,0x91,0x81,0x31,0x6b,0x35,0xfc};
static const BYTE bcas[] = {0x3b,0xf0,0x12,0,0xff,0x91,0x81,0xb1,0x7c,0x45,0x1f,3,0x99};
static int mode(void) {
    char value[8] = {0};
    GetEnvironmentVariableA("HUB_TEST_MODE", value, sizeof(value));
    return value[0];
}
LONG WINAPI SCardEstablishContext(DWORD scope, LPCVOID a, LPCVOID b, LPSCARDCONTEXT context) {
    *context = 123; return SCARD_S_SUCCESS;
}
LONG WINAPI SCardReleaseContext(SCARDCONTEXT context) { return SCARD_S_SUCCESS; }
LONG WINAPI SCardListReadersA(SCARDCONTEXT context, LPCSTR groups, LPSTR readers, LPDWORD size) {
    const char names[] = "Hub Status Test Reader\0";
    DWORD capacity = *size;
    *size = sizeof(names);
    if (!readers) return SCARD_S_SUCCESS;
    if (capacity < sizeof(names)) return SCARD_E_INSUFFICIENT_BUFFER;
    memcpy(readers, names, sizeof(names)); return SCARD_S_SUCCESS;
}
LONG WINAPI SCardConnectA(SCARDCONTEXT context, LPCSTR reader, DWORD share, DWORD preferred,
                         LPSCARDHANDLE card, LPDWORD protocol) {
    if (strcmp(reader, "Hub Status Test Reader")) return SCARD_E_UNKNOWN_READER;
    *card = 456; *protocol = SCARD_PROTOCOL_T1; return SCARD_S_SUCCESS;
}
LONG WINAPI SCardDisconnect(SCARDHANDLE card, DWORD disposition) { return SCARD_S_SUCCESS; }
LONG WINAPI SCardTransmit(SCARDHANDLE card, LPCSCARD_IO_REQUEST sendpci, LPCBYTE send,
                         DWORD sendlen, LPSCARD_IO_REQUEST recvpci, LPBYTE recv, LPDWORD recvlen) {
    return SCARD_E_UNSUPPORTED_FEATURE;
}
LONG WINAPI SCardStatusA(SCARDHANDLE card, LPSTR readers, LPDWORD nameslen, LPDWORD state,
                        LPDWORD protocol, LPBYTE atr, LPDWORD size) {
    const BYTE *value = mode() == 'b' ? bcas : premium;
    DWORD count = mode() == 'b' ? sizeof(bcas) : sizeof(premium);
    if (mode() == 'e') return SCARD_W_REMOVED_CARD;
    *state = SCARD_SPECIFIC; *protocol = SCARD_PROTOCOL_T1;
    if (*size < count) { *size = count; return SCARD_E_INSUFFICIENT_BUFFER; }
    memcpy(atr, value, count); *size = count; return SCARD_S_SUCCESS;
}
LONG WINAPI SCardGetStatusChangeA(SCARDCONTEXT context, DWORD timeout,
                                 LPSCARD_READERSTATEA states, DWORD count) {
    DWORD i;
    for (i = 0; i < count; i++) {
        SCARD_READERSTATEA *p = &states[i];
        if (strcmp(p->szReader, "Hub Status Test Reader")) return SCARD_E_UNKNOWN_READER;
        if (mode() == 'e') return SCARD_E_READER_UNAVAILABLE;
        p->dwEventState = mode() == 'n' ? SCARD_STATE_EMPTY : SCARD_STATE_PRESENT;
        p->cbAtr = mode() == 'n' ? 0 : mode() == 'b' ? sizeof(bcas) : sizeof(premium);
        memcpy(p->rgbAtr, mode() == 'b' ? bcas : premium, p->cbAtr);
        if ((p->dwCurrentState & ~SCARD_STATE_CHANGED) != p->dwEventState)
            p->dwEventState |= SCARD_STATE_CHANGED;
    }
    return SCARD_S_SUCCESS;
}
