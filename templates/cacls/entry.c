#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <sddl.h>
#include <windef.h>

#define IDS_ABBR_CI "(CI)"
#define IDS_ABBR_OI "(OI)"
#define IDS_ABBR_IO "(IO)"
#define IDS_ABBR_FULL "F"
#define IDS_ABBR_READ "R"
#define IDS_ABBR_WRITE "W"
#define IDS_ABBR_CHANGE "C"
#define IDS_ABBR_NONE "N"
#define IDS_ALLOW ""
#define IDS_DENY "(DENY)"
#define IDS_SPECIAL_ACCESS "(special access:)"
#define IDS_GENERIC_READ "GENERIC_READ"
#define IDS_GENERIC_WRITE "GENERIC_WRITE"
#define IDS_GENERIC_EXECUTE "GENERIC_EXECUTE"
#define IDS_GENERIC_ALL "GENERIC_ALL"
#define IDS_FILE_GENERIC_EXECUTE "FILE_GENERIC_EXECUTE"
#define IDS_FILE_GENERIC_READ "FILE_GENERIC_READ"
#define IDS_FILE_GENERIC_WRITE "FILE_GENERIC_WRITE"
#define IDS_FILE_READ_DATA "FILE_READ_DATA"
#define IDS_FILE_WRITE_DATA "FILE_WRITE_DATA"
#define IDS_FILE_APPEND_DATA "FILE_APPEND_DATA"
#define IDS_FILE_READ_EA "FILE_READ_EA"
#define IDS_FILE_WRITE_EA "FILE_WRITE_EA"
#define IDS_FILE_EXECUTE "FILE_EXECUTE"
#define IDS_FILE_DELETE_CHILD "FILE_DELETE_CHILD"
#define IDS_FILE_READ_ATTRIBUTES "FILE_READ_ATTRIBUTES"
#define IDS_FILE_WRITE_ATTRIBUTES "FILE_WRITE_ATTRIBUTES"
#define IDS_MAXIMUM_ALLOWED "MAXIMUM_ALLOWED"
#define IDS_ACCESS_SYSTEM_SECURITY "ACCESS_SYSTEM_SECURITY"
#define IDS_SPECIFIC_RIGHTS_ALL "SPECIFIC_RIGHTS_ALL"
#define IDS_STANDARD_RIGHTS_REQUIRED "STANDARD_RIGHTS_REQUIRED"
#define IDS_SYNCHRONIZE "SYNCHRONIZE"
#define IDS_WRITE_OWNER "WRITE_OWNER"
#define IDS_WRITE_DAC "WRITE_DAC"
#define IDS_READ_CONTROL "READ_CONTROL"
#define IDS_DELETE "DELETE"
#define IDS_STANDARD_RIGHTS_ALL "STANDARD_RIGHTS_ALL"

enum searchtype
{
    File,
    Folder,
    Fail
};

#pragma pack(push, 1)
typedef struct _AR
{
    DWORD Access;
    const char *uID;
} AR, *pAR;
#pragma pack(pop)

static pAR AccessRights = NULL;

#define LOVEIT(a, b, c) a.Access = b; a.uID = c


