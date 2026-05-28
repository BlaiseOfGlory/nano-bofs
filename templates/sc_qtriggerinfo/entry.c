#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"
#include "anticrash.c"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-conversion"
char **ETriggerType = 1;
char **Estartstop = 1;
const char *gServiceName = 1;
#pragma GCC diagnostic pop

#ifndef SERVICE_CONFIG_TRIGGER_INFO
#define SERVICE_CONFIG_TRIGGER_INFO 8
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

void init_enums(void)
{
    ETriggerType = antiStringResolve(
        21,
        "",
        "DEVICE_ARRIVAL",
        "IP_UP_DOWN",
        "DOMAIN_JOIN_LEAVE",
        "FIREWALL_PORT_EVENT",
        "GROUP_POLICY_UPDATE",
        "NETWORK_ENDPOINT",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "CUSTOM"
    );
    Estartstop = antiStringResolve(3, "", "START_SERVICE", "STOP_SERVICE");
}

void cleanup_enums(void)
{
    intFree(ETriggerType);
    intFree(Estartstop);
}

DWORD get_service_triggers(SC_HANDLE scService)
{
    DWORD dwResult = ERROR_SUCCESS;
    PSERVICE_TRIGGER_INFO lpServiceConfig = NULL;
    DWORD cbBytesNeeded = 0;

    do
    {
        ADVAPI32$QueryServiceConfig2A(scService, SERVICE_CONFIG_TRIGGER_INFO, NULL, 0, &cbBytesNeeded);
        dwResult = KERNEL32$GetLastError();
        if (dwResult != ERROR_INSUFFICIENT_BUFFER)
        {
            break;
        }

        lpServiceConfig = (PSERVICE_TRIGGER_INFO)intAlloc(cbBytesNeeded);
        if (lpServiceConfig == NULL)
        {
            dwResult = ERROR_OUTOFMEMORY;
            break;
        }

        if (!ADVAPI32$QueryServiceConfig2A(scService, SERVICE_CONFIG_TRIGGER_INFO, (LPBYTE)lpServiceConfig, cbBytesNeeded, &cbBytesNeeded))
        {
            dwResult = KERNEL32$GetLastError();
            break;
        }

        if (lpServiceConfig->cTriggers == 0)
        {
            internal_printf("The service %s has not registered for any start or stop triggers.\n", gServiceName);
            dwResult = ERROR_SUCCESS;
            break;
        }

        internal_printf("SERVICE_NAME: %s\n\n", gServiceName);

        for (DWORD x = 0; x < lpServiceConfig->cTriggers; x++)
        {
            RPC_CSTR guid = NULL;
            RPCRT4$UuidToStringA(lpServiceConfig->pTriggers[x].pTriggerSubtype, &guid);
            internal_printf(
                "\t%s\n",
                (lpServiceConfig->pTriggers[x].dwAction > 0 && lpServiceConfig->pTriggers[x].dwAction < 3)
                    ? Estartstop[lpServiceConfig->pTriggers[x].dwAction]
                    : "(FAILED TO RESOLVE)"
            );
            internal_printf(
                "\t  %-20s : %s\n",
                (lpServiceConfig->pTriggers[x].dwTriggerType < 21 && lpServiceConfig->pTriggers[x].dwTriggerType > 0)
                    ? ETriggerType[lpServiceConfig->pTriggers[x].dwTriggerType]
                    : "(FAILED TO RESOLVE)",
                guid ? (char *)guid : "(FAILED)"
            );
            if (guid)
            {
                RPCRT4$RpcStringFreeA(&guid);
            }
            if ((lpServiceConfig->pTriggers[x].dwTriggerType == 20 ||
                 lpServiceConfig->pTriggers[x].dwTriggerType == 1 ||
                 lpServiceConfig->pTriggers[x].dwTriggerType == 4 ||
                 lpServiceConfig->pTriggers[x].dwTriggerType == 6) &&
                lpServiceConfig->pTriggers[x].cDataItems)
            {
                internal_printf("Has trigger specific data items but currently this is unsupported\n");
            }
            internal_printf("\n");
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

        dwResult = get_service_triggers(scService);
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

    init_enums();
    if (!bofstart())
    {
        cleanup_enums();
        return;
    }

    result = query_config(hostname, service_name);
    if (result != ERROR_SUCCESS)
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to query service: %u", result);
    }
    printoutput(TRUE);
    cleanup_enums();
}
#endif
