#include <windows.h>
#include <process.h>
#include "bofdefs.h"
#include "base.c"

#define SZ_SERVICE_KEY "SYSTEM\\CurrentControlSet\\Services"
#define SZ_INSTANCE_KEY "Instances"
#define SZ_ALTITUDE_VALUE "Altitude"


static void print_filter_type(const char *service_name, DWORD altitude)
{
    if ((altitude >= 360000) && (altitude <= 389999))
    {
        internal_printf("activitymonitor,%s,%lu\n", service_name, altitude);
    }
    else if ((altitude >= 320000) && (altitude <= 329999))
    {
        internal_printf("antivirus,%s,%lu\n", service_name, altitude);
    }
    else if ((altitude >= 260000) && (altitude <= 269999))
    {
        internal_printf("contentscreener,%s,%lu\n", service_name, altitude);
    }
}


DWORD Enum_Filter_Driver(LPCSTR computer)
{
    DWORD error_code = ERROR_SUCCESS;
    HKEY remote_root = NULL;
    HKEY services_root = NULL;
    HKEY service_key = NULL;
    HKEY instances_key = NULL;
    HKEY instance_subkey = NULL;
    LPSTR service_name = NULL;
    LPSTR instance_name = NULL;
    LPSTR altitude_value = NULL;
    DWORD service_name_capacity = MAX_PATH;
    DWORD service_index = 0;
    DWORD instance_name_capacity = MAX_PATH;
    DWORD instance_index = 0;
    DWORD altitude_value_type = 0;
    DWORD altitude_value_capacity = MAX_PATH;

    service_name = (LPSTR)intAlloc(MAX_PATH);
    if (service_name == NULL)
    {
        error_code = ERROR_OUTOFMEMORY;
        goto END;
    }
    intZeroMemory(service_name, MAX_PATH);

    instance_name = (LPSTR)intAlloc(MAX_PATH);
    if (instance_name == NULL)
    {
        error_code = ERROR_OUTOFMEMORY;
        goto END;
    }
    intZeroMemory(instance_name, MAX_PATH);

    altitude_value = (LPSTR)intAlloc(MAX_PATH);
    if (altitude_value == NULL)
    {
        error_code = ERROR_OUTOFMEMORY;
        goto END;
    }
    intZeroMemory(altitude_value, MAX_PATH);

    if (computer == NULL)
    {
        error_code = ADVAPI32$RegOpenKeyExA(HKEY_LOCAL_MACHINE, SZ_SERVICE_KEY, 0, KEY_READ, &services_root);
    }
    else
    {
        error_code = ADVAPI32$RegConnectRegistryA(computer, HKEY_LOCAL_MACHINE, &remote_root);
        if (error_code == ERROR_SUCCESS)
        {
            error_code = ADVAPI32$RegOpenKeyExA(remote_root, SZ_SERVICE_KEY, 0, KEY_READ, &services_root);
        }
    }
    if (error_code != ERROR_SUCCESS)
    {
        goto END;
    }

    for (;;)
    {
        error_code = ADVAPI32$RegEnumKeyExA(services_root, service_index, service_name, &service_name_capacity, NULL, NULL, NULL, NULL);
        if (error_code == ERROR_NO_MORE_ITEMS)
        {
            error_code = ERROR_SUCCESS;
            break;
        }
        if (error_code != ERROR_SUCCESS)
        {
            goto END;
        }

        error_code = ADVAPI32$RegOpenKeyExA(services_root, service_name, 0, KEY_READ, &service_key);
        if (error_code == ERROR_SUCCESS)
        {
            error_code = ADVAPI32$RegOpenKeyExA(service_key, SZ_INSTANCE_KEY, 0, KEY_READ, &instances_key);
            if (error_code == ERROR_SUCCESS)
            {
                for (;;)
                {
                    error_code = ADVAPI32$RegEnumKeyExA(instances_key, instance_index, instance_name, &instance_name_capacity, NULL, NULL, NULL, NULL);
                    if (error_code == ERROR_NO_MORE_ITEMS)
                    {
                        error_code = ERROR_SUCCESS;
                        break;
                    }
                    if (error_code != ERROR_SUCCESS)
                    {
                        goto END;
                    }

                    error_code = ADVAPI32$RegOpenKeyExA(instances_key, instance_name, 0, KEY_READ, &instance_subkey);
                    if (error_code == ERROR_SUCCESS)
                    {
                        error_code = ADVAPI32$RegQueryValueExA(instance_subkey, SZ_ALTITUDE_VALUE, NULL, &altitude_value_type, (LPBYTE)altitude_value, &altitude_value_capacity);
                        if (error_code == ERROR_SUCCESS)
                        {
                            DWORD altitude = MSVCRT$strtoul(altitude_value, NULL, 10);
                            print_filter_type(service_name, altitude);
                        }

                        ADVAPI32$RegCloseKey(instance_subkey);
                        instance_subkey = NULL;
                    }

                    intZeroMemory(instance_name, MAX_PATH);
                    intZeroMemory(altitude_value, MAX_PATH);
                    instance_name_capacity = MAX_PATH;
                    altitude_value_capacity = MAX_PATH;
                    instance_index++;
                }
            }

            if (instances_key != NULL)
            {
                ADVAPI32$RegCloseKey(instances_key);
                instances_key = NULL;
            }

            ADVAPI32$RegCloseKey(service_key);
            service_key = NULL;
        }

        intZeroMemory(service_name, MAX_PATH);
        service_name_capacity = MAX_PATH;
        instance_index = 0;
        instance_name_capacity = MAX_PATH;
        service_index++;
    }

END:
    if (instance_subkey != NULL)
    {
        ADVAPI32$RegCloseKey(instance_subkey);
    }
    if (instances_key != NULL)
    {
        ADVAPI32$RegCloseKey(instances_key);
    }
    if (service_key != NULL)
    {
        ADVAPI32$RegCloseKey(service_key);
    }
    if (services_root != NULL)
    {
        ADVAPI32$RegCloseKey(services_root);
    }
    if (remote_root != NULL)
    {
        ADVAPI32$RegCloseKey(remote_root);
    }
    if (altitude_value != NULL)
    {
        intFree(altitude_value);
    }
    if (instance_name != NULL)
    {
        intFree(instance_name);
    }
    if (service_name != NULL)
    {
        intFree(service_name);
    }
    return error_code;
}


#ifdef BOF

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const char NANO_COMPUTER[] = "__NANO_COMPUTER__";
    const char *computer = NANO_COMPUTER;
    DWORD error_code = ERROR_SUCCESS;

    if (*computer == 0)
    {
        computer = NULL;
    }

    if (!bofstart())
    {
        return;
    }

    error_code = Enum_Filter_Driver(computer);
    if (error_code != ERROR_SUCCESS)
    {
        BeaconPrintf(CALLBACK_ERROR, "Enum_Filter_Driver FAILED (%lu)\n", error_code);
        goto END;
    }

    internal_printf("SUCCESS.\n");

END:
    printoutput(TRUE);
    bofstop();
}

#endif