static void LovingIt(void)
{
    AccessRights = (pAR)intAlloc(26 * sizeof(AR));
    LOVEIT(AccessRights[0], FILE_WRITE_ATTRIBUTES, IDS_FILE_WRITE_ATTRIBUTES);
    LOVEIT(AccessRights[1], FILE_READ_ATTRIBUTES, IDS_FILE_READ_ATTRIBUTES);
    LOVEIT(AccessRights[2], FILE_DELETE_CHILD, IDS_FILE_DELETE_CHILD);
    LOVEIT(AccessRights[3], FILE_EXECUTE, IDS_FILE_EXECUTE);
    LOVEIT(AccessRights[4], FILE_WRITE_EA, IDS_FILE_WRITE_EA);
    LOVEIT(AccessRights[5], FILE_READ_EA, IDS_FILE_READ_EA);
    LOVEIT(AccessRights[6], FILE_APPEND_DATA, IDS_FILE_APPEND_DATA);
    LOVEIT(AccessRights[7], FILE_WRITE_DATA, IDS_FILE_WRITE_DATA);
    LOVEIT(AccessRights[8], FILE_READ_DATA, IDS_FILE_READ_DATA);
    LOVEIT(AccessRights[9], FILE_GENERIC_EXECUTE, IDS_FILE_GENERIC_EXECUTE);
    LOVEIT(AccessRights[10], FILE_GENERIC_WRITE, IDS_FILE_GENERIC_WRITE);
    LOVEIT(AccessRights[11], FILE_GENERIC_READ, IDS_FILE_GENERIC_READ);
    LOVEIT(AccessRights[12], GENERIC_ALL, IDS_GENERIC_ALL);
    LOVEIT(AccessRights[13], GENERIC_EXECUTE, IDS_GENERIC_EXECUTE);
    LOVEIT(AccessRights[14], GENERIC_WRITE, IDS_GENERIC_WRITE);
    LOVEIT(AccessRights[15], GENERIC_READ, IDS_GENERIC_READ);
    LOVEIT(AccessRights[16], MAXIMUM_ALLOWED, IDS_MAXIMUM_ALLOWED);
    LOVEIT(AccessRights[17], ACCESS_SYSTEM_SECURITY, IDS_ACCESS_SYSTEM_SECURITY);
    LOVEIT(AccessRights[18], SPECIFIC_RIGHTS_ALL, IDS_SPECIFIC_RIGHTS_ALL);
    LOVEIT(AccessRights[19], STANDARD_RIGHTS_REQUIRED, IDS_STANDARD_RIGHTS_REQUIRED);
    LOVEIT(AccessRights[20], SYNCHRONIZE, IDS_SYNCHRONIZE);
    LOVEIT(AccessRights[21], WRITE_OWNER, IDS_WRITE_OWNER);
    LOVEIT(AccessRights[22], WRITE_DAC, IDS_WRITE_DAC);
    LOVEIT(AccessRights[23], READ_CONTROL, IDS_READ_CONTROL);
    LOVEIT(AccessRights[24], DELETE, IDS_DELETE);
    LOVEIT(AccessRights[25], STANDARD_RIGHTS_ALL, IDS_STANDARD_RIGHTS_ALL);
}


static void DoneLovingIt(void)
{
    if (AccessRights != NULL)
    {
        intFree(AccessRights);
        AccessRights = NULL;
    }
}


