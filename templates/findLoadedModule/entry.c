#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"


BOOL ListModules(DWORD PID, const char *modSearchString)
{
    MODULEENTRY32 modinfo = {0};
    HANDLE hSnap = INVALID_HANDLE_VALUE;
    BOOL retVal = FALSE;
    BOOL more = FALSE;

    modinfo.dwSize = sizeof(MODULEENTRY32);
    hSnap = KERNEL32$CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, PID);
    if (hSnap == INVALID_HANDLE_VALUE)
    {
        return FALSE;
    }

    more = KERNEL32$Module32First(hSnap, &modinfo);
    while (more)
    {
        if (SHLWAPI$StrStrIA(modinfo.szExePath, modSearchString))
        {
            internal_printf("%s\n", modinfo.szExePath);
            retVal = TRUE;
        }
        more = KERNEL32$Module32Next(hSnap, &modinfo);
    }

    KERNEL32$CloseHandle(hSnap);
    return retVal;
}


void ListProcesses(const char *procSearchString, const char *modSearchString)
{
    PROCESSENTRY32 procinfo = {0};
    HANDLE hSnap = INVALID_HANDLE_VALUE;
    DWORD count = 0;
    BOOL more = FALSE;

    procinfo.dwSize = sizeof(PROCESSENTRY32);
    hSnap = KERNEL32$CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to list processes: %lu", KERNEL32$GetLastError());
        goto end;
    }

    more = KERNEL32$Process32First(hSnap, &procinfo);
    while (more)
    {
        if (!procSearchString || SHLWAPI$StrStrIA(procinfo.szExeFile, procSearchString))
        {
            if (ListModules(procinfo.th32ProcessID, modSearchString))
            {
                internal_printf("%-10lu : %s\n", procinfo.th32ProcessID, procinfo.szExeFile);
                count++;
            }
        }
        more = KERNEL32$Process32Next(hSnap, &procinfo);
    }

    if (KERNEL32$GetLastError() != ERROR_NO_MORE_FILES)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to enumerate all processes: %lu", KERNEL32$GetLastError());
        goto end;
    }

    if (!count)
    {
        internal_printf("Successfully enumerated all processes, but didn't find the requested module");
    }

end:
    if (hSnap != INVALID_HANDLE_VALUE)
    {
        KERNEL32$CloseHandle(hSnap);
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

    static const char NANO_MODULEPART[] = "__NANO_MODULEPART__";
    static const char NANO_PROCNAMEPART[] = "__NANO_PROCNAMEPART__";
    char modulepart_buffer[sizeof(NANO_MODULEPART)];
    char procnamepart_buffer[sizeof(NANO_PROCNAMEPART)];
    const char *procSearchString = NULL;

    if (!bofstart())
    {
        return;
    }

    memcpy(modulepart_buffer, NANO_MODULEPART, sizeof(NANO_MODULEPART));
    memcpy(procnamepart_buffer, NANO_PROCNAMEPART, sizeof(NANO_PROCNAMEPART));
    procSearchString = procnamepart_buffer[0] ? procnamepart_buffer : NULL;

    ListProcesses(procSearchString, modulepart_buffer);
    printoutput(TRUE);
}
#endif
