#include <windows.h>
#include <stdio.h>
#include "psapi.h"
#include "bofdefs.h"
#include "base.c"


static int PrintSingleModule(char *szFile)
{
    DWORD dwLen = 0;
    DWORD dwUseless = 0;
    LPSTR lpVI = NULL;

    dwLen = VERSION$GetFileVersionInfoSizeA((LPTSTR)szFile, &dwUseless);
    if (dwLen == 0)
    {
        internal_printf("%-60s ERROR: Could not GetFileVersionInfoSizeA() on the DLL.\n", szFile);
        return 1;
    }

    lpVI = (LPTSTR)KERNEL32$GlobalAlloc(GPTR, dwLen);
    if (lpVI != NULL)
    {
        WORD *langInfo = NULL;
        UINT cbLang = 0;
        char szVerDescription[256];
        char szVerCompanyName[256];
        LPVOID lpDescription = NULL;
        LPVOID lpCompanyName = NULL;
        UINT cbBufSize = 0;

        VERSION$GetFileVersionInfoA((LPTSTR)szFile, 0, dwLen, lpVI);
        VERSION$VerQueryValueA(lpVI, "\\VarFileInfo\\Translation", (LPVOID *)&langInfo, &cbLang);

        if (langInfo == NULL || cbLang < sizeof(WORD) * 2)
        {
            internal_printf("%-60s ERROR: Could not query translation info.\n", szFile);
            KERNEL32$GlobalFree((HGLOBAL)lpVI);
            return 1;
        }

        MSVCRT$sprintf(
            szVerDescription,
            "\\StringFileInfo\\%04x%04x\\%s",
            langInfo[0],
            langInfo[1],
            "FileDescription"
        );
        VERSION$VerQueryValueA(lpVI, szVerDescription, &lpDescription, &cbBufSize);

        MSVCRT$sprintf(
            szVerCompanyName,
            "\\StringFileInfo\\%04x%04x\\%s",
            langInfo[0],
            langInfo[1],
            "CompanyName"
        );
        VERSION$VerQueryValueA(lpVI, szVerCompanyName, &lpCompanyName, &cbBufSize);

        internal_printf(
            "%-60s %-25s%-25s\n",
            szFile,
            lpCompanyName != NULL ? (LPTSTR)lpCompanyName : "",
            lpDescription != NULL ? (LPTSTR)lpDescription : ""
        );

        KERNEL32$GlobalFree((HGLOBAL)lpVI);
    }
    else
    {
        internal_printf("ERROR: Could not allocate memory\n");
    }
    return 0;
}


static int PrintModules(DWORD processID)
{
    HMODULE *hMods = NULL;
    HANDLE hProcess = NULL;
    DWORD cbNeeded = 0;
    DWORD cbNeeded2 = 0;
    unsigned int i = 0;
    char szModName[MAX_PATH];

    internal_printf("Printing modules of process ID: %lu\n", processID);

    hProcess = KERNEL32$OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, processID);
    if (hProcess == NULL)
    {
        internal_printf("ERROR: Failed to open process.\n");
        return 1;
    }

    if (!PSAPI$EnumProcessModulesEx(hProcess, 0, 0, &cbNeeded, LIST_MODULES_ALL))
    {
        internal_printf("Failed to enumerate modules (not cross arch compatible)\n");
        KERNEL32$CloseHandle(hProcess);
        return 1;
    }

    hMods = (HMODULE *)intAlloc(cbNeeded);
    if (hMods == NULL)
    {
        internal_printf("ERROR: Could not allocate memory\n");
        KERNEL32$CloseHandle(hProcess);
        return 1;
    }

    if (PSAPI$EnumProcessModulesEx(hProcess, hMods, cbNeeded, &cbNeeded2, LIST_MODULES_ALL))
    {
        for (i = 0; i < (cbNeeded / sizeof(HMODULE)); i++)
        {
            if (PSAPI$GetModuleFileNameExA(hProcess, hMods[i], szModName, sizeof(szModName)))
            {
                PrintSingleModule(szModName);
            }
        }
    }

    intFree(hMods);
    KERNEL32$CloseHandle(hProcess);
    return 0;
}


#ifdef BOF

VOID go(char *args, int length)
{
    (void)args;
    (void)length;

    static const DWORD NANO_PID = __NANO_PID__;
    DWORD pid = NANO_PID;

    if (!bofstart())
    {
        return;
    }

    if (pid == 0)
    {
        pid = KERNEL32$GetCurrentProcessId();
    }

    PrintModules(pid);
    printoutput(TRUE);
}

#endif
