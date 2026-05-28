#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"

DWORD query_service_description(const char *Hostname, LPCSTR cpServiceName)
{
    DWORD dwResult = ERROR_SUCCESS;
    SC_HANDLE scManager = NULL;
    SC_HANDLE scService = NULL;
    DWORD bytesneeded = 0;
    SERVICE_DESCRIPTIONA *desc = NULL;

    do
    {
        scManager = ADVAPI32$OpenSCManagerA(Hostname, SERVICES_ACTIVE_DATABASEA, SC_MANAGER_CONNECT | GENERIC_READ);
        if (scManager == NULL)
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        scService = ADVAPI32$OpenServiceA(scManager, cpServiceName, GENERIC_READ);
        if (scService == NULL)
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        ADVAPI32$QueryServiceConfig2A(scService, SERVICE_CONFIG_DESCRIPTION, NULL, 0, &bytesneeded);
        desc = intAlloc(bytesneeded);
        if (desc == NULL)
        {
            dwResult = ERROR_OUTOFMEMORY;
            break;
        }

        if (ADVAPI32$QueryServiceConfig2A(scService, SERVICE_CONFIG_DESCRIPTION, (LPBYTE)desc, bytesneeded, &bytesneeded) == 0)
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        internal_printf("%s", desc->lpDescription ? desc->lpDescription : "");
    } while (0);

    if (scService)
    {
        ADVAPI32$CloseServiceHandle(scService);
    }

    if (scManager)
    {
        ADVAPI32$CloseServiceHandle(scManager);
    }

    if (desc != NULL)
    {
        intFree(desc);
    }

    return dwResult;
}

#ifdef BOF
VOID go(
    IN PCHAR Buffer,
    IN ULONG Length
)
{
    (void)Buffer;
    (void)Length;

    static const char NANO_SERVER[] = "__NANO_SERVER__";
    static const char NANO_SERVICE_NAME[] = "__NANO_SERVICE_NAME__";
    char server_buffer[sizeof(NANO_SERVER)];
    char service_name_buffer[sizeof(NANO_SERVICE_NAME)];
    const char *hostname = server_buffer;
    const char *servicename = service_name_buffer;
    DWORD result = ERROR_SUCCESS;

    memcpy(server_buffer, NANO_SERVER, sizeof(NANO_SERVER));
    memcpy(service_name_buffer, NANO_SERVICE_NAME, sizeof(NANO_SERVICE_NAME));
    hostname = (*hostname == 0) ? NULL : hostname;

    if (!bofstart())
    {
        return;
    }

    result = query_service_description(hostname, servicename);
    if (result != ERROR_SUCCESS)
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to query service: %u", result);
    }
    printoutput(TRUE);
}
#endif
