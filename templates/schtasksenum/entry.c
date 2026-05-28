#define _WIN32_DCOM
#include <windows.h>
#include <taskschd.h>
#include "bofdefs.h"
#include "base.c"
#include "queue.c"

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

static const wchar_t *safe_bstr(BSTR value)
{
    return value != NULL ? value : L"";
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

static void enumerate_tasks(const wchar_t *server)
{
    HRESULT hr = OLE32$CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE)
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not initialize COM");
        return;
    }

    Pqueue queue = queueInit();
    if (queue == NULL)
    {
        BeaconPrintf(CALLBACK_ERROR, "Could not initialize task folder queue");
        OLE32$CoUninitialize();
        return;
    }

    VARIANT server_variant;
    VARIANT null_variant;
    VARIANT index_variant;
    BSTR rootpath = NULL;
    ITaskService *service = NULL;
    ITaskFolder *current_folder = NULL;
    ITaskFolderCollection *subfolders = NULL;
    ITaskFolder *subfolder = NULL;
    IRegisteredTaskCollection *task_collection = NULL;
    long count = 0;
    long task_number = 0;
    IID clsid_task_scheduler = {0x0f87369f, 0xa4e5, 0x4cfc, {0xbd, 0x3e, 0x73, 0xe6, 0x15, 0x45, 0x72, 0xdd}};
    IID iid_task_service = {0x2faba4c7, 0x4da9, 0x4013, {0x96, 0x97, 0x20, 0xcc, 0x3f, 0xd4, 0x0f, 0x85}};

    OLEAUT32$VariantInit(&server_variant);
    OLEAUT32$VariantInit(&null_variant);
    OLEAUT32$VariantInit(&index_variant);
    index_variant.vt = VT_I4;

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
        BeaconPrintf(CALLBACK_ERROR, "Failed to initialize Task Scheduler interface: %lx", hr);
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

    hr = service->lpVtbl->GetFolder(service, rootpath, &current_folder);
    if (FAILED(hr))
    {
        BeaconPrintf(CALLBACK_ERROR, "Cannot get root folder pointer: %lx", hr);
        goto cleanup;
    }

    do
    {
        if (SUCCEEDED(current_folder->lpVtbl->GetFolders(current_folder, 0, &subfolders)) &&
            SUCCEEDED(subfolders->lpVtbl->get_Count(subfolders, &count)))
        {
            for (long i = 1; i <= count; i++)
            {
                index_variant.lVal = i;
                hr = subfolders->lpVtbl->get_Item(subfolders, index_variant, &subfolder);
                if (SUCCEEDED(hr) && subfolder != NULL)
                {
                    queue->push(queue, subfolder);
                    subfolder = NULL;
                }
            }
        }

        hr = current_folder->lpVtbl->GetTasks(current_folder, TASK_ENUM_HIDDEN, &task_collection);
        if (FAILED(hr))
        {
            BSTR folder_name = NULL;
            current_folder->lpVtbl->get_Name(current_folder, &folder_name);
            BeaconPrintf(CALLBACK_ERROR, "Failed to get tasks for folder %S: %lx", safe_bstr(folder_name), hr);
            if (folder_name != NULL)
            {
                OLEAUT32$SysFreeString(folder_name);
            }
            goto next_folder;
        }

        if (FAILED(task_collection->lpVtbl->get_Count(task_collection, &count)))
        {
            goto next_folder;
        }

        for (long i = 1; i <= count; i++)
        {
            IRegisteredTask *task = NULL;
            BSTR value = NULL;
            VARIANT_BOOL enabled = 0;
            TASK_STATE state = TASK_STATE_UNKNOWN;

            index_variant.lVal = i;
            hr = task_collection->lpVtbl->get_Item(task_collection, index_variant, &task);
            if (FAILED(hr) || task == NULL)
            {
                continue;
            }

            internal_printf("Task %ld\n", ++task_number);

            if (SUCCEEDED(task->lpVtbl->get_Name(task, &value)))
            {
                internal_printf("Name: %S\n", safe_bstr(value));
                OLEAUT32$SysFreeString(value);
                value = NULL;
            }

            if (SUCCEEDED(task->lpVtbl->get_Path(task, &value)))
            {
                internal_printf("Path: %S\n", safe_bstr(value));
                OLEAUT32$SysFreeString(value);
                value = NULL;
            }

            if (SUCCEEDED(task->lpVtbl->get_Enabled(task, &enabled)))
            {
                internal_printf("Enabled: %s\n", enabled == VARIANT_TRUE ? "True" : "False");
            }
            else
            {
                internal_printf("Enabled: (unavailable)\n");
            }

            print_task_time(task, task->lpVtbl->get_LastRunTime, "Last Run");
            print_task_time(task, task->lpVtbl->get_NextRunTime, "Next Run");

            if (SUCCEEDED(task->lpVtbl->get_State(task, &state)))
            {
                internal_printf("Current State: %s\n", task_state_string(state));
            }
            else
            {
                internal_printf("Current State: (unavailable)\n");
            }

            if (SUCCEEDED(task->lpVtbl->get_Xml(task, &value)))
            {
                internal_printf("%S\n", safe_bstr(value));
                OLEAUT32$SysFreeString(value);
            }
            else
            {
                internal_printf("Failed to get xml for this task\n");
            }

            internal_printf("--------------------------------\n");
            task->lpVtbl->Release(task);
        }

    next_folder:
        if (subfolder != NULL)
        {
            subfolder->lpVtbl->Release(subfolder);
            subfolder = NULL;
        }
        if (subfolders != NULL)
        {
            subfolders->lpVtbl->Release(subfolders);
            subfolders = NULL;
        }
        if (task_collection != NULL)
        {
            task_collection->lpVtbl->Release(task_collection);
            task_collection = NULL;
        }
        if (current_folder != NULL)
        {
            current_folder->lpVtbl->Release(current_folder);
            current_folder = NULL;
        }
    } while ((current_folder = queue->pop(queue)) != NULL);

cleanup:
    if (subfolder != NULL)
    {
        subfolder->lpVtbl->Release(subfolder);
    }
    if (subfolders != NULL)
    {
        subfolders->lpVtbl->Release(subfolders);
    }
    if (task_collection != NULL)
    {
        task_collection->lpVtbl->Release(task_collection);
    }
    if (current_folder != NULL)
    {
        current_folder->lpVtbl->Release(current_folder);
    }
    if (service != NULL)
    {
        service->lpVtbl->Release(service);
    }
    if (rootpath != NULL)
    {
        OLEAUT32$SysFreeString(rootpath);
    }
    OLEAUT32$VariantClear(&server_variant);
    queue->free(queue);
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

    if (!bofstart())
    {
        return;
    }

    enumerate_tasks(NANO_SERVER);
    printoutput(TRUE);
}
#endif
