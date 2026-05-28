#include <windows.h>
#include <stdio.h>
#define DYNAMIC_LIB_COUNT 2
#include "beacon.h"
#include "bofdefs.h"
#include "base.c"
#include "adcs_enum.c"

#ifdef BOF
VOID go(
	IN PCHAR Buffer,
	IN ULONG Length
)
{
	HRESULT hr = S_OK;
	static const wchar_t NANO_DOMAIN[] = L"__NANO_DOMAIN__";
	static const int NANO_USE_CURRENT_DOMAIN = __NANO_USE_CURRENT_DOMAIN__;
	DWORD domainlen = MAX_PATH;
	wchar_t domainarg[MAX_PATH];
	wchar_t *domain = NULL;
    
	if (!bofstart())
	{
		return;
	}

	(void)Buffer;
	(void)Length;
	if (!NANO_USE_CURRENT_DOMAIN)
	{
		memset(domainarg, 0, sizeof(domainarg));
		for (SIZE_T i = 0; i < (MAX_PATH - 1) && NANO_DOMAIN[i] != L'\0'; i++)
		{
			domainarg[i] = NANO_DOMAIN[i];
		}
		domain = domainarg;
	}
	else
	{
		memset(domainarg, 0, sizeof(domainarg));
		if (KERNEL32$GetComputerNameExW(ComputerNameDnsDomain, domainarg, &domainlen))
		{
			domain = domainarg;
		}
		else
		{
			BeaconPrintf(CALLBACK_ERROR, "GetComputerNameExW(ComputerNameDnsDomain) failed: %lu\n", KERNEL32$GetLastError());
			printoutput(TRUE);
			return;
		}
	}
	hr = adcs_enum(domain);

	if (S_OK != hr)
	{
		BeaconPrintf(CALLBACK_ERROR, "adcs_enum failed: 0x%08lx\n", hr);
	}
	else
	{
		internal_printf("\nadcs_enum SUCCESS.\n");
	}

	printoutput(TRUE);
};
#else
int main(int argc, char ** argv)
{
	HRESULT hr = S_OK;
	DWORD domainlen = MAX_PATH;
	wchar_t domainarg[MAX_PATH];
	wchar_t* domain = NULL;

	if (argc==2)
	{
		memset(domainarg, 0, sizeof(wchar_t)*MAX_PATH);
		mbstowcs(domainarg, argv[1], MAX_PATH);
		domain = domainarg;
	}
	else
	{
		memset(domainarg, 0, sizeof(wchar_t)*MAX_PATH);
		if (GetComputerNameExW(ComputerNameDnsDomain, domainarg, &domainlen))
		{
			domain = domainarg;
		}
		else
		{
			fprintf(stderr, "GetComputerNameExW(ComputerNameDnsDomain) failed: %lu\n", GetLastError());
			return 1;
		}
	}

	hr = adcs_enum(domain);

	if (S_OK != hr)
	{
		BeaconPrintf(CALLBACK_ERROR, "adcs_enum failed: 0x%08lx\n", hr);
	}
	else
	{
		internal_printf("\nadcs_enum SUCCESS.\n");
	}

	return 0;
}
#endif

	
