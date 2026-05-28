#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <winnetwk.h>

#define NET_USE_LIST_FMT_STRING     "%-12S %-8S %-32S %-32S\n"
#define NET_USE_DETAIL_FMT_STRING   "Local name        %S\nRemote name       %S\nResource type     %S\nStatus            %S\nUser Name         %S\n"
#define BIG_BUFFER_SIZE             16384
#define SMALL_BUFFER_SIZE           64
#define CONNECT_ENCRYPTED           32768
#define CMD_ADD 1
#define CMD_LIST 2
#define CMD_DELETE 3

#define SAFE_ALLOC(size) KERNEL32$HeapAlloc(KERNEL32$GetProcessHeap(), HEAP_ZERO_MEMORY, size)
#define SAFE_FREE(addr) \
    if ((addr) != NULL) \
    { \
        KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, (addr)); \
        (addr) = NULL; \
    }

static void print_windows_error(char *premsg, DWORD errnum)
{
    LPSTR msg = NULL;
    if (KERNEL32$FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, NULL, errnum, 0, (LPSTR)&msg, 0, NULL))
    {
        BeaconPrintf(CALLBACK_ERROR, "%s : %s", (premsg) ? premsg : "", msg);
    }
    else
    {
        BeaconPrintf(CALLBACK_ERROR, "failed to format error message: %lu", errnum);
    }

    if (msg)
    {
        KERNEL32$LocalFree(msg);
    }
}

static void Net_use_add(LPWSTR pswzDeviceName, LPWSTR pswzShareName, LPWSTR pswzPassword, LPWSTR pswzUsername, BOOL bPersist, BOOL bPrivacy)
{
    DWORD dwResult = ERROR_SUCCESS;
    LPNETRESOURCEW lpnrLocal = NULL;
    DWORD dwFlags = (bPersist) ? CONNECT_UPDATE_PROFILE : CONNECT_TEMPORARY;

    if (bPrivacy)
    {
        dwFlags |= CONNECT_ENCRYPTED;
    }

    lpnrLocal = (LPNETRESOURCEW)SAFE_ALLOC(BIG_BUFFER_SIZE);
    if (NULL == lpnrLocal)
    {
        BeaconPrintf(CALLBACK_ERROR, "SAFE_ALLOC failed: 0x%08lx\n", ERROR_OUTOFMEMORY);
        goto fail;
    }

    lpnrLocal->dwType = RESOURCETYPE_DISK;
    lpnrLocal->lpLocalName = pswzDeviceName;
    lpnrLocal->lpRemoteName = pswzShareName;
    lpnrLocal->lpProvider = NULL;

    dwResult = MPR$WNetAddConnection2W(lpnrLocal, pswzPassword, pswzUsername, dwFlags);
    if (NO_ERROR == dwResult)
    {
        internal_printf("The command completed successfully.\n");
    }
    else
    {
        print_windows_error("Unable to map share", dwResult);
        if (dwResult == ERROR_INVALID_PARAMETER)
        {
            BeaconPrintf(CALLBACK_ERROR, "If you set /REQUIREPRIVACY it is likely this flag is not supported on this computer");
        }
    }

fail:
    SAFE_FREE(lpnrLocal);
}

static void Net_use_delete(LPWSTR target, BOOL bPersist, BOOL force)
{
    DWORD dwResult = NO_ERROR;
    DWORD dwFlags = (bPersist) ? CONNECT_UPDATE_PROFILE : 0;

    dwResult = MPR$WNetCancelConnection2W(target, dwFlags, force);
    if (NO_ERROR == dwResult)
    {
        internal_printf("%ls was deleted successfully.\n", target);
    }
    else
    {
        print_windows_error("Unable to delete share", dwResult);
    }
}

