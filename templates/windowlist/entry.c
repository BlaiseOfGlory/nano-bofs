#include <windows.h>
#include "bofdefs.h"
#include "base.c"


static BOOL ALL_WINDOWS = FALSE;


static BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lParam)
{
    (void)lParam;

    char WindowName[128] = {0};
    DWORD WinLen = USER32$GetWindowTextA(hwnd, WindowName, 127);

    if (WindowName[0] != 0 && WinLen != 0)
    {
        if (ALL_WINDOWS)
        {
            internal_printf(
                "%-40s : %s\n",
                WindowName,
                USER32$IsWindowVisible(hwnd) ? "Visible" : "Hidden"
            );
        }
        else if (USER32$IsWindowVisible(hwnd))
        {
            internal_printf("%s\n", WindowName);
        }
    }
    return TRUE;
}


#ifdef BOF

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const BOOL NANO_ALL = __NANO_ALL__;

    if (!bofstart())
    {
        return;
    }

    ALL_WINDOWS = NANO_ALL;
    USER32$EnumDesktopWindows(NULL, (WNDENUMPROC)EnumWindowsProc, (LPARAM)NULL);
    printoutput(TRUE);
}

#endif
