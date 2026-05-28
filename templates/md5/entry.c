#include <windows.h>
#include <stdio.h>
#include "beacon.h"
#include "bofdefs.h"
#include "base.c"


static BOOL MD5File(LPCSTR path)
{
    HCRYPTPROV hProv;
    HCRYPTHASH hHash;
    HANDLE hFile;
    DWORD dwBytesRead;
    BYTE bReadFile[0x512];
    BYTE bMD5[16];

    hFile = KERNEL32$CreateFileA(path, FILE_READ_ACCESS, FILE_SHARE_READ, 0, OPEN_EXISTING, 0, 0);
    if (hFile == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Error: Could not find file \"%s\"", path);
        return FALSE;
    }

    if (!ADVAPI32$CryptAcquireContextA(&hProv, NULL, NULL, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT))
    {
        KERNEL32$CloseHandle(hFile);
        BeaconPrintf(CALLBACK_ERROR, "Error: Could not initialize HCRYPTPROV context");
        return FALSE;
    }

    if (!ADVAPI32$CryptCreateHash(hProv, CALG_MD5, 0, 0, &hHash))
    {
        ADVAPI32$CryptReleaseContext(hProv, 0);
        KERNEL32$CloseHandle(hFile);
        BeaconPrintf(CALLBACK_ERROR, "Error: CryptCreateHash (MD5) failed");
        return FALSE;
    }

    while (KERNEL32$ReadFile(hFile, bReadFile, sizeof(bReadFile), &dwBytesRead, NULL))
    {
        if (dwBytesRead == 0)
        {
            break;
        }
        ADVAPI32$CryptHashData(hHash, bReadFile, dwBytesRead, 0);
    }

    dwBytesRead = sizeof(bMD5);
    if (ADVAPI32$CryptGetHashParam(hHash, HP_HASHVAL, bMD5, &dwBytesRead, 0))
    {
        CHAR hash[64] = "";
        for (DWORD i = 0; i < dwBytesRead; i++)
        {
            CHAR digits[3];
            MSVCRT$sprintf(digits, "%02X", bMD5[i]);
            MSVCRT$strcat(hash, digits);
        }
        BeaconPrintf(CALLBACK_OUTPUT, "MD5 Hash for %s: %s", path, hash);
    }

    ADVAPI32$CryptDestroyHash(hHash);
    ADVAPI32$CryptReleaseContext(hProv, 0);
    KERNEL32$CloseHandle(hFile);
    return TRUE;
}


#ifdef BOF

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    (void)Buffer;
    (void)Length;

    static const char NANO_PATH[] = "__NANO_PATH__";

    if (!bofstart())
    {
        return;
    }

    MD5File(NANO_PATH);
}

#endif
