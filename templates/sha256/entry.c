#include <windows.h>
#include <stdio.h>
#include "beacon.h"
#include "bofdefs.h"
#include "base.c"


static BOOL SHA256File(LPCSTR path)
{
    HCRYPTPROV hProv;
    HCRYPTHASH hHash;
    HANDLE hFile;
    DWORD dwBytesRead;
    BYTE bReadFile[0x512];
    BYTE bSHA256[32];

    hFile = KERNEL32$CreateFileA(path, FILE_READ_ACCESS, FILE_SHARE_READ, 0, OPEN_EXISTING, 0, 0);
    if (hFile == INVALID_HANDLE_VALUE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Error: Could not find file \"%s\"", path);
        return FALSE;
    }

    if (!ADVAPI32$CryptAcquireContextA(&hProv, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT))
    {
        KERNEL32$CloseHandle(hFile);
        BeaconPrintf(CALLBACK_ERROR, "Error: Could not initilize HCRYPTPROV context");
        return FALSE;
    }

    if (!ADVAPI32$CryptCreateHash(hProv, CALG_SHA_256, 0, 0, &hHash))
    {
        KERNEL32$CloseHandle(hFile);
        ADVAPI32$CryptReleaseContext(hProv, 0);
        BeaconPrintf(CALLBACK_ERROR, "Error: CryptCreateHash failed");
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

    dwBytesRead = sizeof(bSHA256);
    if (ADVAPI32$CryptGetHashParam(hHash, HP_HASHVAL, bSHA256, &dwBytesRead, 0))
    {
        CHAR hash[256] = "";
        for (DWORD i = 0; i < dwBytesRead; i++)
        {
            CHAR digits[3];
            MSVCRT$sprintf(digits, "%02X", bSHA256[i]);
            MSVCRT$strcat(hash, digits);
        }
        BeaconPrintf(CALLBACK_OUTPUT, "SHA-256 Hash for %s: %s", path, hash);
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

    SHA256File(NANO_PATH);
}

#endif