static void Net_use_list(LPWSTR pswzDeviceName)
{
    DWORD dwResult = NO_ERROR;
    HANDLE hEnum = NULL;
    DWORD cbBuffer = BIG_BUFFER_SIZE;
    DWORD cEntries = (DWORD)-1;
    LPNETRESOURCEW lpnrLocal = NULL;
    DWORD i = 0;
    LPNETRESOURCEW lpCurrent = NULL;
    LPNETRESOURCEW lpnrRemote = NULL;
    DWORD dwResourceInformationLength = BIG_BUFFER_SIZE;
    LPWSTR lpSystem = NULL;
    WCHAR pwszStatus[SMALL_BUFFER_SIZE];
    WCHAR pwszDriveType[SMALL_BUFFER_SIZE];
    WCHAR pwszUserName[MAX_PATH];
    DWORD dwszUserNameLength = MAX_PATH;
    WCHAR pwszLocalName[MAX_PATH];
    WCHAR pwszRemoteName[MAX_PATH];
    WCHAR pwszProviderName[MAX_PATH];

    dwResult = MPR$WNetOpenEnumW(RESOURCE_CONNECTED, RESOURCETYPE_ANY, 0, NULL, &hEnum);
    if (dwResult != NO_ERROR)
    {
        BeaconPrintf(CALLBACK_ERROR, "MPR$WNetOpenEnumW failed: 0x%08lx\n", dwResult);
        goto fail;
    }
    lpnrLocal = (LPNETRESOURCEW)SAFE_ALLOC(cbBuffer);
    if (NULL == lpnrLocal)
    {
        BeaconPrintf(CALLBACK_ERROR, "SAFE_ALLOC failed: 0x%08lx\n", ERROR_OUTOFMEMORY);
        goto fail;
    }

    do
    {
        intZeroMemory(lpnrLocal, cbBuffer);
        cEntries = (DWORD)-1;

        dwResult = MPR$WNetEnumResourceW(hEnum, &cEntries, lpnrLocal, &cbBuffer);
        if (dwResult == NO_ERROR)
        {
            if (NULL == pswzDeviceName)
            {
                internal_printf(NET_USE_LIST_FMT_STRING, L"Status", L"Local", L"Remote", L"Network");
                internal_printf("-------------------------------------------------------------------------------------------------\n");
            }

            for (i = 0; i < cEntries; i++)
            {
                lpCurrent = &lpnrLocal[i];
                lpnrRemote = NULL;
                dwResourceInformationLength = BIG_BUFFER_SIZE;
                lpSystem = NULL;
                dwszUserNameLength = SMALL_BUFFER_SIZE;
                intZeroMemory(pwszStatus, SMALL_BUFFER_SIZE);
                intZeroMemory(pwszDriveType, SMALL_BUFFER_SIZE);
                intZeroMemory(pwszUserName, MAX_PATH);
                intZeroMemory(pwszLocalName, MAX_PATH);
                intZeroMemory(pwszRemoteName, MAX_PATH);
                intZeroMemory(pwszProviderName, MAX_PATH);

                if (lpCurrent->lpLocalName)
                {
                    MSVCRT$wcscpy(pwszLocalName, lpCurrent->lpLocalName);
                }
                if (lpCurrent->lpRemoteName)
                {
                    MSVCRT$wcscpy(pwszRemoteName, lpCurrent->lpRemoteName);
                }
                if (lpCurrent->lpProvider)
                {
                    MSVCRT$wcscpy(pwszProviderName, lpCurrent->lpProvider);
                }

                if (RESOURCETYPE_DISK == lpCurrent->dwType)
                {
                    MSVCRT$wcscpy(pwszDriveType, L"Disk");
                }
                else if (RESOURCETYPE_PRINT == lpCurrent->dwType)
                {
                    MSVCRT$wcscpy(pwszDriveType, L"Print");
                }
                else
                {
                    MSVCRT$wcscpy(pwszDriveType, L"Other");
                }

                lpnrRemote = (LPNETRESOURCEW)SAFE_ALLOC(dwResourceInformationLength);
                if (NULL == lpnrRemote)
                {
                    BeaconPrintf(CALLBACK_ERROR, "SAFE_ALLOC failed: 0x%08lx\n", ERROR_OUTOFMEMORY);
                    goto fail;
                }

                dwResult = MPR$WNetGetResourceInformationW(lpCurrent, lpnrRemote, &dwResourceInformationLength, &lpSystem);
                if (NO_ERROR == dwResult)
                {
                    MSVCRT$wcscpy(pwszStatus, L"OK");
                }
                else if (ERROR_BAD_NET_NAME == dwResult)
                {
                    MSVCRT$wcscpy(pwszStatus, L"Disconnected");
                }
                else if (ERROR_NO_NETWORK == dwResult)
                {
                    MSVCRT$wcscpy(pwszStatus, L"Unavailable");
                }

                SAFE_FREE(lpnrRemote);

                MPR$WNetGetUserW(pwszLocalName, pwszUserName, &dwszUserNameLength);

                if (NULL == pswzDeviceName)
                {
                    internal_printf(NET_USE_LIST_FMT_STRING, pwszStatus, pwszLocalName, pwszRemoteName, pwszProviderName);
                }
                else
                {
                    if (0 != MSVCRT$_wcsicmp(pwszLocalName, pswzDeviceName) && 0 != MSVCRT$_wcsicmp(pwszRemoteName, pswzDeviceName))
                    {
                        continue;
                    }

                    internal_printf(
                        NET_USE_DETAIL_FMT_STRING,
                        pwszLocalName,
                        pwszRemoteName,
                        pwszDriveType,
                        pwszStatus,
                        pwszUserName
                    );
                }
            }
        }
        else if (dwResult != ERROR_NO_MORE_ITEMS)
        {
            BeaconPrintf(CALLBACK_ERROR, "MPR$WNetEnumResourceW failed with error %lu\n", dwResult);
            goto fail;
        }
    } while (dwResult != ERROR_NO_MORE_ITEMS);

    internal_printf("The command completed successfully.\n");

fail:
    SAFE_FREE(lpnrLocal);
    SAFE_FREE(lpnrRemote);

    if ((NULL != hEnum) && (INVALID_HANDLE_VALUE != hEnum))
    {
        dwResult = MPR$WNetCloseEnum(hEnum);
        if (dwResult != NO_ERROR)
        {
            BeaconPrintf(CALLBACK_ERROR, "MPR$WNetCloseEnum failed with error %lu\n", dwResult);
        }
    }
}

