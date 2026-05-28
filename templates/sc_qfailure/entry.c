#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"
#include "anticrash.c"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-conversion"
const char *gServiceName = 1;
#pragma GCC diagnostic pop

char *resolveAction(DWORD a)
{
    if (a == 0)
    {
        return "NONE";
    }
    else if (a == 1)
    {
        return "RESTART";
    }
    else if (a == 2)
    {
        return "REBOOT";
    }
    else if (a == 3)
    {
        return "COMMAND";
    }
    return "(FAILED TO RESOLVE)";
}

DWORD get_service_failure(SC_HANDLE scService)
{
    DWORD dwResult = ERROR_SUCCESS;
    LPSERVICE_FAILURE_ACTIONSA lpServiceConfig = NULL;
    DWORD cbBytesNeeded = 0;

    do
    {
        ADVAPI32$QueryServiceConfig2A(scService, SERVICE_CONFIG_FAILURE_ACTIONS, NULL, 0, &cbBytesNeeded);
        dwResult = KERNEL32$GetLastError();
        if (dwResult != ERROR_INSUFFICIENT_BUFFER)
        {
            break;
        }

        lpServiceConfig = (LPSERVICE_FAILURE_ACTIONSA)intAlloc(cbBytesNeeded);
        if (lpServiceConfig == NULL)
        {
            dwResult = ERROR_OUTOFMEMORY;
            break;
        }

        if (!ADVAPI32$QueryServiceConfig2A(scService, SERVICE_CONFIG_FAILURE_ACTIONS, (LPBYTE)lpServiceConfig, cbBytesNeeded, &cbBytesNeeded))
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        internal_printf(
            "SERVICE_NAME: %s\n"
            "\t%-30s : %lu\n"
            "\t%-30s : %s\n"
            "\t%-30s : %s\n",
            gServiceName,
            "RESET_PERIOD (in seconds)", lpServiceConfig->dwResetPeriod,
            "REBOOT_MESSAGE", lpServiceConfig->lpRebootMsg ? lpServiceConfig->lpRebootMsg : "",
            "COMMAND_LINE", lpServiceConfig->lpCommand ? lpServiceConfig->lpCommand : ""
        );
        for (DWORD x = 0; x < lpServiceConfig->cActions; x++)
        {
            internal_printf(
                "\t%-30s : %s -- Delay = %lu milliseconds\n",
                "FAILURE_ACTIONS",
                resolveAction(lpServiceConfig->lpsaActions[x].Type),
                lpServiceConfig->lpsaActions[x].Delay
            );
        }
        dwResult = ERROR_SUCCESS;
    } while (0);

    if (lpServiceConfig)
    {
        intFree(lpServiceConfig);
    }

    return dwResult;
}

DWORD query_config(const char *hostname, LPCSTR service_name)
{
    DWORD dwResult = ERROR_SUCCESS;
    SC_HANDLE scManager = NULL;
    SC_HANDLE scService = NULL;

    do
    {
        scManager = ADVAPI32$OpenSCManagerA(hostname, SERVICES_ACTIVE_DATABASEA, SC_MANAGER_CONNECT | GENERIC_READ);
        if (scManager == NULL)
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        scService = ADVAPI32$OpenServiceA(scManager, service_name, GENERIC_READ);
        if (scService == NULL)
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        dwResult = get_service_failure(scService);
    } while (0);

    if (scService)
    {
        ADVAPI32$CloseServiceHandle(scService);
    }

    if (scManager)
    {
        ADVAPI32$CloseServiceHandle(scManager);
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
    const char *service_name = service_name_buffer;
    DWORD result = ERROR_SUCCESS;

    memcpy(server_buffer, NANO_SERVER, sizeof(NANO_SERVER));
    memcpy(service_name_buffer, NANO_SERVICE_NAME, sizeof(NANO_SERVICE_NAME));
    hostname = (*hostname == 0) ? NULL : hostname;
    gServiceName = service_name;

    if (!bofstart())
    {
        return;
    }

    result = query_config(hostname, service_name);
    if (result != ERROR_SUCCESS)
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to query service: %u", result);
    }
    printoutput(TRUE);
}
#endif
