#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include "lm.h"

void ListServerGroupMembers(const wchar_t *server, const wchar_t *groupname)
{
    PLOCALGROUP_MEMBERS_INFO_3 pBuff = NULL, p = NULL;
    DWORD dwTotal = 0, dwRead = 0, i = 0;
    DWORD_PTR hResume = 0;
    NET_API_STATUS res = 0;
    do
    {
        res = NETAPI32$NetLocalGroupGetMembers(server, groupname, 3, (LPBYTE *)&pBuff, MAX_PREFERRED_LENGTH, &dwRead, &dwTotal, &hResume);
        if((res == ERROR_SUCCESS) || (res == ERROR_MORE_DATA))
        {
            p = pBuff;
            for(i = 0; i < dwRead; i++)
            {
                internal_printf("%S\n", p->lgrmi3_domainandname);
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

    static const wchar_t NANO_SERVER[] = L"__NANO_SERVER__";
    static const wchar_t NANO_GROUP[] = L"__NANO_GROUP__";
    wchar_t server_buffer[256] = {0};
    wchar_t group_buffer[256] = {0};
    const wchar_t *server = server_buffer;
    const wchar_t *group = group_buffer;

    if(!bofstart())
    {
        return;
    }

    for(int i = 0; i < 255; i++)
    {
        server_buffer[i] = NANO_SERVER[i];
        if(NANO_SERVER[i] == 0)
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

    server = (*server == 0) ? NULL : server;
    group = (*group == 0) ? NULL : group;

    ListServerGroupMembers(server, group);
    printoutput(TRUE);
}

#endif