static BOOL PrintFileDacl(IN LPWSTR FilePath, IN LPWSTR FileName, IN enum searchtype ST)
{
    GENERIC_MAPPING FileGenericMapping = {0};
    SIZE_T Length;
    PSECURITY_DESCRIPTOR SecurityDescriptor;
    DWORD SDSize = 0;
    WCHAR FullFileName[MAX_PATH + 1];
    BOOL Error = FALSE;
    BOOL Ret = FALSE;
    int x = 0;
    int x2 = 0;

    if (ST == File)
    {
        Length = KERNEL32$lstrlenW(FilePath) + KERNEL32$lstrlenW(FileName);
        if (Length > MAX_PATH)
        {
            KERNEL32$SetLastError(ERROR_FILE_NOT_FOUND);
            return FALSE;
        }

        KERNEL32$lstrcpynW(FullFileName, FilePath, MAX_PATH);
        KERNEL32$lstrcatW(FullFileName, FileName);
    }
    else
    {
        KERNEL32$lstrcpynW(FullFileName, FilePath, MAX_PATH);
    }

    if (!ADVAPI32$GetFileSecurityW(FullFileName, DACL_SECURITY_INFORMATION, NULL, 0, &SDSize) &&
        KERNEL32$GetLastError() != ERROR_INSUFFICIENT_BUFFER)
    {
        return FALSE;
    }

    SecurityDescriptor = (PSECURITY_DESCRIPTOR)intAlloc(SDSize);
    if (SecurityDescriptor == NULL)
    {
        KERNEL32$SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return FALSE;
    }

    if (ADVAPI32$GetFileSecurityW(FullFileName, DACL_SECURITY_INFORMATION, SecurityDescriptor, SDSize, &SDSize))
    {
        PACL Dacl;
        BOOL DaclPresent;
        BOOL DaclDefaulted;
        if (ADVAPI32$GetSecurityDescriptorDacl(SecurityDescriptor, &DaclPresent, &Dacl, &DaclDefaulted))
        {
            if (Dacl && DaclPresent)
            {
                PACCESS_ALLOWED_ACE Ace;
                DWORD AceIndex = 0;

                while (ADVAPI32$GetAce(Dacl, AceIndex, (PVOID *)&Ace))
                {
                    LPWSTR SidString = NULL;
                    DWORD IndentAccess = 0;
                    DWORD AccessMask = Ace->Mask;
                    PSID Sid = (PSID)&Ace->SidStart;

                    if (!ADVAPI32$ConvertSidToStringSidW(Sid, &SidString))
                    {
                        Error = TRUE;
                        break;
                    }

                    internal_printf("%S ", FullFileName);

                    if (AceIndex == 0)
                    {
                        DWORD i = 0;
                        while (FullFileName[i] != L'\0')
                        {
                            FullFileName[i++] = L' ';
                        }
                    }

                    if (SidString != NULL)
                    {
                        internal_printf("%S:", SidString);
                        IndentAccess = (DWORD)KERNEL32$lstrlenW(SidString);
                    }

                    if (Ace->Header.AceFlags & CONTAINER_INHERIT_ACE)
                    {
                        internal_printf("%s", IDS_ABBR_CI);
                        IndentAccess += 4;
                    }
                    if (Ace->Header.AceFlags & OBJECT_INHERIT_ACE)
                    {
                        internal_printf("%s", IDS_ABBR_OI);
                        IndentAccess += 4;
                    }
                    if (Ace->Header.AceFlags & INHERIT_ONLY_ACE)
                    {
                        internal_printf("%s", IDS_ABBR_IO);
                        IndentAccess += 4;
                    }

                    IndentAccess += 2;
                    ADVAPI32$MapGenericMask(&AccessMask, &FileGenericMapping);
                    if (Ace->Header.AceType & ACCESS_DENIED_ACE_TYPE)
                    {
                        if (AccessMask == FILE_ALL_ACCESS)
                        {
                            internal_printf("%s", IDS_ABBR_NONE);
                        }
                        else
                        {
                            internal_printf("%s", IDS_DENY);
                            goto PrintSpecialAccess;
                        }
                    }
                    else
                    {
                        if (AccessMask == FILE_ALL_ACCESS)
                        {
                            internal_printf("%s", IDS_ABBR_FULL);
                        }
                        else if (!(Ace->Mask & (GENERIC_READ | GENERIC_EXECUTE)) &&
                                 AccessMask == (FILE_GENERIC_READ | FILE_EXECUTE))
                        {
                            internal_printf("%s", IDS_ABBR_READ);
                        }
                        else if (AccessMask == (FILE_GENERIC_READ | FILE_GENERIC_WRITE | FILE_EXECUTE | DELETE))
                        {
                            internal_printf("%s", IDS_ABBR_CHANGE);
                        }
                        else if (AccessMask == FILE_GENERIC_WRITE)
                        {
                            internal_printf("%s", IDS_ABBR_WRITE);
                        }
                        else
                        {
                            internal_printf("%s", IDS_ALLOW);
PrintSpecialAccess:
                            internal_printf("%s", IDS_SPECIAL_ACCESS);
                            x = 25;
                            while (x >= 0)
                            {
                                if ((Ace->Mask & AccessRights[x].Access) == AccessRights[x].Access)
                                {
                                    internal_printf("\n%S ", FullFileName);
                                    for (x2 = 0; x2 < (int)IndentAccess; x2++)
                                    {
                                        internal_printf("%s", " ");
                                    }
                                    internal_printf("%s", AccessRights[x].uID);
                                }
                                x--;
                            }
                            internal_printf("%s", "\n");
                        }
                    }

                    internal_printf("%s", "\n");

                    if (SidString != NULL)
                    {
                        KERNEL32$LocalFree((HLOCAL)SidString);
                        SidString = NULL;
                    }
                    AceIndex++;
                }

                if (!Error)
                {
                    Ret = TRUE;
                }
            }
            else
            {
                KERNEL32$SetLastError(ERROR_NO_SECURITY_ON_OBJECT);
            }
        }
    }

    intFree(SecurityDescriptor);
    return Ret;
}