#ifdef BOF
VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const short NANO_CMD = __NANO_CMD__;
    static const short NANO_PERSIST = __NANO_PERSIST__;
    static const short NANO_REQUIRE_PRIVACY = __NANO_REQUIRE_PRIVACY__;
    static const short NANO_FORCE = __NANO_FORCE__;
    static const wchar_t NANO_TARGET[] = L"__NANO_TARGET__";
    static const wchar_t NANO_SHARE_NAME[] = L"__NANO_SHARE_NAME__";
    static const wchar_t NANO_USERNAME[] = L"__NANO_USERNAME__";
    static const wchar_t NANO_PASSWORD[] = L"__NANO_PASSWORD__";
    static const wchar_t NANO_DEVICE_NAME[] = L"__NANO_DEVICE_NAME__";

    wchar_t target_buffer[512] = {0};
    wchar_t share_buffer[512] = {0};
    wchar_t username_buffer[256] = {0};
    wchar_t password_buffer[256] = {0};
    wchar_t device_buffer[32] = {0};
    LPWSTR pswzDeviceName = NULL;
    LPWSTR pswzShareName = NULL;
    LPWSTR pswzPassword = NULL;
    LPWSTR pswzUsername = NULL;
    LPWSTR pswzTarget = NULL;
    size_t i = 0;

    for (i = 0; i < (sizeof(target_buffer) / sizeof(target_buffer[0])) - 1 && NANO_TARGET[i] != 0; i++)
    {
        target_buffer[i] = NANO_TARGET[i];
    }
    for (i = 0; i < (sizeof(share_buffer) / sizeof(share_buffer[0])) - 1 && NANO_SHARE_NAME[i] != 0; i++)
    {
        share_buffer[i] = NANO_SHARE_NAME[i];
    }
    for (i = 0; i < (sizeof(username_buffer) / sizeof(username_buffer[0])) - 1 && NANO_USERNAME[i] != 0; i++)
    {
        username_buffer[i] = NANO_USERNAME[i];
    }
    for (i = 0; i < (sizeof(password_buffer) / sizeof(password_buffer[0])) - 1 && NANO_PASSWORD[i] != 0; i++)
    {
        password_buffer[i] = NANO_PASSWORD[i];
    }
    for (i = 0; i < (sizeof(device_buffer) / sizeof(device_buffer[0])) - 1 && NANO_DEVICE_NAME[i] != 0; i++)
    {
        device_buffer[i] = NANO_DEVICE_NAME[i];
    }

    if (target_buffer[0] != 0)
    {
        pswzTarget = target_buffer;
    }
    if (share_buffer[0] != 0)
    {
        pswzShareName = share_buffer;
    }
    if (username_buffer[0] != 0)
    {
        pswzUsername = username_buffer;
    }
    if (password_buffer[0] != 0)
    {
        pswzPassword = password_buffer;
    }
    if (device_buffer[0] != 0)
    {
        pswzDeviceName = device_buffer;
    }

    if (!bofstart())
    {
        return;
    }

    if (NANO_CMD == CMD_ADD)
    {
        Net_use_add(pswzDeviceName, pswzShareName, pswzPassword, pswzUsername, NANO_PERSIST, NANO_REQUIRE_PRIVACY);
    }
    else if (NANO_CMD == CMD_LIST)
    {
        Net_use_list(pswzTarget);
    }
    else if (NANO_CMD == CMD_DELETE)
    {
        Net_use_delete(pswzTarget, NANO_PERSIST, NANO_FORCE);
    }
    else
    {
        BeaconPrintf(CALLBACK_ERROR, "invalid embedded command selector: %d", NANO_CMD);
    }

    printoutput(TRUE);
    bofstop();
}
#endif
