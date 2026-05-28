#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include "lm.h"
#include "lmaccess.h"

// Code taken from example code at
// https://docs.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netquerydisplayinformation
void ListserverGroups(const wchar_t * server)
{
	PLOCALGROUP_INFO_1 pBuff = NULL, p = NULL;
	DWORD res = 0, dwRec = 0, dwTotal = 0;
	DWORD_PTR hResume = 0;
	do
	{
		res = NETAPI32$NetLocalGroupEnum(server, 1, (LPBYTE *)&pBuff, MAX_PREFERRED_LENGTH, &dwRec, &dwTotal, &hResume);
		if((res==ERROR_SUCCESS) || (res==ERROR_MORE_DATA))
		{
			p = pBuff;
			for(;dwRec>0;dwRec--)
			{
				internal_printf("Name:      %S\n"
				"Comment:   %S\n"
				"--------------------------------\n",
				p->lgrpi1_name,
				p->lgrpi1_comment);
				p++;
			}
			NETAPI32$NetApiBufferFree(pBuff);
		}
		else
		{
			BeaconPrintf(CALLBACK_ERROR, "Error: %lu\n", res);
		}
	} while (res==ERROR_MORE_DATA);
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
	const wchar_t * server = NANO_SERVER;

	if(!bofstart())
	{
		return;
	}

	if(*server == 0)
	{
		server = NULL;
	}

	ListserverGroups(server);
	printoutput(TRUE);
};

#endif
