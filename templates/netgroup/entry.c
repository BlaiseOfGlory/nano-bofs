#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include "lm.h"

void ListGlobalGroupMembers(const wchar_t * domain, const wchar_t * groupname)
{
    PGROUP_USERS_INFO_0 pBuff = NULL, p = NULL;
    DWORD dwTotal = 0, dwRead = 0, i = 0;
    DWORD_PTR hResume = 0;
    NET_API_STATUS res = 0;
    do
    {
        res = NETAPI32$NetGroupGetUsers(domain, groupname, 0, (LPBYTE *)&pBuff, MAX_PREFERRED_LENGTH, &dwRead, &dwTotal, &hResume);
        if((res==ERROR_SUCCESS) || (res==ERROR_MORE_DATA))
        {
            p = pBuff;
            for(i = 0; i < dwRead; i++)
            {
                internal_printf("%S\n", p->grui0_name);
                p++;
            }
        }
        else
        {
            BeaconPrintf(CALLBACK_ERROR, "Error: %lu\n", res);
        }

        NETAPI32$NetApiBufferFree(pBuff);
        pBuff = NULL;
    } while(res == ERROR_MORE_DATA);
}

#ifdef BOF

VOID go(
    IN PCHAR Buffer,
    IN ULONG Length
)
{
    (void)Buffer;
    (void)Length;

    static const wchar_t NANO_DOMAIN[] = L"__NANO_DOMAIN__";
    static const wchar_t NANO_GROUP[] = L"__NANO_GROUP__";
    wchar_t domain_buffer[256] = {0};
    wchar_t group_buffer[256] = {0};
    wchar_t default_domain[256] = {0};
    DWORD dwDefaultSize = 256;
    const wchar_t * domain = domain_buffer;
    const wchar_t * group = group_buffer;

    if(!bofstart())
    {
        return;
    }

    for(int i = 0; i < 255; i++)
    {
        domain_buffer[i] = NANO_DOMAIN[i];
        if(NANO_DOMAIN[i] == 0)
        {
            break;
        }
    }

    for(int i = 0; i < 255; i++)
    {
        group_buffer[i] = NANO_GROUP[i];
        if(NANO_GROUP[i] == 0)
        {
            break;
        }
    }

    if(*domain == 0)
    {
        if(KERNEL32$GetComputerNameExW(ComputerNameDnsDomain, (LPWSTR)&default_domain, &dwDefaultSize) == 0)
        {
            domain = NULL;
        }
        else
        {
            domain = default_domain;
        }
    }

    ListGlobalGroupMembers(domain, group);
    printoutput(TRUE);
}

#endif
