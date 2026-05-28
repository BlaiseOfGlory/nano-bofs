#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <stdio.h>
#include <windns.h>
#include <lm.h>

typedef PCWSTR (*myInetNtopW)(
    INT Family,
    const VOID *pAddr,
    PWSTR pStringBuf,
    size_t StringBufSize
);

DWORD query_domain(const char *domainname, unsigned short wType, const char *dnsserver, PDNS_RECORD base, PIP4_ARRAY pSrvList)
{
    (void)dnsserver;

    PDNS_RECORD pdns = NULL;
    DWORD options = DNS_QUERY_WIRE_ONLY;
    DNS_FREE_TYPE freetype = DnsFreeRecordListDeep;
    DWORD status = 0;

    status = DNSAPI$DnsQuery_A(domainname, wType, options, pSrvList, &base, NULL);

    pdns = base;
    if (status != 0 || pdns == NULL)
    {
        return status != 0 ? status : DNS_INFO_NO_RECORDS;
    }

    do
    {
        if (pdns->wType == DNS_TYPE_PTR)
        {
            internal_printf("PTR: %s\n", pdns->Data.PTR.pNameHost);
        }
        pdns = pdns->pNext;
    } while (pdns);

    if (base)
    {
        DNSAPI$DnsFree(base, freetype);
    }

    return ERROR_SUCCESS;
}

void NetSessions(wchar_t *hostname, unsigned short resolveMethod, char *dnsserver)
{
    LPSESSION_INFO_10 pBuf = NULL;
    LPSESSION_INFO_10 pTmpBuf;
    DWORD dwLevel = 10;
    DWORD dwPrefMaxLen = MAX_PREFERRED_LENGTH;
    DWORD dwEntriesRead = 0;
    DWORD dwTotalEntries = 0;
    DWORD dwResumeHandle = 0;
    DWORD i;
    DWORD dwTotalCount = 0;
    LPWSTR pszServerName = NULL;
    LPWSTR pszClientName = NULL;
    LPWSTR pszUserName = NULL;
    NET_API_STATUS nStatus;
    DWORD dnsStatus = ERROR_SUCCESS;

    PDNS_RECORD base = NULL;
    myInetNtopW inetntow;
    HMODULE WS = NULL;
    PIP4_ARRAY pSrvList = NULL;
    WKSTA_INFO_100 *pInfo = NULL;

    if (hostname)
    {
        pszServerName = hostname;
    }

    if (resolveMethod == 0)
    {
        WS = LoadLibraryA("WS2_32");
        int (*intinet_pton)(INT, LPCSTR, PVOID);
        if (WS == NULL)
        {
            BeaconPrintf(CALLBACK_ERROR, "Unable to load ws2 lib");
            return;
        }

        inetntow = (myInetNtopW)GetProcAddress(WS, "InetNtopW");
        intinet_pton = (int (*)(INT, LPCSTR, PVOID))GetProcAddress(WS, "inet_pton");
        if (!inetntow || !intinet_pton)
        {
            BeaconPrintf(CALLBACK_ERROR, "Could not load functions");
            goto END;
        }

        if (dnsserver != NULL)
        {
            pSrvList = (PIP4_ARRAY)KERNEL32$LocalAlloc(LPTR, sizeof(IP4_ARRAY));
            if (!pSrvList)
            {
                BeaconPrintf(CALLBACK_ERROR, "could not allocate memory");
                goto END;
            }
            if (intinet_pton(AF_INET, dnsserver, &(pSrvList->AddrArray[0])) != 1)
            {
                BeaconPrintf(CALLBACK_ERROR, "Could not convert dnsserver from ip to binary");
                KERNEL32$LocalFree(pSrvList);
                pSrvList = NULL;
                goto END;
            }
            pSrvList->AddrCount = 1;
        }
    }

    do
    {
        nStatus = NETAPI32$NetSessionEnum(
            pszServerName,
            pszClientName,
            pszUserName,
            dwLevel,
            (LPBYTE *)&pBuf,
            dwPrefMaxLen,
            &dwEntriesRead,
            &dwTotalEntries,
            &dwResumeHandle
        );

        if ((nStatus == NERR_Success) || (nStatus == ERROR_MORE_DATA))
        {
            if ((pTmpBuf = pBuf) != NULL)
            {
                for (i = 0; (i < dwEntriesRead); i++)
                {
                    if (pTmpBuf == NULL)
                    {
                        BeaconPrintf(CALLBACK_ERROR, "An access violation has occurred\n");
                        break;
                    }

                    internal_printf("---------------Session--------------\n");
                    internal_printf("Client: %ls\n", pTmpBuf->sesi10_cname);

                    wchar_t *clientname = pTmpBuf->sesi10_cname;
                    if (clientname[0] == L'\\' && clientname[1] == L'\\')
                    {
                        clientname += 2;
                    }

                    if (resolveMethod == 1)
                    {
                        NET_API_STATUS stat = NETAPI32$NetWkstaGetInfo(clientname, 100, (LPBYTE *)&pInfo);
                        if (stat == NERR_Success)
                        {
                            internal_printf("ComputerName: %S\n", pInfo->wki100_computername);
                            internal_printf("ComputerDomain: %S\n", pInfo->wki100_langroup);
                        }
                        else
                        {
                            internal_printf("ComputerName: NetWkstaGetInfo Failed; %lu\n", stat);
                            internal_printf("ComputerDomain: NetWkstaGetInfo Failed; %lu\n", stat);
                        }

                        if (pInfo != NULL)
                        {
                            NETAPI32$NetApiBufferFree(pInfo);
                            pInfo = NULL;
                        }
                    }
                    else
                    {
                        if (clientname[0] >= L'0' && clientname[0] <= L'9')
                        {
                            char ipAddress[16];
                            char *octets[4];
                            int octet_index = 0;
                            char *token = NULL;
                            char arpaFormat[256];

                            MSVCRT$wcstombs(ipAddress, clientname, sizeof(ipAddress));

                            token = MSVCRT$strtok(ipAddress, ".");
                            while (token != NULL && octet_index < 4)
                            {
                                octets[octet_index] = token;
                                token = MSVCRT$strtok(NULL, ".");
                                octet_index++;
                            }

                            if (octet_index != 4)
                            {
                                internal_printf("PTR: Failed; Invalid IP address\n");
                            }
                            else
                            {
                                MSVCRT$sprintf(
                                    arpaFormat,
                                    "%s.%s.%s.%s.in-addr.arpa",
                                    octets[3],
                                    octets[2],
                                    octets[1],
                                    octets[0]
                                );
                                dnsStatus = query_domain(arpaFormat, DNS_TYPE_PTR, dnsserver, base, pSrvList);
                                if (dnsStatus != ERROR_SUCCESS)
                                {
                                    internal_printf(
                                        "DNS PTR lookup failed for %s: %lu\n",
                                        arpaFormat,
                                        dnsStatus
                                    );
                                    goto END;
                                }
                            }
                        }
                    }

                    internal_printf("User: %ls\n", pTmpBuf->sesi10_username);
                    internal_printf("Active: %lu\n", pTmpBuf->sesi10_time);
                    internal_printf("Idle: %lu\n", pTmpBuf->sesi10_idle_time);
                    internal_printf("-------------End Session------------\n\n");

                    pTmpBuf++;
                    dwTotalCount++;
                }
            }
        }
        else
        {
            BeaconPrintf(CALLBACK_ERROR, "A system error has occurred: %lu\n", nStatus);
        }

        if (pBuf != NULL)
        {
            NETAPI32$NetApiBufferFree(pBuf);
            pBuf = NULL;
        }
    } while (nStatus == ERROR_MORE_DATA);

    if (pBuf != NULL)
    {
        NETAPI32$NetApiBufferFree(pBuf);
    }

    internal_printf("\nTotal of %lu entries enumerated\n", dwTotalCount);

END:
    if (pSrvList != NULL)
    {
        KERNEL32$LocalFree(pSrvList);
    }
    if (WS)
    {
        FreeLibrary(WS);
    }
}

