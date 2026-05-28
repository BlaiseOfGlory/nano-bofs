#include <windows.h>
#include <string.h>
#include <windns.h>
#include "bofdefs.h"
#include "beacon.h"
#include "base.c"

BOOL resolve_host_ipv4(const char *host, struct in_addr *address)
{
    PDNS_RECORD records = NULL;
    PDNS_RECORD current = NULL;
    DNS_STATUS status = 0;

    if (WS2_32$inet_pton(AF_INET, host, address) == 1)
    {
        return TRUE;
    }

    status = DNSAPI$DnsQuery_A(host, DNS_TYPE_A, DNS_QUERY_STANDARD, NULL, &records, NULL);
    if (status != ERROR_SUCCESS || records == NULL)
    {
        return FALSE;
    }

    current = records;
    while (current != NULL)
    {
        if (current->wType == DNS_TYPE_A)
        {
            address->S_un.S_addr = current->Data.A.IpAddress;
            DNSAPI$DnsFree(records, DnsFreeRecordListDeep);
            return TRUE;
        }
        current = current->pNext;
    }

    DNSAPI$DnsFree(records, DnsFreeRecordListDeep);
    return FALSE;
}


BOOL is_port_open(char *host, int port, int timeout)
{
    BOOL ret = FALSE;
    struct in_addr address;
    struct sockaddr_in target;
    SOCKET sock = INVALID_SOCKET;
    u_long nonblock = 1;
    struct timeval tv;
    struct fd_set sockets;

    intZeroMemory(&address, sizeof(address));
    intZeroMemory(&target, sizeof(target));
    if (!resolve_host_ipv4(host, &address))
    {
        return FALSE;
    }

    target.sin_family = AF_INET;
    target.sin_addr = address;
    target.sin_port = WS2_32$htons((u_short)port);

    sock = WS2_32$socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
    {
        return FALSE;
    }

    WS2_32$ioctlsocket(sock, FIONBIO, &nonblock);

    tv.tv_sec = timeout;
    tv.tv_usec = 0;

    FD_ZERO(&sockets);
    FD_SET(sock, &sockets);

    WS2_32$connect(sock, (const struct sockaddr *)&target, sizeof(target));
    WS2_32$select(1, NULL, &sockets, NULL, &tv);

    if (WS2_32$__WSAFDIsSet(sock, &sockets))
    {
        ret = TRUE;
    }

    WS2_32$closesocket(sock);
    return ret;
}


#ifdef BOF
VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const char NANO_HOST[] = "__NANO_HOST__";
    char host_buffer[sizeof(NANO_HOST)];
    int port = __NANO_PORT__;
    int time_out = __NANO_TIMEOUT__;
    char *port_status = NULL;

    if (!bofstart())
    {
        return;
    }

    memcpy(host_buffer, NANO_HOST, sizeof(NANO_HOST));
    port_status = is_port_open(host_buffer, port, time_out) ? "OPEN" : "FAILED";
    internal_printf("%s:%d %s", host_buffer, port, port_status);

    printoutput(TRUE);
    bofstop();
}
#endif
