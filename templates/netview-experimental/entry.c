#include <windows.h>
#include <lmserver.h>
#include <lmerr.h>
#include "lm.h"
#include "beacon.h"
#include "bofdefs.h"
#include "base.c"

void netview_enum(wchar_t *domain)
{
    NET_API_STATUS nStatus;
    LPWSTR pszServerName = NULL;
    DWORD dwLevel = 101;
    LPSERVER_INFO_101 pBuf = NULL;
    LPSERVER_INFO_101 pTmpBuf;
    DWORD dwPrefMaxLen = MAX_PREFERRED_LENGTH;
    DWORD dwEntriesRead = 0;
    DWORD dwTotalEntries = 0;
    DWORD dwServerType = SV_TYPE_ALL;
    LPWSTR pszDomainName = domain;
    DWORD dwResumeHandle = 0;
    int i = 0;

    nStatus = NETAPI32$NetServerEnum(
        pszServerName,
        dwLevel,
        (LPBYTE *)&pBuf,
        dwPrefMaxLen,
        &dwEntriesRead,
        &dwTotalEntries,
        dwServerType,
        pszDomainName,
        &dwResumeHandle
    );
    if ((nStatus == NERR_Success) || (nStatus == ERROR_MORE_DATA))
    {
        if ((pTmpBuf = pBuf) != NULL)
        {
            for (i = 0; i < dwEntriesRead; i++)
            {
                if (pTmpBuf == NULL)
                {
                    BeaconPrintf(CALLBACK_ERROR, "Could not access entry");
                    return;
                }
                internal_printf("%S\n", pTmpBuf->sv101_name);
                pTmpBuf++;
            }
        }
    }
    if (pBuf != NULL)
    {
        NETAPI32$NetApiBufferFree(pBuf);
    }
}

#ifdef BOF

VOID go(
    IN PCHAR Buffer,
    IN ULONG Length
)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_DOMAIN[] = L"__NANO_DOMAIN__";
    wchar_t domain_buffer[sizeof(NANO_DOMAIN) / sizeof(NANO_DOMAIN[0])];
    wchar_t *domain = NULL;

    if (!bofstart())
    {
        return;
    }

    // Mirror the upstream copy-before-call behavior for the embedded domain.
    memcpy(domain_buffer, NANO_DOMAIN, sizeof(NANO_DOMAIN));
    if (domain_buffer[0] != 0)
    {
        domain = domain_buffer;
    }

    netview_enum(domain);
    printoutput(TRUE);
}

#endif
