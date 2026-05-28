#include <windows.h>
#include <string.h>
#include "bofdefs.h"
#include "base.c"

#define FSCTL_SRV_ENUMERATE_SNAPSHOTS 0x00144064

void EnumSnapshots(wchar_t *hostname, wchar_t *sharename)
{
    HANDLE hFile = NULL;
    wchar_t path[MAX_PATH] = {0};
    wchar_t *targetPath = NULL;
    IO_STATUS_BLOCK io = {0};
    char *snapshots = NULL;
    ULONG snapshotsLen = 0;
    wchar_t *entry = NULL;
    DWORD Volumes = 0;
    DWORD VolumesReturned = 0;
    DWORD VolumeBytes = 0;
    NTSTATUS ret = 0;

    MSVCRT$_snwprintf(path, MAX_PATH, L"\\\\%ls\\%ls", hostname, sharename);
    targetPath = path;
    internal_printf("Target = %ls\n", targetPath);

    hFile = KERNEL32$CreateFileW(
        targetPath,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        NULL
    );

    if (hFile == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not open root folder to query, Error: %lu", KERNEL32$GetLastError());
        return;
    }

    snapshotsLen = 16;
    snapshots = intAlloc(snapshotsLen);
    if (snapshots == NULL)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to allocate memory for snapshots");
        goto end;
    }

    ret = NTDLL$NtFsControlFile(
        hFile,
        NULL,
        NULL,
        NULL,
        &io,
        FSCTL_SRV_ENUMERATE_SNAPSHOTS,
        NULL,
        0,
        snapshots,
        snapshotsLen
    );
    memcpy(&Volumes, snapshots, 4);
    memcpy(&VolumesReturned, snapshots + 4, 4);
    memcpy(&VolumeBytes, snapshots + 8, 4);
    if (ret != 0 && VolumeBytes == 0)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to get snapshots: %X", ret);
        goto end;
    }
    intFree(snapshots);
    snapshots = NULL;

    snapshotsLen = 12 + VolumeBytes;
    snapshots = intAlloc(snapshotsLen);
    if (snapshots == NULL)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to allocate memory for snapshots");
        goto end;
    }

    ret = NTDLL$NtFsControlFile(
        hFile,
        NULL,
        NULL,
        NULL,
        &io,
        FSCTL_SRV_ENUMERATE_SNAPSHOTS,
        NULL,
        0,
        snapshots,
        snapshotsLen
    );
    if (ret != 0)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to get snapshots: %X", ret);
        goto end;
    }

    entry = (wchar_t *)((char *)snapshots + 12);
    for (DWORD i = 0; i < VolumesReturned; i++)
    {
        internal_printf("%ls\n", entry);
        entry += MSVCRT$wcslen(entry) + 1;
    }
    BeaconPrintf(CALLBACK_OUTPUT, "Found and enumerated %lu snapshots", VolumesReturned);

end:
    if (snapshots)
    {
        intFree(snapshots);
    }
    if (hFile != NULL && hFile != INVALID_HANDLE_VALUE)
    {
        KERNEL32$CloseHandle(hFile);
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

    static const wchar_t NANO_HOSTNAME[] = L"__NANO_HOSTNAME__";
    static const wchar_t NANO_SHARENAME[] = L"__NANO_SHARENAME__";
    wchar_t hostname_buffer[sizeof(NANO_HOSTNAME) / sizeof(NANO_HOSTNAME[0])];
    wchar_t sharename_buffer[sizeof(NANO_SHARENAME) / sizeof(NANO_SHARENAME[0])];

    if (!bofstart())
    {
        return;
    }

    memcpy(hostname_buffer, NANO_HOSTNAME, sizeof(NANO_HOSTNAME));
    memcpy(sharename_buffer, NANO_SHARENAME, sizeof(NANO_SHARENAME));
    EnumSnapshots(hostname_buffer, sharename_buffer);
    printoutput(TRUE);
}
#endif
