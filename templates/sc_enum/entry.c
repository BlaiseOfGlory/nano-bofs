#include <windows.h>
#include "bofdefs.h"
#include "base.c"

#ifndef SERVICE_CONFIG_TRIGGER_INFO
#define SERVICE_CONFIG_TRIGGER_INFO 8
#endif

#ifndef SERVICE_TRIGGER_ACTION_SERVICE_START
#define SERVICE_TRIGGER_ACTION_SERVICE_START 1
#endif

#ifndef SERVICE_TRIGGER_ACTION_SERVICE_STOP
#define SERVICE_TRIGGER_ACTION_SERVICE_STOP 2
#endif

#ifdef __MINGW32__
typedef struct _SERVICE_TRIGGER_SPECIFIC_DATA_ITEM {
    DWORD dwDataType;
    DWORD cbData;
    PBYTE pData;
} SERVICE_TRIGGER_SPECIFIC_DATA_ITEM, *PSERVICE_TRIGGER_SPECIFIC_DATA_ITEM;

typedef struct _SERVICE_TRIGGER {
    DWORD dwTriggerType;
    DWORD dwAction;
    GUID *pTriggerSubtype;
    DWORD cDataItems;
    PSERVICE_TRIGGER_SPECIFIC_DATA_ITEM pDataItems;
} SERVICE_TRIGGER, *PSERVICE_TRIGGER;

typedef struct _SERVICE_TRIGGER_INFO {
    DWORD cTriggers;
    PSERVICE_TRIGGER pTriggers;
    PBYTE pReserved;
} SERVICE_TRIGGER_INFO, *PSERVICE_TRIGGER_INFO;
#endif

static const char *safe_str(LPCSTR value)
{
    return value ? value : "";
}

static char *make_long_str(LPSTR serviceinfo, const char *buffer_end)
{
    DWORD i = 0;

    if (serviceinfo == NULL || serviceinfo[0] == 0)
    {
        return "";
    }
    if (serviceinfo[0] == SC_GROUP_IDENTIFIERA)
    {
        return serviceinfo;
    }

    while ((serviceinfo + i + 1) < buffer_end &&
           !(serviceinfo[i] == 0 && serviceinfo[i + 1] == 0))
    {
        if (serviceinfo[i] == 0)
        {
            serviceinfo[i] = ' ';
        }
        i++;
    }

    return serviceinfo;
}

static const char *resolve_type(DWORD service_type)
{
    if (service_type == 0x1)
    {
        return "KERNEL_DRIVER";
    }
    if (service_type == 0x2)
    {
        return "FILE_DRIVER";
    }
    if (service_type == 0x10 || service_type == 0x110)
    {
        return service_type == 0x10 ? "WIN32_OWN" : "WIN32_OWN Interactive";
    }
    if (service_type == 0x20 || service_type == 0x120)
    {
        return service_type == 0x20 ? "WIN32_SHARED" : "WIN32_SHARED Interactive";
    }
    if (service_type == 0x50 || service_type == 0xD0)
    {
        return service_type == 0x50 ? "USER_OWN" : "USER_OWN Instance";
    }
    if (service_type == 0x60 || service_type == 0xE0)
    {
        return service_type == 0x60 ? "USER_SHARED" : "USER_SHARED Instance";
    }
    return "UNKNOWN";
}

static const char *service_status_string(DWORD status)
{
    switch (status)
    {
    case SERVICE_STOPPED:
        return "STOPPED";
    case SERVICE_START_PENDING:
        return "START_PENDING";
    case SERVICE_STOP_PENDING:
        return "STOP_PENDING";
    case SERVICE_RUNNING:
        return "RUNNING";
    case SERVICE_CONTINUE_PENDING:
        return "CONTINUE_PENDING";
    case SERVICE_PAUSE_PENDING:
        return "PAUSE_PENDING";
    case SERVICE_PAUSED:
        return "PAUSED";
    default:
        return "UNKNOWN";
    }
}

static const char *startup_type_string(DWORD start_type)
{
    switch (start_type)
    {
    case SERVICE_BOOT_START:
        return "BOOT_DRIVER";
    case SERVICE_SYSTEM_START:
        return "SYSTEM_START_DRIVER";
    case SERVICE_AUTO_START:
        return "AUTO_START";
    case SERVICE_DEMAND_START:
        return "DEMAND_START";
    case SERVICE_DISABLED:
        return "DISABLED";
    default:
        return "UNKNOWN";
    }
}

