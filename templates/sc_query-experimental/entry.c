#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"
#include "anticrash.c"

WINADVAPI WINBOOL WINAPI ADVAPI32$EnumServicesStatusA(
    SC_HANDLE hSCManager,
    DWORD dwServiceType,
    DWORD dwServiceState,
    LPENUM_SERVICE_STATUSA lpServices,
    DWORD cbBufSize,
    LPDWORD pcbBytesNeeded,
    LPDWORD lpServicesReturned,
    LPDWORD lpResumeHandle
);

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-conversion"
char **EServiceStatus = 1;
const char *gServiceName = 1;
#pragma GCC diagnostic pop

void init_enums()
{
    EServiceStatus = antiStringResolve(8, "SPACER", "STOPPED", "START_PENDING", "STOP_PENDING", "RUNNING", "CONTINUE_PENDING", "PAUSE_PENDING", "PAUSED");
}

char *resolveType(DWORD service_type)
{
    if (service_type == 0x1)
    {
        return "KERNEL_DRIVER";
    }
    else if (service_type == 0x2)
    {
        return "FILE_DRIVER";
    }
    else if (service_type == 0x10 || service_type == 0x110)
    {
        return (service_type == 0x10) ? "WIN32_OWN" : "WIN32_OWN Interactive";
    }
    else if (service_type == 0x20 || service_type == 0x120)
    {
        return (service_type == 0x20) ? "WIN32_SHARED" : "WIN32_SHARED Interactive";
    }
    else if (service_type == 0x50 || service_type == 0xD0)
    {
        return (service_type == 0x50) ? "USER_OWN" : "USER_OWN Instance";
    }
    else if (service_type == 0x60 || service_type == 0xE0)
    {
        return (service_type == 0x60) ? "USER_SHARED" : "USER_SHARED Instance";
    }
    else
    {
        return "UNKNOWN";
    }
}

void cleanup_enums()
{
    intFree(EServiceStatus);
}

DWORD query_service(const char *hostname, LPCSTR service_name);

DWORD get_service_status(SC_HANDLE scService)
{
    DWORD dwResult = ERROR_SUCCESS;
    SERVICE_STATUS service_status;

    do
    {
        if (!ADVAPI32$QueryServiceStatus(scService, &service_status))
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        internal_printf(
            "SERVICE_NAME: %s\n"
            "\t%-20s : %d %s\n"
            "\t%-20s : %d %s\n"
            "\t%-20s : %d\n"
            "\t%-20s : %d\n"
            "\t%-20s : %d\n"
            "\t%-20s : %d\n",
            gServiceName,
            "TYPE", service_status.dwServiceType, resolveType(service_status.dwServiceType),
            "STATE", service_status.dwCurrentState, EServiceStatus[service_status.dwCurrentState],
            "WIN32_EXIT_CODE", service_status.dwWin32ExitCode,
            "SERVICE_EXIT_CODE", service_status.dwServiceSpecificExitCode,
            "CHECKPOINT", service_status.dwCheckPoint,
            "WAIT_HINT", service_status.dwWaitHint
        );
    } while (0);

    return dwResult;
}

DWORD enumerate_services(const char *hostname)
{
    DWORD dwResult = ERROR_SUCCESS;
    SC_HANDLE scManager = NULL;
    ENUM_SERVICE_STATUSA *service_info = NULL;
    DWORD bytes_needed = 0;
    DWORD services_returned = 0;
    DWORD resume_handle = 0;
    DWORD service_index = 0;
    BOOL query_result = FALSE;

    do
    {
        scManager = ADVAPI32$OpenSCManagerA(hostname, SERVICES_ACTIVE_DATABASEA, SC_MANAGER_CONNECT | GENERIC_READ);
        if (scManager == NULL)
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        query_result = ADVAPI32$EnumServicesStatusA(
            scManager,
            SERVICE_WIN32,
            SERVICE_STATE_ALL,
            NULL,
            0,
            &bytes_needed,
            &services_returned,
            &resume_handle
        );

        if (!query_result && bytes_needed)
        {
            service_info = (ENUM_SERVICE_STATUSA *)intAlloc(bytes_needed);
            if (service_info == NULL)
            {
                break;
            }

            query_result = ADVAPI32$EnumServicesStatusA(
                scManager,
                SERVICE_WIN32,
                SERVICE_STATE_ALL,
                service_info,
                bytes_needed,
                &bytes_needed,
                &services_returned,
                &resume_handle
            );
            if (!query_result)
            {
                dwResult = KERNEL32$GetLastError();
                break;
            }
        }
        else
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        for (service_index = 0; service_index < services_returned; ++service_index)
        {
            internal_printf("DISPLAY_NAME: %s\n", service_info[service_index].lpDisplayName);
            gServiceName = service_info[service_index].lpServiceName;
            query_service(hostname, service_info[service_index].lpServiceName);
            internal_printf("\n");
        }
    } while (0);

    if (service_info)
    {
        intFree(service_info);
    }

    if (scManager)
    {
        ADVAPI32$CloseServiceHandle(scManager);
    }

    return dwResult;
}

DWORD query_service(const char *hostname, LPCSTR service_name)
{
    DWORD dwResult = ERROR_SUCCESS;
    SC_HANDLE scManager = NULL;
    SC_HANDLE scService = NULL;
    DWORD bytes_needed = 0;

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

        ADVAPI32$QueryServiceConfigA(scService, NULL, 0, &bytes_needed);
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
    const char *hostname = NULL;
    const char *service_name = NULL;
    DWORD result = ERROR_SUCCESS;

    memcpy(server_buffer, NANO_SERVER, sizeof(NANO_SERVER));
    memcpy(service_name_buffer, NANO_SERVICE_NAME, sizeof(NANO_SERVICE_NAME));
    hostname = (*server_buffer == 0) ? NULL : server_buffer;
    service_name = (*service_name_buffer == 0) ? NULL : service_name_buffer;
    gServiceName = service_name;

    init_enums();
    if (!bofstart())
    {
        cleanup_enums();
        return;
    }

    if (service_name == NULL)
    {
        result = enumerate_services(hostname);
    }
    else
    {
        result = query_service(hostname, service_name);
    }

    if (result != S_OK)
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to query service: %u", result);
    }
    printoutput(TRUE);
    cleanup_enums();
}
#endif
