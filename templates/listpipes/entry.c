#include <windows.h>
#include "beacon.h"
#include "bofdefs.h"

static const wchar_t PIPE_GLOB[] = L"\\\\.\\pipe\\*";

void go(char *args, int len)
{
    WIN32_FIND_DATAW find_data;
    HANDLE find_handle = INVALID_HANDLE_VALUE;
    DWORD count = 0;

    (void)args;
    (void)len;

    find_handle = KERNEL32$FindFirstFileW(PIPE_GLOB, &find_data);
    if (find_handle == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "FindFirstFileW failed on \\\\.\\pipe\\* (%lu)", KERNEL32$GetLastError());
        return;
    }

    do
    {
        if (find_data.cFileName[0] == L'\0')
        {
            continue;
        }

        BeaconPrintf(CALLBACK_OUTPUT, "Pipe: %ls\n", find_data.cFileName);
        count++;
    } while (KERNEL32$FindNextFileW(find_handle, &find_data));

    KERNEL32$FindClose(find_handle);
    BeaconPrintf(CALLBACK_OUTPUT, "\nTotal named pipes: %lu", count);
}