static const char *error_control_string(DWORD error_control)
{
    switch (error_control)
    {
    case SERVICE_ERROR_IGNORE:
        return "IGNORE";
    case SERVICE_ERROR_NORMAL:
        return "NORMAL";
    case SERVICE_ERROR_SEVERE:
        return "SEVERE";
    case SERVICE_ERROR_CRITICAL:
        return "CRITICAL";
    default:
        return "UNKNOWN";
    }
}

static const char *failure_action_string(DWORD action)
{
    switch (action)
    {
    case SC_ACTION_NONE:
        return "NONE";
    case SC_ACTION_RESTART:
        return "RESTART";
    case SC_ACTION_REBOOT:
        return "REBOOT";
    case SC_ACTION_RUN_COMMAND:
        return "COMMAND";
    default:
        return "(FAILED TO RESOLVE)";
    }
}

static const char *trigger_action_string(DWORD action)
{
    switch (action)
    {
    case SERVICE_TRIGGER_ACTION_SERVICE_START:
        return "START_SERVICE";
    case SERVICE_TRIGGER_ACTION_SERVICE_STOP:
        return "STOP_SERVICE";
    default:
        return "(FAILED TO RESOLVE)";
    }
}

static const char *trigger_type_string(DWORD trigger_type)
{
    switch (trigger_type)
    {
    case 1:
        return "DEVICE_ARRIVAL";
    case 2:
        return "IP_UP_DOWN";
    case 3:
        return "DOMAIN_JOIN_LEAVE";
    case 4:
        return "FIREWALL_PORT_EVENT";
    case 5:
        return "GROUP_POLICY_UPDATE";
    case 6:
        return "NETWORK_ENDPOINT";
    case 20:
        return "CUSTOM";
    default:
        return "(FAILED TO RESOLVE)";
    }
}

static DWORD get_service_config(SC_HANDLE service)
{
    DWORD result = ERROR_SUCCESS;
    DWORD bytes_needed = 0;
    LPQUERY_SERVICE_CONFIGA config = NULL;
    const char *buffer_end = NULL;

    ADVAPI32$QueryServiceConfigA(service, NULL, 0, &bytes_needed);
    result = KERNEL32$GetLastError();
    if (result != ERROR_INSUFFICIENT_BUFFER)
    {
        return result;
    }

    config = (LPQUERY_SERVICE_CONFIGA)intAlloc(bytes_needed);
    if (config == NULL)
    {
        return ERROR_NOT_ENOUGH_MEMORY;
    }

    if (!ADVAPI32$QueryServiceConfigA(service, config, bytes_needed, &bytes_needed))
    {
        result = KERNEL32$GetLastError();
        intFree(config);
        return result;
    }

    buffer_end = ((const char *)config) + bytes_needed;

    internal_printf(
        "\t%-30s : %lx %s\n"
        "\t%-30s : %lx %s\n"
        "\t%-30s : %lx %s\n"
        "\t%-30s : %s\n"
        "\t%-30s : %s\n"
        "\t%-30s : %ld\n"
        "\t%-30s : %s\n"
        "\t%-30s : %s%s\n"
        "\t%-30s : %s\n",
        "TYPE", config->dwServiceType, resolve_type(config->dwServiceType),
        "START_TYPE", config->dwStartType, startup_type_string(config->dwStartType),
        "ERROR_CONTROL", config->dwErrorControl, error_control_string(config->dwErrorControl),
        "BINARY_PATH_NAME", safe_str(config->lpBinaryPathName),
        "LOAD_ORDER_GROUP", safe_str(config->lpLoadOrderGroup),
        "TAG", config->dwTagId,
        "DISPLAY_NAME", safe_str(config->lpDisplayName),
        "DEPENDENCIES",
        (config->lpDependencies && config->lpDependencies[0] == SC_GROUP_IDENTIFIERA) ? "(GROUP) " : "",
        make_long_str(config->lpDependencies, buffer_end),
        "SERVICE_START_NAME", safe_str(config->lpServiceStartName)
    );

    intFree(config);
    return ERROR_SUCCESS;
}

