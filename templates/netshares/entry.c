#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include <lm.h>

void listSharesUser(wchar_t *servername)
{
    PSHARE_INFO_1 output = NULL;
    PSHARE_INFO_1 current = NULL;
    DWORD entries = 0;
    DWORD totalentrieshint = 0;
    DWORD resume = 0;
    NET_API_STATUS stat = 0;

    internal_printf("Share:              Remark:\n");
    internal_printf("---------------------%S----------------------------------\n", servername == NULL ? L"(Local)" : servername);

    do
    {
        stat = NETAPI32$NetShareEnum(servername, 1, (LPBYTE *)&output, MAX_PREFERRED_LENGTH, &entries, &totalentrieshint, &resume);
        if (stat == ERROR_SUCCESS || stat == ERROR_MORE_DATA)
        {
            current = output;
            for (DWORD pos = 0; pos < entries; pos++)
            {
                internal_printf("%-20S%S\n", current->shi1_netname, current->shi1_remark);
                current++;
            }
        }
        else
        {
            internal_printf("Unable to list share: %lu\n", stat);
        }

        NETAPI32$NetApiBufferFree(output);
        output = NULL;
    } while (stat == ERROR_MORE_DATA);
}

void listSharesAdmin(wchar_t *servername)
{
    PSHARE_INFO_2 output = NULL;
    PSHARE_INFO_2 current = NULL;
    DWORD entries = 0;
    DWORD totalentrieshint = 0;
    DWORD resume = 0;
    NET_API_STATUS stat = 0;

    internal_printf("Share:              Local Path:                   Uses:   Descriptor:\n");
    internal_printf("---------------------%S----------------------------------\n", servername == NULL ? L"(Local)" : servername);

    do
    {
        stat = NETAPI32$NetShareEnum(servername, 2, (LPBYTE *)&output, MAX_PREFERRED_LENGTH, &entries, &totalentrieshint, &resume);
        if (stat == ERROR_SUCCESS || stat == ERROR_MORE_DATA)
        {
            current = output;
            for (DWORD pos = 0; pos < entries; pos++)
            {
                internal_printf("%-20S%-30S%-8lu %S\n", current->shi2_netname, current->shi2_path, current->shi2_current_uses, current->shi2_remark);
                current++;
            }
        }
        else
        {
            internal_printf("Unable to list share: %lu\n", stat);
        }

        NETAPI32$NetApiBufferFree(output);
        output = NULL;
    } while (stat == ERROR_MORE_DATA);
}


#ifdef BOF

VOID go(
    IN PCHAR Buffer,
    IN ULONG Length
)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_SERVER[] = L"__NANO_SERVER__";
    static const int NANO_LEVEL = __NANO_LEVEL__;
    wchar_t *servername = (wchar_t *)NANO_SERVER;

    if (*servername == 0)
    {
        servername = NULL;
    }
    if (!bofstart())
    {
        return;
    }

    if (NANO_LEVEL == 2)
    {
        listSharesAdmin(servername);
    }
    else
    {
        listSharesUser(servername);
    }
    printoutput(TRUE);
};

#endif