#ifdef BOF

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_HOSTNAME[] = L"__NANO_HOSTNAME__";
    static const int NANO_RESOLVE_METHOD = __NANO_RESOLVE_METHOD__;
    static const char NANO_DNSSERVER[] = "__NANO_DNSSERVER__";

    wchar_t hostname_buffer[260] = {0};
    char dnsserver_buffer[64] = {0};
    wchar_t *hostname = NULL;
    char *dnsserver = NULL;
    size_t i = 0;

    for (i = 0; i < (sizeof(hostname_buffer) / sizeof(hostname_buffer[0])) - 1 && NANO_HOSTNAME[i] != 0; i++)
    {
        hostname_buffer[i] = NANO_HOSTNAME[i];
    }
    hostname_buffer[i] = 0;

    for (i = 0; i < sizeof(dnsserver_buffer) - 1 && NANO_DNSSERVER[i] != 0; i++)
    {
        dnsserver_buffer[i] = NANO_DNSSERVER[i];
    }
    dnsserver_buffer[i] = 0;

    if (hostname_buffer[0] != 0)
    {
        hostname = hostname_buffer;
    }
    if (dnsserver_buffer[0] != 0)
    {
        dnsserver = dnsserver_buffer;
    }

    if (!bofstart())
    {
        return;
    }

    if (hostname)
    {
        BeaconPrintf(CALLBACK_OUTPUT, "[*] Enumerating sessions for system: %ls\n", hostname);
    }

    internal_printf("[*] Resolving client IPs to hostnames using ");
    if (NANO_RESOLVE_METHOD == 0)
    {
        internal_printf("DNS\n\n");
    }
    else
    {
        internal_printf("NetWkstaGetInfo\n\n");
    }

    NetSessions(hostname, (unsigned short)NANO_RESOLVE_METHOD, dnsserver);
    printoutput(TRUE);
}

#endif