static DWORD get_service_failure(SC_HANDLE service)
{
    DWORD result = ERROR_SUCCESS;
    DWORD bytes_needed = 0;
    LPSERVICE_FAILURE_ACTIONSA config = NULL;

    ADVAPI32$QueryServiceConfig2A(service, SERVICE_CONFIG_FAILURE_ACTIONS, NULL, 0, &bytes_needed);
    result = KERNEL32$GetLastError();
    if (result != ERROR_INSUFFICIENT_BUFFER)
    {
        return result;
    }

    config = (LPSERVICE_FAILURE_ACTIONSA)intAlloc(bytes_needed);
    if (config == NULL)
    {
        return ERROR_NOT_ENOUGH_MEMORY;
    }

    if (!ADVAPI32$QueryServiceConfig2A(service, SERVICE_CONFIG_FAILURE_ACTIONS, (LPBYTE)config, bytes_needed, &bytes_needed))
    {
        result = KERNEL32$GetLastError();
        intFree(config);
        return result;
    }

    internal_printf(
        "\t%-30s : %lu\n"
        "\t%-30s : %s\n"
        "\t%-30s : %s\n",
        "RESET_PERIOD (in seconds)", config->dwResetPeriod,
        "REBOOT_MESSAGE", safe_str(config->lpRebootMsg),
        "COMMAND_LINE", safe_str(config->lpCommand)
    );

    if (config->cActions > 0 && config->lpsaActions == NULL)
    {
        intFree(config);
        return ERROR_INVALID_DATA;
    }

    for (DWORD i = 0; i < config->cActions; i++)
    {
        internal_printf(
            "\t%-30s : %s -- Delay = %lu milliseconds\n",
            "FAILURE_ACTIONS",
            failure_action_string(config->lpsaActions[i].Type),
            config->lpsaActions[i].Delay
        );
    }

    intFree(config);
    return ERROR_SUCCESS;
}

static DWORD get_service_triggers(SC_HANDLE service)
{
    DWORD result = ERROR_SUCCESS;
    DWORD bytes_needed = 0;
    PSERVICE_TRIGGER_INFO config = NULL;
    RPC_CSTR guid = NULL;

    ADVAPI32$QueryServiceConfig2A(service, SERVICE_CONFIG_TRIGGER_INFO, NULL, 0, &bytes_needed);
    result = KERNEL32$GetLastError();
    if (result != ERROR_INSUFFICIENT_BUFFER)
    {
        return result;
    }

    config = (PSERVICE_TRIGGER_INFO)intAlloc(bytes_needed);
    if (config == NULL)
    {
        return ERROR_NOT_ENOUGH_MEMORY;
    }

    if (!ADVAPI32$QueryServiceConfig2A(service, SERVICE_CONFIG_TRIGGER_INFO, (LPBYTE)config, bytes_needed, &bytes_needed))
    {
        result = KERNEL32$GetLastError();
        intFree(config);
        return result;
    }

    if (config->cTriggers == 0)
    {
        internal_printf("The service has not registered for any start or stop triggers.\n");
        intFree(config);
        return ERROR_SUCCESS;
    }

    if (config->pTriggers == NULL)
    {
        intFree(config);
        return ERROR_INVALID_DATA;
    }

    for (DWORD i = 0; i < config->cTriggers; i++)
    {
        if (config->pTriggers[i].pTriggerSubtype != NULL &&
            RPCRT4$UuidToStringA(config->pTriggers[i].pTriggerSubtype, &guid) != RPC_S_OK)
        {
            guid = NULL;
        }

        internal_printf("\t%s\n", trigger_action_string(config->pTriggers[i].dwAction));
        internal_printf(
            "\t  %-20s : %s\n",
            trigger_type_string(config->pTriggers[i].dwTriggerType),
            guid ? (char *)guid : "(FAILED)"
        );

        if (guid != NULL)
        {
            RPCRT4$RpcStringFreeA(&guid);
            guid = NULL;
        }

        if ((config->pTriggers[i].dwTriggerType == 20 ||
             config->pTriggers[i].dwTriggerType == 1 ||
             config->pTriggers[i].dwTriggerType == 4 ||
             config->pTriggers[i].dwTriggerType == 6) &&
            config->pTriggers[i].cDataItems > 0)
        {
            internal_printf("Has trigger specific data items but currently this is unsupported\n");
        }

        internal_printf("\n");
    }

    intFree(config);
    return ERROR_SUCCESS;
}

static void query_service(SC_HANDLE manager, LPCSTR service_name)
{
    DWORD result = ERROR_SUCCESS;
    SC_HANDLE service = ADVAPI32$OpenServiceA(manager, service_name, GENERIC_READ);

    if (service == NULL)
    {
        result = KERNEL32$GetLastError();
        internal_printf("Unable to query any additional service information: %lu\n", result);
        return;
    }

    result = get_service_config(service);
    if (result != ERROR_SUCCESS)
    {
        internal_printf("\tUnable to query base configuration: %lu\n", result);
    }

    result = get_service_failure(service);
    if (result != ERROR_SUCCESS)
    {
        internal_printf("\tUnable to query failure configuration: %lu\n", result);
    }

    result = get_service_triggers(service);
    if (result != ERROR_SUCCESS)
    {
        internal_printf("\tUnable to query trigger configuration: %lu\n", result);
    }

    internal_printf("\n");
    ADVAPI32$CloseServiceHandle(service);
}