static VOID AddBackslash(LPWSTR FilePath)
{
    INT len = KERNEL32$lstrlenW(FilePath);
    if (len == 0)
    {
        return;
    }
    if (FilePath[len - 1] != L'\\')
    {
        FilePath[len] = L'\\';
        FilePath[len + 1] = L'\0';
    }
}


static enum searchtype GetPathOfFile(LPWSTR FilePath, LPCWSTR pszFiles)
{
    WCHAR FullPath[MAX_PATH];
    LPWSTR pch;
    DWORD attrs;

    attrs = KERNEL32$GetFileAttributesW(pszFiles);
    if (attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_DIRECTORY))
    {
        KERNEL32$GetFullPathNameW(pszFiles, MAX_PATH, FilePath, NULL);
        return Folder;
    }

    KERNEL32$lstrcpynW(FilePath, pszFiles, MAX_PATH);
    pch = MSVCRT$wcsrchr(FilePath, L'\\');
    if (pch != NULL)
    {
        *pch = 0;
        if (!KERNEL32$GetFullPathNameW(FilePath, MAX_PATH, FullPath, NULL))
        {
            BeaconPrintf(CALLBACK_ERROR, "Failed to resolve path: 0x%lx", KERNEL32$GetLastError());
            return Fail;
        }

        KERNEL32$lstrcpynW(FilePath, FullPath, MAX_PATH);
        attrs = KERNEL32$GetFileAttributesW(FilePath);
        if (attrs == 0xFFFFFFFF || !(attrs & FILE_ATTRIBUTE_DIRECTORY))
        {
            BeaconPrintf(CALLBACK_ERROR, "Failed to resolve attributes: %ld", ERROR_DIRECTORY);
            return Fail;
        }
    }
    else
    {
        KERNEL32$GetCurrentDirectoryW(MAX_PATH, FilePath);
    }

    AddBackslash(FilePath);
    return File;
}


static BOOL PrintDaclsOfFiles(LPCWSTR pszFiles)
{
    WCHAR FilePath[MAX_PATH] = {0};
    WIN32_FIND_DATAW FindData;
    HANDLE hFind;
    DWORD LastError;
    enum searchtype ST;

    ST = GetPathOfFile(FilePath, pszFiles);
    switch (ST)
    {
        case Fail:
            BeaconPrintf(CALLBACK_ERROR, "Unable to resolve file path");
            return FALSE;
        case Folder:
            if (!PrintFileDacl(FilePath, L"", ST))
            {
                BeaconPrintf(CALLBACK_ERROR, "Unable to list permissions of file %S", pszFiles);
                return FALSE;
            }
            return TRUE;
        case File:
            break;
        default:
            break;
    }

    hFind = KERNEL32$FindFirstFileW(pszFiles, &FindData);
    if (hFind == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Error starting search handle\n");
        return FALSE;
    }

    do
    {
        if (FindData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
        {
            continue;
        }

        if (!PrintFileDacl(FilePath, FindData.cFileName, ST))
        {
            LastError = KERNEL32$GetLastError();
            if (LastError == ERROR_ACCESS_DENIED)
            {
                BeaconPrintf(CALLBACK_ERROR, "Unable to list permissions of file %S", FindData.cFileName);
            }
            else
            {
                BeaconPrintf(CALLBACK_ERROR, "Unhandled error in listing: 0x%lx", LastError);
                break;
            }
        }
        else
        {
            internal_printf("\n");
        }
    } while (KERNEL32$FindNextFileW(hFind, &FindData));

    LastError = KERNEL32$GetLastError();
    KERNEL32$FindClose(hFind);
    if (LastError != ERROR_NO_MORE_FILES)
    {
        BeaconPrintf(CALLBACK_ERROR, "Unable to handle all files, received error 0x%lx", LastError);
        return FALSE;
    }

    return TRUE;
}


#ifdef BOF

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_PATH[] = L"__NANO_PATH__";
    wchar_t target_path[MAX_PATH];

    if (!bofstart())
    {
        return;
    }

    // Folder targets were unreliable when read straight from static storage
    // under Apollo; copying onto the stack matches the stable runtime shape.
    KERNEL32$lstrcpynW(target_path, NANO_PATH, MAX_PATH);
    LovingIt();
    PrintDaclsOfFiles(target_path);
    DoneLovingIt();
    printoutput(TRUE);
}

#endif
