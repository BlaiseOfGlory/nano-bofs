#define _WIN32_DCOM
#include <windows.h>
#include <string.h>
#include <taskschd.h>
#include "bofdefs.h"
#include "base.c"

static const char *task_state_string(TASK_STATE state)
{
    switch (state)
    {
    case TASK_STATE_DISABLED:
        return "DISABLED";
    case TASK_STATE_QUEUED:
        return "QUEUED";
    case TASK_STATE_READY:
        return "READY";
    case TASK_STATE_RUNNING:
        return "RUNNING";
    case TASK_STATE_UNKNOWN:
    default:
        return "UNKNOWN";
    }
}

static void print_task_time(IRegisteredTask *task, HRESULT(__stdcall *getter)(IRegisteredTask *, DATE *), const char *label)
{
    VARIANT date_value;
    BSTR formatted = NULL;

    OLEAUT32$VariantInit(&date_value);
    date_value.vt = VT_DATE;

    if (FAILED(getter(task, &date_value.date)))
    {
        internal_printf("%s: (unavailable)\n", label);
        return;
    }

    OLEAUT32$VarFormatDateTime(&date_value, 0, 0, &formatted);
    if (formatted != NULL)
    {
        internal_printf("%s: %S\n", label, formatted);
        OLEAUT32$SysFreeString(formatted);
        return;
    }

    internal_printf("%s: (unavailable)\n", label);
}

static void query_task(const wchar_t *server, const wchar_t *taskpath)
{
    HRESULT hr = OLE32$CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not initialize COM");
        return;
    }

    VARIANT server_variant;
    VARIANT null_variant;
    VARIANT date_variant;
    BSTR rootpath = NULL;
    BSTR full_task_path = NULL;
    ITaskService *service = NULL;
    ITaskFolder *root_folder = NULL;
    IRegisteredTask *registered_task = NULL;
    VARIANT_BOOL enabled = VARIANT_FALSE;
    TASK_STATE state = TASK_STATE_UNKNOWN;
    BSTR value = NULL;
    IID clsid_task_scheduler = {0x0f87369f, 0xa4e5, 0x4cfc, {0xbd, 0x3e, 0x73, 0xe6, 0x15, 0x45, 0x72, 0xdd}};
    IID iid_task_service = {0x2faba4c7, 0x4da9, 0x4013, {0x96, 0x97, 0x20, 0xcc, 0x3f, 0xd4, 0x0f, 0x85}};

    OLEAUT32$VariantInit(&server_variant);
    OLEAUT32$VariantInit(&null_variant);
    OLEAUT32$VariantInit(&date_variant);
    date_variant.vt = VT_DATE;

    server_variant.vt = VT_BSTR;
    server_variant.bstrVal = OLEAUT32$SysAllocString(server);
    if (server_variant.bstrVal == NULL && server[0] != L'\0')
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not allocate target server string");
        goto cleanup;
    }

    hr = OLE32$CoCreateInstance(
        &clsid_task_scheduler,
        NULL,
        CLSCTX_INPROC_SERVER,
        &iid_task_service,
        (void **)&service);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Failed to initialize Task Scheduler interface");
        goto cleanup;
    }

    hr = service->lpVtbl->Connect(service, server_variant, null_variant, null_variant, null_variant);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not connect to requested target %lx", hr);
        goto cleanup;
    }

    rootpath = OLEAUT32$SysAllocString(L"\\");
    if (rootpath == NULL)
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not allocate root task path");
        goto cleanup;
    }

    hr = service->lpVtbl->GetFolder(service, rootpath, &root_folder);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Cannot get Root Folder pointer: %lx", hr);
        goto cleanup;
    }

    full_task_path = OLEAUT32$SysAllocString(taskpath);
    if (full_task_path == NULL)
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not allocate task path");
        goto cleanup;
    }

    hr = root_folder->lpVtbl->GetTask(root_folder, full_task_path, &registered_task);
    if (FAILED(hr) || registered_task == NULL)
    {
        internal_printf("Could not find a task at given path of %S\n", full_task_path);
        internal_printf("When using query you must give the full path and name of the task you are looking for\n");
        goto cleanup;
    }

    if (SUCCEEDED(registered_task->lpVtbl->get_Name(registered_task, &value)))
    {
        internal_printf("Name: %S\n", value);
        OLEAUT32$SysFreeString(value);
        value = NULL;
    }

    if (SUCCEEDED(registered_task->lpVtbl->get_Path(registered_task, &value)))
    {
        internal_printf("Path: %S\n", value);
        OLEAUT32$SysFreeString(value);
        value = NULL;
    }

    if (SUCCEEDED(registered_task->lpVtbl->get_Enabled(registered_task, &enabled)))
    {
        internal_printf("Enabled: %s\n", enabled == VARIANT_TRUE ? "True" : "False");
    }
    else
    {
        internal_printf("Enabled: (unavailable)\n");
    }

    print_task_time(registered_task, registered_task->lpVtbl->get_LastRunTime, "Last Run");
    print_task_time(registered_task, registered_task->lpVtbl->get_NextRunTime, "Next Run");

    if (SUCCEEDED(registered_task->lpVtbl->get_State(registered_task, &state)))
    {
        internal_printf("Current State: %s\n", task_state_string(state));
    }
    else
    {
        internal_printf("Current State: (unavailable)\n");
    }

    if (server[0] != L'\0')
    {
        printoutput(FALSE);
    }

    if (SUCCEEDED(registered_task->lpVtbl->get_Xml(registered_task, &value)))
    {
        internal_printf("%S\n", value);
        OLEAUT32$SysFreeString(value);
        value = NULL;
    }
    else
    {
        internal_printf("Failed to get xml for this task\n");
    }

    internal_printf("--------------------------------\n");

cleanup:
    if (value != NULL)
    {
        OLEAUT32$SysFreeString(value);
    }
    if (registered_task != NULL)
    {
        registered_task->lpVtbl->Release(registered_task);
    }
    if (root_folder != NULL)
    {
        root_folder->lpVtbl->Release(root_folder);
    }
    if (service != NULL)
    {
        service->lpVtbl->Release(service);
    }
    if (full_task_path != NULL)
    {
        OLEAUT32$SysFreeString(full_task_path);
    }
    if (rootpath != NULL)
    {
        OLEAUT32$SysFreeString(rootpath);
    }
    OLEAUT32$VariantClear(&server_variant);
    OLE32$CoUninitialize();
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
    static const wchar_t NANO_TASKPATH[] = L"__NANO_TASKPATH__";
    wchar_t server_buffer[sizeof(NANO_SERVER) / sizeof(NANO_SERVER[0])];
    wchar_t taskpath_buffer[sizeof(NANO_TASKPATH) / sizeof(NANO_TASKPATH[0])];

    memcpy(server_buffer, NANO_SERVER, sizeof(NANO_SERVER));
    memcpy(taskpath_buffer, NANO_TASKPATH, sizeof(NANO_TASKPATH));

    if (!bofstart())
    {
        return;
    }

    query_task(server_buffer, taskpath_buffer);
    printoutput(TRUE);
}
#endif
