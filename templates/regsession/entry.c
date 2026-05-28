#include <windows.h>
#include "bofdefs.h"
#include "base.c"

void Reg_EnumKey(const char *hostname)
{
    DWORD j = 0;
    DWORD dwresult = 0;
    HKEY rootkey = 0;
    HKEY remoteKey = 0;
    int sessionCount = 0;

    if (hostname == NULL)
    {
        internal_printf("[*] Querying local registry...\n");
        dwresult = ADVAPI32$RegOpenKeyExA(HKEY_USERS, NULL, 0, KEY_READ, &rootkey);
        if (dwresult != ERROR_SUCCESS)
        {
            goto end;
        }
    }
    else
    {
        internal_printf("[*] Querying registry on %s...\n", hostname);
        dwresult = ADVAPI32$RegConnectRegistryA(hostname, HKEY_USERS, &remoteKey);
        if (dwresult != ERROR_SUCCESS)
        {
            internal_printf("failed to connect\n");
            goto end;
        }

        dwresult = ADVAPI32$RegOpenKeyExA(remoteKey, NULL, 0, KEY_READ, &rootkey);
        if (dwresult != ERROR_SUCCESS)
        {
            internal_printf("failed to open remote key\n");
            goto end;
        }
    }

    DWORD index = 0;
    CHAR subkeyName[256];
    DWORD subkeyNameSize = sizeof(subkeyName);

    while ((dwresult = ADVAPI32$RegEnumKeyExA(rootkey, index, subkeyName, &subkeyNameSize, NULL, NULL, NULL, NULL)) == ERROR_SUCCESS)
    {
        BOOL isSID = TRUE;

        if (
            subkeyName[0] == 'S' &&
            subkeyName[1] == '-' &&
            subkeyName[2] == '1' &&
            subkeyName[3] == '-' &&
            subkeyName[4] == '5' &&
            subkeyName[5] == '-' &&
            subkeyName[6] == '2' &&
            subkeyName[7] == '1'
        )
        {
            for (j = 0; j < subkeyNameSize; j++)
            {
                if (subkeyName[j] == '_')
                {
                    isSID = FALSE;
                    break;
                }
            }

            if (isSID)
            {
                sessionCount++;
                internal_printf("-----------Registry Session---------\n");
                internal_printf("UserSid: %s\n", subkeyName);
                internal_printf("Host: %s\n", hostname == NULL ? "(Local)" : hostname);
                internal_printf("---------End Registry Session-------\n\n");
            }
        }

        index++;
        subkeyNameSize = sizeof(subkeyName);
    }

    internal_printf("[*] Found %d sessions in the registry\n", sessionCount);

end:
    if (rootkey)
    {
        ADVAPI32$RegCloseKey(rootkey);
    }
    if (remoteKey)
    {
        ADVAPI32$RegCloseKey(remoteKey);
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

    static const char NANO_HOSTNAME[] = "__NANO_HOSTNAME__";
    const char *hostname = NANO_HOSTNAME;

    if (*hostname == 0)
    {
        hostname = NULL;
    }
    if (!bofstart())
    {
        return;
    }

    Reg_EnumKey(hostname);
    printoutput(TRUE);
};

#endif
