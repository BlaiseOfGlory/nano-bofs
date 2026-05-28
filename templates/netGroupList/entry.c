#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include "lm.h"
#include "lmaccess.h"

// Code taken from example code at
// https://docs.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netquerydisplayinformation
void ListDomainGroups(const wchar_t * domain)
{
	PNET_DISPLAY_GROUP pBuff = NULL, p = NULL;
	DWORD res = 0, dwRec = 0, i = 0;

	do
	{
		res = NETAPI32$NetQueryDisplayInformation(domain, 3, i, 100, MAX_PREFERRED_LENGTH, &dwRec, (PVOID*) &pBuff);
		if((res==ERROR_SUCCESS) || (res==ERROR_MORE_DATA) && dwRec != 0 && pBuff != NULL)
		{
			p = pBuff;
			for(;dwRec>0;dwRec--)
			{
				internal_printf("Name:      %S\n"
				"Comment:   %S\n"
				"Group ID:  %lu\n"
				"Attributes: %lu\n"
				"--------------------------------\n",
				p->grpi3_name,
				p->grpi3_comment,
				p->grpi3_group_id,
				p->grpi3_attributes);
				i = p->grpi3_next_index;
				p++;
			}
			NETAPI32$NetApiBufferFree(pBuff);
			pBuff = NULL;
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

	static const wchar_t NANO_DOMAIN[] = L"__NANO_DOMAIN__";
	const wchar_t * domain = NANO_DOMAIN;
	wchar_t default_domain[256] = {0};
	DWORD dwDefaultSize = 256;

	if(!bofstart())
	{
		return;
	}

	// Preserve the original target-side default-domain fallback while
	// removing command argument parsing from the BOF.
	if(*domain == 0)
	{
		if(KERNEL32$GetComputerNameExW(ComputerNameDnsDomain, (LPWSTR)&default_domain, &dwDefaultSize) == 0)
		{
			BeaconPrintf(CALLBACK_ERROR, "Warning, could not get default domain name, continuing against local system");
			domain = NULL;
		}
		else
		{
			BeaconPrintf(CALLBACK_OUTPUT, "Using Resolved domain of %S", default_domain);
			domain = default_domain;
		}
	}

	ListDomainGroups(domain);
	printoutput(TRUE);
};

#endif
