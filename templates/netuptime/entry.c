#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <lm.h>

void netuptime(wchar_t *servername)
{
    PSTAT_WORKSTATION_0 output = NULL;
    NET_API_STATUS stat = 0;
    wchar_t *service = L"LanmanWorkstation";
    FILETIME bootFileTime = {0};
    SYSTEMTIME bootSystemTime = {0};

    stat = NETAPI32$NetStatisticsGet(servername, service, 0, 0, (LPBYTE *)&output);
    if (stat == ERROR_SUCCESS)
    {
        bootFileTime.dwLowDateTime = output->StatisticsStartTime.LowPart;
        bootFileTime.dwHighDateTime = output->StatisticsStartTime.HighPart;
        KERNEL32$FileTimeToSystemTime(&bootFileTime, &bootSystemTime);

        internal_printf("ServerName:   %S\n", servername == NULL ? L"(Local)" : servername);
        internal_printf(
            "Boot time:    %4d-%.2d-%.2d %.2d:%.2d:%.2d\n",
            bootSystemTime.wYear,
            bootSystemTime.wMonth,
            bootSystemTime.wDay,
            bootSystemTime.wHour,
            bootSystemTime.wMinute,
            bootSystemTime.wSecond
        );
    }
    else
    {
        internal_printf("Unable to retrieve up time remotely: %lu\n", stat);
    }

    if (output != NULL)
    {
        NETAPI32$NetApiBufferFree(output);
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

    netuptime(servername);
    printoutput(TRUE);
};

#endif
