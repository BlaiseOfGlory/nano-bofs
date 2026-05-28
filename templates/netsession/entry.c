#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <lm.h>

void NetSessions(wchar_t *hostname)
{
    LPSESSION_INFO_10 pBuf = NULL;
    LPSESSION_INFO_10 pTmpBuf = NULL;
    DWORD dwEntriesRead = 0;
    DWORD dwTotalEntries = 0;
    DWORD dwResumeHandle = 0;
    DWORD dwTotalCount = 0;
    NET_API_STATUS nStatus = 0;

    if (hostname != NULL)
    {
        internal_printf("Enumerating sessions for system: %ls\n", hostname);
    }
    else
    {
        internal_printf("Enumerating sessions for system: (Local)\n");
    }

    do
    {
        nStatus = NETAPI32$NetSessionEnum(
            hostname,
            NULL,
            NULL,
            10,
            (LPBYTE *)&pBuf,
            MAX_PREFERRED_LENGTH,
            &dwEntriesRead,
            &dwTotalEntries,
            &dwResumeHandle
        );

        if (nStatus == NERR_Success || nStatus == ERROR_MORE_DATA)
        {
            pTmpBuf = pBuf;
            for (DWORD i = 0; i < dwEntriesRead; i++)
            {
                if (pTmpBuf == NULL)
                {
                    internal_printf("Encountered a null session entry pointer.\n");
                    break;
                }

                internal_printf("\nClient: %ls\n", pTmpBuf->sesi10_cname);
                internal_printf("User:   %ls\n", pTmpBuf->sesi10_username);
                internal_printf("Active: %lu\n", pTmpBuf->sesi10_time);
                internal_printf("Idle:   %lu\n", pTmpBuf->sesi10_idle_time);
                internal_printf("--------------------\n");

                pTmpBuf++;
                dwTotalCount++;
            }
        }
        else
        {
            internal_printf("A system error has occurred: %lu\n", nStatus);
        }

        if (pBuf != NULL)
        {
            NETAPI32$NetApiBufferFree(pBuf);
            pBuf = NULL;
        }
    } while (nStatus == ERROR_MORE_DATA);

    internal_printf("\nTotal of %lu entries enumerated\n", dwTotalCount);
}


#ifdef BOF

VOID go(
    IN PCHAR Buffer,
    IN ULONG Length
)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_SERVER[] = L"__NANO_SERVER__";
    wchar_t *hostname = (wchar_t *)NANO_SERVER;

    if (*hostname == 0)
    {
        hostname = NULL;
    }
    if (!bofstart())
    {
        return;
    }

    NetSessions(hostname);
    printoutput(TRUE);
};

#endif
