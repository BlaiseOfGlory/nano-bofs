#include <windows.h>
#include <stdio.h>
#include "beacon.h"
#include "bofdefs.h"
#include "base.c"
#include "wmi.c"

static HRESULT wmi_query_run(
    LPWSTR pwszServer,
    LPWSTR pwszNameSpace,
    LPWSTR pwszQuery,
    LPWSTR pwszResource
)
{
    HRESULT hr = S_OK;
    WMI m_WMI;
    BSTR** ppbstrResults = NULL;
    DWORD dwRowCount = 0;
    DWORD dwColumnCount = 0;
    DWORD dwCurrentRowIndex = 0;
    DWORD dwCurrentColumnIndex = 0;

    hr = Wmi_Initialize(&m_WMI);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_Initialize failed: 0x%08lx", hr);
        goto fail;
    }

    hr = Wmi_Connect(&m_WMI, pwszResource);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_Connect failed: 0x%08lx", hr);
        goto fail;
    }

    hr = Wmi_Query(&m_WMI, pwszQuery);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_Query failed: 0x%08lx", hr);
        goto fail;
    }

    hr = Wmi_ParseAllResults(&m_WMI, &ppbstrResults, &dwRowCount, &dwColumnCount);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_ParseAllResults failed: 0x%08lx", hr);
        goto fail;
    }

    for (dwCurrentRowIndex = 0; dwCurrentRowIndex < dwRowCount; dwCurrentRowIndex++)
    {
        for (dwCurrentColumnIndex = 0; dwCurrentColumnIndex < dwColumnCount; dwCurrentColumnIndex++)
        {
            if (0 == dwCurrentColumnIndex)
            {
                internal_printf("%S", ppbstrResults[dwCurrentRowIndex][dwCurrentColumnIndex]);
            }
            else
            {
                internal_printf(", %S", ppbstrResults[dwCurrentRowIndex][dwCurrentColumnIndex]);
            }
        }
        internal_printf("\n");
    }

    hr = S_OK;

fail:
    for (dwCurrentRowIndex = 0; dwCurrentRowIndex < dwRowCount; dwCurrentRowIndex++)
    {
        for (dwCurrentColumnIndex = 0; dwCurrentColumnIndex < dwColumnCount; dwCurrentColumnIndex++)
        {
            SAFE_FREE(ppbstrResults[dwCurrentRowIndex][dwCurrentColumnIndex]);
        }
        KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, ppbstrResults[dwCurrentRowIndex]);
    }

    if (ppbstrResults)
    {
        KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, ppbstrResults);
        ppbstrResults = NULL;
    }

    Wmi_Finalize(&m_WMI);
    return hr;
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
    static const wchar_t NANO_NAMESPACE[] = L"__NANO_NAMESPACE__";
    static const wchar_t NANO_QUERY[] = L"__NANO_QUERY__";
    static const wchar_t NANO_RESOURCE[] = L"__NANO_RESOURCE__";

    HRESULT hr = S_OK;

    if (!bofstart())
    {
        return;
    }

    hr = wmi_query_run(
        (LPWSTR)NANO_SERVER,
        (LPWSTR)NANO_NAMESPACE,
        (LPWSTR)NANO_QUERY,
        (LPWSTR)NANO_RESOURCE
    );
    if (S_OK != hr)
    {
        BeaconPrintf(CALLBACK_ERROR, "wmi_query failed: 0x%08lx", hr);
    }

    printoutput(TRUE);
}
#endif
