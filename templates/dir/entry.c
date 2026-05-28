#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include "queue.c"

void listDir(char *path, unsigned short subdirs)
{
    WIN32_FIND_DATA fd = {0};
    HANDLE hand = NULL;
    LARGE_INTEGER fileSize;
    LONGLONG totalFileSize = 0;
    int nFiles = 0;
    int nDirs = 0;
    Pqueue dirQueue = queueInit();
    char *uncIndex;
    char *curitem;
    char *nextPath;
    int pathlen = MSVCRT$strlen(path);

    // On UNC shares, FindFirstFileA needs an extra trailing slash on the share root.
    if (MSVCRT$_strnicmp(path, "\\\\", 2) == 0)
    {
        uncIndex = MSVCRT$strstr(path + 2, "\\");
        if (uncIndex != NULL && MSVCRT$strstr(uncIndex + 1, "\\") == NULL)
        {
            MSVCRT$strcat(path, "\\");
            pathlen = pathlen + 1;
        }
    }

    if (MSVCRT$strcmp(path + pathlen - 1, "\\") == 0)
    {
        MSVCRT$strcat(path, "*");
    }
    else if (MSVCRT$strcmp(path + pathlen - 1, ":") == 0)
    {
        MSVCRT$strcat(path, "\\*");
    }

    hand = KERNEL32$FindFirstFileA(path, &fd);
    if (hand == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Couldn't open %s: Error %u", path, KERNEL32$GetLastError());
        KERNEL32$FindClose(hand);
        return;
    }

    if ((fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && MSVCRT$strstr(path, "*") == NULL)
    {
        MSVCRT$strcat(path, "\\*");
        listDir(path, subdirs);
        KERNEL32$FindClose(hand);
        return;
    }

    internal_printf("Contents of %s:\n", path);
    do
    {
        SYSTEMTIME stUTC;
        SYSTEMTIME stLocal;
        KERNEL32$FileTimeToSystemTime(&(fd.ftLastWriteTime), &stUTC);
        KERNEL32$SystemTimeToTzSpecificLocalTime(NULL, &stUTC, &stLocal);

        internal_printf(
            "\t%02d/%02d/%02d %02d:%02d",
            stLocal.wMonth,
            stLocal.wDay,
            stLocal.wYear,
            stLocal.wHour,
            stLocal.wMinute
        );

        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
        {
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
            {
                internal_printf("%16s %s\n", "<junction>", fd.cFileName);
            }
            else
            {
                internal_printf("%16s %s\n", "<dir>", fd.cFileName);
            }
            nDirs++;

            if (MSVCRT$strcmp(fd.cFileName, ".") == 0 || MSVCRT$strcmp(fd.cFileName, "..") == 0)
            {
                continue;
            }

            if (subdirs)
            {
                nextPath = intAlloc((MSVCRT$strlen(path) + MSVCRT$strlen(fd.cFileName) + 3) * 2);
                MSVCRT$strncat(nextPath, path, MSVCRT$strlen(path) - 1);
                MSVCRT$strcat(nextPath, fd.cFileName);
                dirQueue->push(dirQueue, nextPath);
            }
        }
        else
        {
            fileSize.LowPart = fd.nFileSizeLow;
            fileSize.HighPart = fd.nFileSizeHigh;
            internal_printf("%16lld %s\n", fileSize.QuadPart, fd.cFileName);

            nFiles++;
            totalFileSize += fileSize.QuadPart;
        }
    } while (KERNEL32$FindNextFileA(hand, &fd));

    internal_printf("\t%32lld Total File Size for %d File(s)\n", totalFileSize, nFiles);
    internal_printf("\t%55d Dir(s)\n", nDirs);

    DWORD err = KERNEL32$GetLastError();
    if (err != ERROR_NO_MORE_FILES)
    {
        BeaconPrintf(CALLBACK_ERROR, "Error fetching files: %u\n", err);
        KERNEL32$FindClose(hand);
        return;
    }

    KERNEL32$FindClose(hand);
    while ((curitem = dirQueue->pop(dirQueue)) != NULL)
    {
        listDir(curitem, subdirs);
        intFree(curitem);
    }
    dirQueue->free(dirQueue);
}

#ifdef BOF

VOID go(
    IN PCHAR Buffer,
    IN ULONG Length
)
{
    (void)Buffer;
    (void)Length;

    static const char NANO_PATH[] = "__NANO_PATH__";
    static const unsigned short NANO_SUBDIRS = __NANO_SUBDIRS__;
    char realPath[sizeof(NANO_PATH) + 4] = {0};

    if (!bofstart())
    {
        return;
    }

    MSVCRT$strncat(realPath, NANO_PATH, sizeof(realPath) - 1);
    listDir(realPath, NANO_SUBDIRS);
    printoutput(TRUE);
}

#endif