static DWORD enumerate_services(SC_HANDLE manager)
{
    DWORD result = ERROR_SUCCESS;
    DWORD bytes_needed = 0;
    DWORD services_returned = 0;
    DWORD resume_handle = 0;
    DWORD service_index = 0;
    DWORD last_error = ERROR_SUCCESS;
    ENUM_SERVICE_STATUS_PROCESSA *services = NULL;

    if (ADVAPI32$EnumServicesStatusExA(
            manager,
            SC_ENUM_PROCESS_INFO,
            SERVICE_WIN32,
            SERVICE_STATE_ALL,
            NULL,
            0,
            &bytes_needed,
            &services_returned,
            &resume_handle,
            NULL))
    {
        return ERROR_SUCCESS;
    }

    last_error = KERNEL32$GetLastError();
    if (last_error != ERROR_MORE_DATA || bytes_needed == 0)
    {
        return last_error;
    }

    services = (ENUM_SERVICE_STATUS_PROCESSA *)intAlloc(bytes_needed);
    if (services == NULL)
    {
        return ERROR_NOT_ENOUGH_MEMORY;
    }

    if (!ADVAPI32$EnumServicesStatusExA(
            manager,
            SC_ENUM_PROCESS_INFO,
            SERVICE_WIN32,
            SERVICE_STATE_ALL,
            (LPBYTE)services,
            bytes_needed,
            &bytes_needed,
            &services_returned,
            &resume_handle,
            NULL))
    {
        result = KERNEL32$GetLastError();
        intFree(services);
        return result;
    }

    for (service_index = 0; service_index < services_returned; service_index++)
    {
        internal_printf(
            "SERVICE_NAME: %s\n"
            "DISPLAY_NAME: %s\n"
            "\t%-30s : %ld %s\n"
            "\t%-30s : %ld %s\n"
            "\t%-30s : %ld\n"
            "\t%-30s : %ld\n"
            "\t%-30s : %ld\n"
            "\t%-30s : %ld\n"
            "\t%-30s : %ld\n"
            "\t%-30s : %ld\n",
            services[service_index].lpServiceName,
            safe_str(services[service_index].lpDisplayName),
            "TYPE", services[service_index].ServiceStatusProcess.dwServiceType, resolve_type(services[service_index].ServiceStatusProcess.dwServiceType),
            "STATE", services[service_index].ServiceStatusProcess.dwCurrentState, service_status_string(services[service_index].ServiceStatusProcess.dwCurrentState),
            "WIN32_EXIT_CODE", services[service_index].ServiceStatusProcess.dwWin32ExitCode,
            "SERVICE_EXIT_CODE", services[service_index].ServiceStatusProcess.dwServiceSpecificExitCode,
            "CHECKPOINT", services[service_index].ServiceStatusProcess.dwCheckPoint,
            "WAIT_HINT", services[service_index].ServiceStatusProcess.dwWaitHint,
            "PID", services[service_index].ServiceStatusProcess.dwProcessId,
            "FLAGS", services[service_index].ServiceStatusProcess.dwServiceFlags
        );

        query_service(manager, services[service_index].lpServiceName);
    }

    intFree(services);
    return ERROR_SUCCESS;
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
    const char *server = NANO_SERVER;
    DWORD result = ERROR_SUCCESS;
    SC_HANDLE manager = NULL;

    if (*server == 0)
    {
        server = NULL;
    }
    if (!bofstart())
    {
        return;
    }

    manager = ADVAPI32$OpenSCManagerA(server, SERVICES_ACTIVE_DATABASEA, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE | GENERIC_READ);
    if (manager == NULL)
    {
        result = KERNEL32$GetLastError();
        BeaconPrintf(CALLBACK_ERROR, "Failed to connect to service manager: %lu", result);
        printoutput(TRUE);
        return;
    }

    result = enumerate_services(manager);
    if (result != ERROR_SUCCESS)
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to query service: %lu", result);
    }

    ADVAPI32$CloseServiceHandle(manager);
    printoutput(TRUE);
};

#endif
