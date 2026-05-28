#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <lm.h>
#include <time.h>

void nettime(LPCWSTR pszServer)
{
    TIME_OF_DAY_INFO *pTod = NULL;
    NET_API_STATUS nStatus = NETAPI32$NetRemoteTOD(pszServer, (LPBYTE *)&pTod);

    if (pszServer == NULL)
    {
        pszServer = L"localhost";
    }

    if (nStatus == NERR_Success)
    {
        time_t elapsed = pTod->tod_elapsedt;
        char date[80];
        struct tm *ptm = NULL;

        elapsed -= pTod->tod_timezone * 60;
        ptm = MSVCRT$gmtime(&elapsed);
        if (ptm != NULL)
        {
            MSVCRT$strftime(date, sizeof(date), "%m/%d/%Y %I:%M:%S %p", ptm);
            internal_printf("Remote host: %ls\n", pszServer);
            internal_printf("Local time (GMT%+03d:00) is %s\n", -pTod->tod_timezone / 60, date);
        }
        else
        {
            internal_printf("Unable to convert remote time information.\n");
        }
    }
    else
    {
        internal_printf("Unable to retrieve remote time: %lu\n", nStatus);
    }

    if (pTod != NULL)
    {
        NETAPI32$NetApiBufferFree(pTod);
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

    static const wchar_t NANO_SERVER[] = L"__NANO_SERVER__";
    wchar_t *servername = (wchar_t *)NANO_SERVER;

    if (*servername == 0)
    {
        servername = NULL;
    }
    if (!bofstart())
    {
        return;
    }

    nettime(servername);
    printoutput(TRUE);
};

#endif
