#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <winnetwk.h>

#define NET_USE_LIST_FMT_STRING     "%-12S %-8S %-32S %-32S\n"
#define NET_USE_DETAIL_FMT_STRING   "Local name        %S\nRemote name       %S\nResource type     %S\nStatus            %S\nUser Name         %S\n"
#define BIG_BUFFER_SIZE             16384
#define SMALL_BUFFER_SIZE           64

#define SAFE_ALLOC(size) KERNEL32$HeapAlloc(KERNEL32$GetProcessHeap(), HEAP_ZERO_MEMORY, size)
#define SAFE_FREE(addr) \
    if ((addr) != NULL) \
    { \
        KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, (addr)); \
        (addr) = NULL; \
    }

typedef DWORD (WINAPI *fnWNetOpenEnumW)(DWORD, DWORD, DWORD, LPNETRESOURCEW, LPHANDLE);
typedef DWORD (WINAPI *fnWNetEnumResourceW)(HANDLE, LPDWORD, LPVOID, LPDWORD);
typedef DWORD (WINAPI *fnWNetGetResourceInformationW)(LPNETRESOURCEW, LPVOID, LPDWORD, LPWSTR*);
typedef DWORD (WINAPI *fnWNetGetUserW)(LPCWSTR, LPWSTR, LPDWORD);
typedef DWORD (WINAPI *fnWNetCloseEnum)(HANDLE);

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
    HMODULE hMpr = NULL;
    fnWNetOpenEnumW pWNetOpenEnumW = NULL;
    fnWNetEnumResourceW pWNetEnumResourceW = NULL;
    fnWNetGetResourceInformationW pWNetGetResourceInformationW = NULL;
    fnWNetGetUserW pWNetGetUserW = NULL;
    fnWNetCloseEnum pWNetCloseEnum = NULL;

    hMpr = KERNEL32$LoadLibraryA("Mpr");
    if (hMpr == NULL)
    {
        BeaconPrintf(CALLBACK_ERROR, "LoadLibraryA(Mpr) failed\n");
        goto fail;
    }

    pWNetOpenEnumW = (fnWNetOpenEnumW)KERNEL32$GetProcAddress(hMpr, "WNetOpenEnumW");
    pWNetEnumResourceW = (fnWNetEnumResourceW)KERNEL32$GetProcAddress(hMpr, "WNetEnumResourceW");
    pWNetGetResourceInformationW = (fnWNetGetResourceInformationW)KERNEL32$GetProcAddress(hMpr, "WNetGetResourceInformationW");
    pWNetGetUserW = (fnWNetGetUserW)KERNEL32$GetProcAddress(hMpr, "WNetGetUserW");
    pWNetCloseEnum = (fnWNetCloseEnum)KERNEL32$GetProcAddress(hMpr, "WNetCloseEnum");
    if (!pWNetOpenEnumW || !pWNetEnumResourceW || !pWNetGetResourceInformationW || !pWNetGetUserW || !pWNetCloseEnum)
    {
        BeaconPrintf(CALLBACK_ERROR, "GetProcAddress(WNet*) failed\n");
        goto fail;
    }

    dwResult = pWNetOpenEnumW(RESOURCE_CONNECTED, RESOURCETYPE_ANY, 0, NULL, &hEnum);
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

        dwResult = pWNetEnumResourceW(hEnum, &cEntries, lpnrLocal, &cbBuffer);
        if (dwResult == NO_ERROR)
        {
            if (NULL == pswzDeviceName)
            {
                internal_printf(NET_USE_LIST_FMT_STRING, L"Status", L"Local", L"Remote", L"Network");
                internal_printf("-------------------------------------------------------------------------------\n");
            }

            for (i = 0; i < cEntries; i++)
            {
                lpCurrent = &lpnrLocal[i];
                lpnrRemote = NULL;
                dwResourceInformationLength = BIG_BUFFER_SIZE;
                lpSystem = NULL;
                dwszUserNameLength = MAX_PATH;
                intZeroMemory(pwszStatus, sizeof(pwszStatus));
                intZeroMemory(pwszDriveType, sizeof(pwszDriveType));
                intZeroMemory(pwszUserName, sizeof(pwszUserName));
                intZeroMemory(pwszLocalName, sizeof(pwszLocalName));
                intZeroMemory(pwszRemoteName, sizeof(pwszRemoteName));
                intZeroMemory(pwszProviderName, sizeof(pwszProviderName));

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

                dwResult = pWNetGetResourceInformationW(lpCurrent, lpnrRemote, &dwResourceInformationLength, &lpSystem);
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

                if (pwszLocalName[0] != 0)
                {
                    pWNetGetUserW(pwszLocalName, pwszUserName, &dwszUserNameLength);
                }

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
        dwResult = pWNetCloseEnum(hEnum);
        if (dwResult != NO_ERROR)
        {
            BeaconPrintf(CALLBACK_ERROR, "MPR$WNetCloseEnum failed with error %lu\n", dwResult);
        }
    }
    if (hMpr != NULL)
    {
        KERNEL32$FreeLibrary(hMpr);
    }
}

#ifdef BOF
VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_TARGET[] = L"__NANO_TARGET__";
    wchar_t target_buffer[512] = {0};
    LPWSTR pswzTarget = NULL;
    size_t i = 0;

    for (i = 0; i < (sizeof(target_buffer) / sizeof(target_buffer[0])) - 1 && NANO_TARGET[i] != 0; i++)
    {
        target_buffer[i] = NANO_TARGET[i];
    }
    if (target_buffer[0] != 0)
    {
        pswzTarget = target_buffer;
    }

    if (!bofstart())
    {
        return;
    }

    Net_use_list(pswzTarget);
    printoutput(TRUE);
    bofstop();
}
#endif
