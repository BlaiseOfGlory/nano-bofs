// https://docs.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuserenum
#include <windows.h>
#include <iphlpapi.h>
#include <lmaccess.h>
#include <lmerr.h>
#include "lm.h"
#include "bofdefs.h"
#include "base.c"

char *netuser_enum(int usedomain, int userfilter)
{
    LPVOID pBuf = NULL;
    LPUSER_INFO_1 pTmpBuf;
    DWORD dwLevel = 1;
    DWORD dwPrefMaxLen = MAX_PREFERRED_LENGTH;
    DWORD dwEntriesRead = 0;
    DWORD dwTotalEntries = 0;
    DWORD dwResumeHandle = 0;
    DWORD i;
    DWORD dwTotalCount = 0;
    NET_API_STATUS nStatus;
    LPTSTR pszServerName = NULL;

    if (usedomain == 1)
    {
        NETAPI32$NetGetAnyDCName(NULL, NULL, (LPBYTE *)&pszServerName);
    }
    dwLevel = (userfilter == 1) ? 0 : 1;
    do
    {
        nStatus = NETAPI32$NetUserEnum(
            (LPCWSTR)pszServerName,
            dwLevel,
            FILTER_NORMAL_ACCOUNT,
            (LPBYTE *)&pBuf,
            dwPrefMaxLen,
            &dwEntriesRead,
            &dwTotalEntries,
            &dwResumeHandle);
        if ((nStatus == NERR_Success) || (nStatus == ERROR_MORE_DATA))
        {
            if ((pTmpBuf = pBuf) != NULL)
            {
                for (i = 0; (i < dwEntriesRead); i++)
                {
                    if (pTmpBuf == NULL)
                    {
                        break;
                    }
                    if (userfilter == 1)
                    {
                        goto printu;
                    }
                    else if (userfilter == 2)
                    {
                        if (pTmpBuf->usri1_flags & UF_LOCKOUT)
                        {
                            goto printu;
                        }
                        else
                        {
                            goto nextu;
                        }
                    }
                    else if (userfilter == 3)
                    {
                        if (pTmpBuf->usri1_flags & UF_ACCOUNTDISABLE)
                        {
                            goto printu;
                        }
                        else
                        {
                            goto nextu;
                        }
                    }
                    else if (userfilter == 4)
                    {
                        if (!(pTmpBuf->usri1_flags & (UF_ACCOUNTDISABLE | UF_LOCKOUT)))
                        {
                            goto printu;
                        }
                        else
                        {
                            goto nextu;
                        }
                    }
                    else
                    {
                        break;
                    }
                printu:
                    internal_printf("-- %S\n", pTmpBuf->usri1_name);
                nextu:
                    if (dwLevel)
                    {
                        pTmpBuf++;
                    }
                    else
                    {
                        pTmpBuf = (LPUSER_INFO_1)((LPUSER_INFO_0)pTmpBuf + 1);
                    }

                    dwTotalCount++;
                }
            }
        }
        else
        {
            BeaconPrintf(CALLBACK_ERROR, "Failed to query for local users\n");
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
    if (pszServerName != NULL)
    {
        NETAPI32$NetApiBufferFree(pszServerName);
    }

    return NULL;
}

#ifdef BOF

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const int NANO_USEDOMAIN = __NANO_USEDOMAIN__;
    static const int NANO_USERFILTER = __NANO_USERFILTER__;

    if (!bofstart())
    {
        return;
    }
    netuser_enum(NANO_USEDOMAIN, NANO_USERFILTER);
    printoutput(TRUE);
}

#endif
