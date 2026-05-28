#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"
#include "anticrash.c"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-conversion"
char **EServiceStatus = 1;
char **EServiceStartup = 1;
char **EServiceError = 1;
const char *gServiceName = 1;
#pragma GCC diagnostic pop

void init_enums()
{
    EServiceStatus = antiStringResolve(7, "SPACER", "STOPPED", "START_PENDING", "STOP_PENDING", "RUNNING", "CONTINUE_PENDING", "PAUSE_PENDING");
    EServiceStartup = antiStringResolve(5, "BOOT_DRIVER", "SYSTEM_START_DRIVER", "AUTO_START", "DEMAND_START", "DISABLED");
    EServiceError = antiStringResolve(4, "IGNORE", "NORMAL", "SEVERE", "CRITICAL");
}

char *resolveType(DWORD T)
{
    if (T == 0x1)
    {
        return "KERNEL_DRIVER";
    }
    else if (T == 0x2)
    {
        return "FILE_DRIVER";
    }
    else if (T == 0x10 || T == 0x110)
    {
        return (T == 0x10) ? "WIN32_OWN" : "WIN32_OWN Interactive";
    }
    else if (T == 0x20 || T == 0x120)
    {
        return (T == 0x20) ? "WIN32_SHARED" : "WIN32_SHARED Interactive";
    }
    else if (T == 0x50 || T == 0xD0)
    {
        return (T == 0x50) ? "USER_OWN" : "USER_OWN Instance";
    }
    else if (T == 0x60 || T == 0xE0)
    {
        return (T == 0x60) ? "USER_SHARED" : "USER_SHARED Instance";
    }
    else
    {
        return "UNKNOWN";
    }
}

void cleanup_enums()
{
    intFree(EServiceStatus);
    intFree(EServiceStartup);
    intFree(EServiceError);
}

DWORD get_service_status(SC_HANDLE scService)
{
    DWORD dwResult = ERROR_SUCCESS;
    SERVICE_STATUS serviceStatus;

    do
    {
        if (!ADVAPI32$QueryServiceStatus(scService, &serviceStatus))
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        internal_printf("\t%-20s : %s\n", "CURRENT_STATUS", EServiceStatus[serviceStatus.dwCurrentState]);
    } while (0);

    return dwResult;
}

char *make_long_str(LPSTR serviceinfo)
{
    DWORD i = 0;
    if (!serviceinfo || serviceinfo[0] == 0)
    {
        return "";
    }
    else if (serviceinfo[0] == SC_GROUP_IDENTIFIERA)
    {
        return serviceinfo;
    }
    else
    {
        while (!(serviceinfo[i] == 0 && serviceinfo[i + 1] == 0))
        {
            if (serviceinfo[i] == 0)
            {
                serviceinfo[i] = ' ';
            }
            i++;
        }
        return serviceinfo;
    }
}

DWORD get_service_config(SC_HANDLE scService)
{
    DWORD dwResult = ERROR_SUCCESS;
    LPQUERY_SERVICE_CONFIGA lpServiceConfig = NULL;
    DWORD cbBytesNeeded = 0;

    do
    {
        ADVAPI32$QueryServiceConfigA(scService, NULL, 0, &cbBytesNeeded);
        dwResult = KERNEL32$GetLastError();

        if (dwResult != ERROR_INSUFFICIENT_BUFFER)
        {
            break;
        }

        lpServiceConfig = (LPQUERY_SERVICE_CONFIGA)intAlloc(cbBytesNeeded);
        if (lpServiceConfig == NULL)
        {
            break;
        }

        if (!ADVAPI32$QueryServiceConfigA(scService, lpServiceConfig, cbBytesNeeded, &cbBytesNeeded))
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        internal_printf(
            "SERVICE_NAME: %s\n"
            "\t%-20s : %lx %s\n"
            "\t%-20s : %lx %s\n"
            "\t%-20s : %lx %s\n"
            "\t%-20s : %s\n"
            "\t%-20s : %s\n"
            "\t%-20s : %ld\n"
            "\t%-20s : %s\n"
            "\t%-20s : %s%s\n"
            "\t%-20s : %s\n",
            gServiceName,
            "TYPE", lpServiceConfig->dwServiceType, resolveType(lpServiceConfig->dwServiceType),
            "START_TYPE", lpServiceConfig->dwStartType, EServiceStartup[lpServiceConfig->dwStartType],
            "ERROR_CONTROL", lpServiceConfig->dwErrorControl, EServiceError[lpServiceConfig->dwErrorControl],
            "BINARY_PATH_NAME", lpServiceConfig->lpBinaryPathName,
            "LOAD_ORDER_GROUP", lpServiceConfig->lpLoadOrderGroup ? lpServiceConfig->lpLoadOrderGroup : "",
            "TAG", lpServiceConfig->dwTagId,
            "DISPLAY_NAME", lpServiceConfig->lpDisplayName,
            "DEPENDENCIES", (lpServiceConfig->lpDependencies && lpServiceConfig->lpDependencies[0] == SC_GROUP_IDENTIFIERA) ? "(GROUP) " : "", make_long_str(lpServiceConfig->lpDependencies),
            "SERVICE_START_NAME", lpServiceConfig->lpServiceStartName
        );

        dwResult = ERROR_SUCCESS;
    } while (0);

    if (lpServiceConfig)
    {
        intFree(lpServiceConfig);
    }

    return dwResult;
}

DWORD query_config(const char *Hostname, LPCSTR cpServiceName)
{
    DWORD dwResult = ERROR_SUCCESS;
    SC_HANDLE scManager = NULL;
    SC_HANDLE scService = NULL;

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

        dwResult = get_service_config(scService);
        if (dwResult)
        {
            break;
        }
        dwResult = get_service_status(scService);
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
    const char *servicename = service_name_buffer;
    DWORD result = ERROR_SUCCESS;

    memcpy(server_buffer, NANO_SERVER, sizeof(NANO_SERVER));
    memcpy(service_name_buffer, NANO_SERVICE_NAME, sizeof(NANO_SERVICE_NAME));
    hostname = (*hostname == 0) ? NULL : hostname;
    gServiceName = servicename;

    init_enums();
    if (!bofstart())
    {
        cleanup_enums();
        return;
    }

    result = query_config(hostname, servicename);
    if (result != S_OK)
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to query service: %u", result);
    }
    printoutput(TRUE);
    cleanup_enums();
}
#endif
