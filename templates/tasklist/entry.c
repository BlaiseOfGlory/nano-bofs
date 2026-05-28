#include <windows.h>
#include "bofdefs.h"
#include "base.c"
#include "wmi.c"

#define WMI_QUERY_PROCESSES         L"SELECT * FROM Win32_Process"
#define WMI_KEYS_PROCESSES          L"Name,ProcessId,ParentProcessId,SessionId,CommandLine"
#define RESULTS_OUTPUT_FORMAT       "%-32S %10S %16S %10S %-80S\n"
#define RESULTS_NAME_COL            0
#define RESULTS_PROCESSID_COL       1
#define RESULTS_PARENTPROCESSID_COL 2
#define RESULTS_SESSIONID_COL       3
#define RESULTS_COMMANDLINE_COL     4

static HRESULT task_list(LPWSTR resource)
{
    HRESULT hr = S_OK;
    WMI wmi;
    BSTR **results = NULL;
    DWORD row_count = 0;
    DWORD column_count = 0;
    DWORD row_index = 0;
    DWORD column_index = 0;

    hr = Wmi_Initialize(&wmi);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_Initialize failed: 0x%08lx", hr);
        goto cleanup;
    }

    hr = Wmi_Connect(&wmi, resource);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_Connect failed: 0x%08lx", hr);
        goto cleanup;
    }

    hr = Wmi_Query(&wmi, WMI_QUERY_PROCESSES);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_Query failed: 0x%08lx", hr);
        goto cleanup;
    }

    hr = Wmi_ParseResults(&wmi, WMI_KEYS_PROCESSES, &results, &row_count, &column_count);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Wmi_ParseResults failed: 0x%08lx", hr);
        goto cleanup;
    }

    for (row_index = 0; row_index < row_count; row_index++)
    {
        internal_printf(
            RESULTS_OUTPUT_FORMAT,
            results[row_index][RESULTS_NAME_COL],
            results[row_index][RESULTS_PROCESSID_COL],
            results[row_index][RESULTS_PARENTPROCESSID_COL],
            results[row_index][RESULTS_SESSIONID_COL],
            results[row_index][RESULTS_COMMANDLINE_COL]
        );
    }

cleanup:
    for (row_index = 0; row_index < row_count; row_index++)
    {
        for (column_index = 0; column_index < column_count; column_index++)
        {
            SAFE_FREE(results[row_index][column_index]);
        }
        KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, results[row_index]);
    }
    if (results != NULL)
    {
        KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, results);
    }

    Wmi_Finalize(&wmi);
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

    static wchar_t NANO_RESOURCE[] = L"__NANO_RESOURCE__";
    HRESULT hr = S_OK;

    if (!bofstart())
    {
        return;
    }

    hr = task_list(NANO_RESOURCE);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "task_list failed: 0x%08lx", hr);
    }

    printoutput(TRUE);
}
#endif
