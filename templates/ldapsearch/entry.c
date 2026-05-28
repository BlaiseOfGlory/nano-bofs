#include <windows.h>
#include <dsgetdc.h>
#include <winldap.h>
#include <winber.h>
#include <rpc.h>
#include <lm.h>
#include <sddl.h>
#include <rpcdce.h>
#include <stdint.h>
#define DYNAMIC_LIB_COUNT 1
#include "bofdefs.h"
#include "base.c"
#define SECURITY_WIN32
#include <secext.h>

#define MAX_ATTRIBUTES 100

static char NANO_QUERY[] = "__NANO_QUERY__";
static char NANO_ATTRIBUTES[] = "__NANO_ATTRIBUTES__";
static char NANO_HOSTNAME[] = "__NANO_HOSTNAME__";
static char NANO_DN[] = "__NANO_DN__";
static const ULONG NANO_COUNT = __NANO_COUNT__;
static const ULONG NANO_SCOPE = __NANO_SCOPE__;
static const ULONG NANO_LDAPS = __NANO_LDAPS__;

typedef long (*_fuuidtostring)(UUID *Uuid, RPC_CSTR *StringUuid);
typedef long (*_RpcStringFreeA)(RPC_CSTR *String);
typedef ULONG LDAPAPI (*_ldap_search_abondon_page)(PLDAP h, PLDAPSearch S);
_fuuidtostring fuuidtostring = (void *)1;
_RpcStringFreeA frpcstringfree = (void *)1;
HMODULE rpcrt = (void *)1;

typedef LDAP *LDAPAPI (*ldap_init_t)(PSTR HostName, ULONG PortNumber);
typedef ULONG LDAPAPI (*ldap_set_optionW_t)(LDAP *ld, int option, const void *invalue);
typedef ULONG LDAPAPI (*ldap_get_optionW_t)(LDAP *ld, int option, void *invalue);
typedef ULONG LDAPAPI (*ldap_bind_s_t)(LDAP *ld, const PSTR dn, const PCHAR cred, ULONG method);
typedef ULONG LDAPAPI (*ldap_unbind_t)(LDAP *);
typedef ULONG LDAPAPI (*ldap_msgfree_t)(LDAPMessage *);
typedef VOID LDAPAPI (*ldap_memfree_t)(PCHAR);
typedef LDAPMessage *(*ldap_first_entry_t)(LDAP *ld, LDAPMessage *res);
typedef ULONG LDAPAPI (*ldap_get_next_page_s_t)(
    PLDAP ExternalHandle,
    PLDAPSearch SearchHandle,
    struct l_timeval *timeout,
    ULONG PageSize,
    ULONG *TotalCount,
    LDAPMessage **Results
);
typedef ULONG LDAPAPI (*ldap_count_entries_t)(LDAP *, LDAPMessage *);
typedef LDAPMessage *(*ldap_next_entry_t)(LDAP *, LDAPMessage *);
typedef PCHAR LDAPAPI (*ldap_first_attribute_t)(LDAP *ld, LDAPMessage *entry, BerElement **ptr);
typedef struct berval **LDAPAPI (*ldap_get_values_lenA_t)(LDAP *ExternalHandle, LDAPMessage *Message, const PCHAR attr);
typedef PCHAR *LDAPAPI (*ldap_get_values_t)(LDAP *ld, LDAPMessage *entry, const PSTR attr);
typedef ULONG LDAPAPI (*ldap_value_free_len_t)(struct berval **vals);
typedef ULONG LDAPAPI (*ldap_value_free_t)(PCHAR *);
typedef PCHAR LDAPAPI (*ldap_next_attribute_t)(LDAP *ld, LDAPMessage *entry, BerElement *ptr);
typedef PLDAPSearch LDAPAPI (*ldap_search_init_pageA_t)(
    PLDAP ExternalHandle,
    const PCHAR DistinguishedName,
    ULONG ScopeOfSearch,
    const PCHAR SearchFilter,
    PCHAR AttributeList[],
    ULONG AttributesOnly,
    PLDAPControlA *ServerControls,
    PLDAPControlA *ClientControls,
    ULONG PageTimeLimit,
    ULONG TotalSizeLimit,
    PLDAPSortKeyA *SortKeys
);
WINBASEAPI void *WINAPI MSVCRT$malloc(SIZE_T);
WINBERAPI BerElement *BERAPI WLDAP32$ber_alloc_t(INT options);
WINBERAPI INT BERAPI WLDAP32$ber_printf(BerElement *pBerElement, PSTR fmt, ...);
WINBERAPI INT BERAPI WLDAP32$ber_flatten(BerElement *pBerElement, PBERVAL *pBerVal);
WINLDAPAPI VOID LDAPAPI WLDAP32$ber_bvfree(PBERVAL bv);

#define WLDAP32$ldap_init ((ldap_init_t)DynamicLoad("WLDAP32", "ldap_init"))
#define WLDAP32$ldap_set_optionW ((ldap_set_optionW_t)DynamicLoad("WLDAP32", "ldap_set_optionW"))
#define WLDAP32$ldap_get_optionW ((ldap_get_optionW_t)DynamicLoad("WLDAP32", "ldap_get_optionW"))
#define WLDAP32$ldap_bind_s ((ldap_bind_s_t)DynamicLoad("WLDAP32", "ldap_bind_s"))
#define WLDAP32$ldap_unbind ((ldap_unbind_t)DynamicLoad("WLDAP32", "ldap_unbind"))
#define WLDAP32$ldap_msgfree ((ldap_msgfree_t)DynamicLoad("WLDAP32", "ldap_msgfree"))
#define WLDAP32$ldap_memfree ((ldap_memfree_t)DynamicLoad("WLDAP32", "ldap_memfree"))
#define WLDAP32$ldap_first_entry ((ldap_first_entry_t)DynamicLoad("WLDAP32", "ldap_first_entry"))
#define WLDAP32$ldap_get_next_page_s ((ldap_get_next_page_s_t)DynamicLoad("WLDAP32", "ldap_get_next_page_s"))
#define WLDAP32$ldap_count_entries ((ldap_count_entries_t)DynamicLoad("WLDAP32", "ldap_count_entries"))
#define WLDAP32$ldap_next_entry ((ldap_next_entry_t)DynamicLoad("WLDAP32", "ldap_next_entry"))
#define WLDAP32$ldap_first_attribute ((ldap_first_attribute_t)DynamicLoad("WLDAP32", "ldap_first_attribute"))
#define WLDAP32$ldap_get_values_lenA ((ldap_get_values_lenA_t)DynamicLoad("WLDAP32", "ldap_get_values_lenA"))
#define WLDAP32$ldap_get_values ((ldap_get_values_t)DynamicLoad("WLDAP32", "ldap_get_values"))
#define WLDAP32$ldap_value_free_len ((ldap_value_free_len_t)DynamicLoad("WLDAP32", "ldap_value_free_len"))
#define WLDAP32$ldap_value_free ((ldap_value_free_t)DynamicLoad("WLDAP32", "ldap_value_free"))
#define WLDAP32$ldap_next_attribute ((ldap_next_attribute_t)DynamicLoad("WLDAP32", "ldap_next_attribute"))
#define WLDAP32$ldap_search_init_pageA ((ldap_search_init_pageA_t)DynamicLoad("WLDAP32", "ldap_search_init_pageA"))

VERIFYSERVERCERT ServerCertCallback;
BOOLEAN _cdecl ServerCertCallback(PLDAP Connection, PCCERT_CONTEXT pServerCert)
{
    (void)Connection;
    (void)pServerCert;
    return TRUE;
}

PLDAPControlA FormatSDFlags(int iFlagValue)
{
    BerElement *pber = NULL;
    PLDAPControl pLControl = NULL;
    PBERVAL pldctrl_value = NULL;
    int success = -1;

    pber = WLDAP32$ber_alloc_t(LBER_USE_DER);
    if (pber == NULL) {
        return NULL;
    }
    pLControl = (PLDAPControl)MSVCRT$malloc(sizeof(LDAPControl));
    if (pLControl == NULL) {
        WLDAP32$ber_free(pber, 1);
        return NULL;
    }
    WLDAP32$ber_printf(pber, "{i}", iFlagValue);

    success = WLDAP32$ber_flatten(pber, &pldctrl_value);
    if (success == 0) {
        WLDAP32$ber_free(pber, 1);
    } else {
        BeaconPrintf(CALLBACK_ERROR, "ber_flatten failed!");
    }
    pLControl->ldctl_oid = "1.2.840.113556.1.4.801";
    pLControl->ldctl_iscritical = TRUE;
    pLControl->ldctl_value.bv_val = (char *)MSVCRT$malloc((size_t)pldctrl_value->bv_len);
    memcpy(pLControl->ldctl_value.bv_val, pldctrl_value->bv_val, pldctrl_value->bv_len);
    pLControl->ldctl_value.bv_len = pldctrl_value->bv_len;

    WLDAP32$ber_bvfree(pldctrl_value);
    return pLControl;
}

static const char basis_64[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

int Base64encode(char *encoded, const char *string, int len)
{
    int i;
    char *p;

    p = encoded;
    for (i = 0; i < len - 2; i += 3) {
        *p++ = basis_64[(string[i] >> 2) & 0x3F];
        *p++ = basis_64[((string[i] & 0x3) << 4) |
                        ((int)(string[i + 1] & 0xF0) >> 4)];
        *p++ = basis_64[((string[i + 1] & 0xF) << 2) |
                        ((int)(string[i + 2] & 0xC0) >> 6)];
        *p++ = basis_64[string[i + 2] & 0x3F];
    }
    if (i < len) {
        *p++ = basis_64[(string[i] >> 2) & 0x3F];
        if (i == (len - 1)) {
            *p++ = basis_64[((string[i] & 0x3) << 4)];
            *p++ = '=';
        } else {
            *p++ = basis_64[((string[i] & 0x3) << 4) |
                            ((int)(string[i + 1] & 0xF0) >> 4)];
            *p++ = basis_64[((string[i + 1] & 0xF) << 2)];
        }
        *p++ = '=';
    }

    *p++ = '\0';
    return (int)(p - encoded);
}

LDAP *InitialiseLDAPConnection(PCHAR hostName, PCHAR distinguishedName, BOOL ldaps)
{
    LDAP *pLdapConnection = NULL;
    ULONG result;
    int portNumber = ldaps == TRUE ? 636 : 389;

    pLdapConnection = WLDAP32$ldap_init(hostName, portNumber);

    if (pLdapConnection == NULL) {
        BeaconPrintf(CALLBACK_ERROR, "[-] Failed to establish LDAP connection on %d.\n", portNumber);
        return NULL;
    }

    ULONG version = LDAP_VERSION3;
    result = WLDAP32$ldap_set_optionW(pLdapConnection, LDAP_OPT_VERSION, (void *)&version);
    if (result != LDAP_SUCCESS) {
        BeaconPrintf(CALLBACK_ERROR, "[-] Failed to set LDAP version: %lu\n", result);
    }

    if (ldaps == TRUE) {
        result = WLDAP32$ldap_set_optionW(pLdapConnection, LDAP_OPT_SSL, LDAP_OPT_ON);
        if (result != LDAP_SUCCESS) {
            BeaconPrintf(CALLBACK_ERROR, "[-] Failed to enable SSL: %lu\n", result);
        }

        result = WLDAP32$ldap_set_optionW(pLdapConnection, LDAP_OPT_SERVER_CERTIFICATE, (void *)&ServerCertCallback);
        if (result != LDAP_SUCCESS) {
            BeaconPrintf(CALLBACK_ERROR, "[-] Failed to set certificate callback: %lu\n", result);
        }
    } else {
        void *value = LDAP_OPT_ON;
        result = WLDAP32$ldap_set_optionW(pLdapConnection, LDAP_OPT_SIGN, &value);
        if (result != LDAP_SUCCESS) {
            internal_printf("[!] Warning: Failed to enable LDAP signing: %lu\n", result);
        }

        result = WLDAP32$ldap_set_optionW(pLdapConnection, LDAP_OPT_ENCRYPT, &value);
        if (result != LDAP_SUCCESS) {
            internal_printf("[!] Warning: Failed to enable LDAP sealing: %lu\n", result);
        }
    }

    ULONG lRtn = 0;
    lRtn = WLDAP32$ldap_bind_s(
        pLdapConnection,
        distinguishedName,
        NULL,
        LDAP_AUTH_NEGOTIATE
    );

    if (lRtn != LDAP_SUCCESS) {
        if (lRtn == LDAP_STRONG_AUTH_REQUIRED) {
            BeaconPrintf(CALLBACK_ERROR, "[-] Bind Failed: Strong authentication required (LDAP signing may be enforced by server)\n");
        } else if (lRtn == LDAP_INVALID_CREDENTIALS) {
            BeaconPrintf(CALLBACK_ERROR, "[-] Bind Failed: Invalid credentials\n");
        } else if (lRtn == LDAP_UNWILLING_TO_PERFORM) {
            BeaconPrintf(CALLBACK_ERROR, "[-] Bind Failed: Server unwilling to perform operation (check security requirements)\n");
        } else {
            BeaconPrintf(CALLBACK_ERROR, "[-] Bind Failed with error: %lu\n", lRtn);
        }
        WLDAP32$ldap_unbind(pLdapConnection);
        pLdapConnection = NULL;
    } else {
        internal_printf(
            "[+] Successfully bound to %s on port %d using %s\n",
            hostName,
            portNumber,
            ldaps ? "LDAPS" : "LDAP"
        );
    }

    return pLdapConnection;
}

PLDAPSearch ExecuteLDAPQuery(LDAP *pLdapConnection, PCHAR distinguishedName, char *ldap_filter, char *ldap_attributes, ULONG maxResults, ULONG scope_of_search)
{
    internal_printf("[*] Filter: %s\n", ldap_filter);
    internal_printf("[*] Scope of search value: %lu\n", scope_of_search);

    int sdFlags = 0x07;
    PLDAPControlA serverControls[2];
    int aclSearch = 0;
    ULONG scope = LDAP_SCOPE_SUBTREE;

    PLDAPSearch pSearchResult = NULL;
    PCHAR attr[MAX_ATTRIBUTES] = {0};
    if (ldap_attributes) {
        internal_printf("[*] Returning specific attribute(s): %s\n", ldap_attributes);

        int attribute_count = 0;
        char *token = NULL;
        const char s[2] = ",";

        token = MSVCRT$strtok(ldap_attributes, s);

        while (token != NULL) {
            if (MSVCRT$_stricmp(token, "nTSecurityDescriptor") == 0) {
                serverControls[0] = FormatSDFlags(sdFlags);
                serverControls[1] = NULL;
                aclSearch = 1;
            }
            if (attribute_count < (MAX_ATTRIBUTES - 1)) {
                attr[attribute_count] = token;
                attribute_count++;
                token = MSVCRT$strtok(NULL, s);
            } else {
                internal_printf("[!] Cannot return more than %i attributes, will omit additional attributes.\n", MAX_ATTRIBUTES);
                break;
            }
        }
    }

    if (scope_of_search == 1) {
        scope = LDAP_SCOPE_BASE;
    } else if (scope_of_search == 2) {
        scope = LDAP_SCOPE_ONELEVEL;
    } else if (scope_of_search == 3) {
        scope = LDAP_SCOPE_SUBTREE;
    }

    if (aclSearch) {
        pSearchResult = WLDAP32$ldap_search_init_pageA(
            pLdapConnection,
            distinguishedName,
            scope,
            ldap_filter,
            (*attr) ? attr : NULL,
            0,
            serverControls,
            NULL,
            15,
            maxResults,
            NULL
        );

        MSVCRT$free(serverControls[0]->ldctl_value.bv_val);
        MSVCRT$free(serverControls[0]);
    } else {
        pSearchResult = WLDAP32$ldap_search_init_pageA(
            pLdapConnection,
            distinguishedName,
            scope,
            ldap_filter,
            (*attr) ? attr : NULL,
            0,
            NULL,
            NULL,
            15,
            maxResults,
            NULL
        );
    }

    if (pSearchResult == NULL) {
        BeaconPrintf(CALLBACK_ERROR, "Paging not supported on this server, aborting");
    }
    return pSearchResult;
}

void customAttributes(PCHAR pAttribute, PCHAR pValue)
{
    if (MSVCRT$strcmp(pAttribute, "objectGUID") == 0) {
        if (fuuidtostring == (void *)1) {
            rpcrt = LoadLibraryA("rpcrt4");
            fuuidtostring = (_fuuidtostring)GetProcAddress(rpcrt, "UuidToStringA");
            frpcstringfree = (_RpcStringFreeA)GetProcAddress(rpcrt, "RpcStringFreeA");
        }
        RPC_CSTR G = NULL;
        PBERVAL tmp = (PBERVAL)pValue;
        fuuidtostring((UUID *)tmp->bv_val, &G);
        internal_printf("%s", G);
        frpcstringfree(&G);
    } else if (MSVCRT$strcmp(pAttribute, "pKIExpirationPeriod") == 0 ||
               MSVCRT$strcmp(pAttribute, "pKIOverlapPeriod") == 0 ||
               MSVCRT$strcmp(pAttribute, "cACertificate") == 0 ||
               MSVCRT$strcmp(pAttribute, "nTSecurityDescriptor") == 0 ||
               MSVCRT$strcmp(pAttribute, "msDS-AllowedToActOnBehalfOfOtherIdentity") == 0 ||
               MSVCRT$strcmp(pAttribute, "msDS-GenerationId") == 0 ||
               MSVCRT$strcmp(pAttribute, "auditingPolicy") == 0 ||
               MSVCRT$strcmp(pAttribute, "dSASignature") == 0 ||
               MSVCRT$strcmp(pAttribute, "mS-DS-CreatorSID") == 0 ||
               MSVCRT$strcmp(pAttribute, "logonHours") == 0 ||
               MSVCRT$strcmp(pAttribute, "schemaIDGUID") == 0 ||
               MSVCRT$strcmp(pAttribute, "mSMQDigests") == 0 ||
               MSVCRT$strcmp(pAttribute, "mSMQSignCertificates") == 0 ||
               MSVCRT$strcmp(pAttribute, "userCertificate") == 0 ||
               MSVCRT$strcmp(pAttribute, "attributeSecurityGUID") == 0 ||
               MSVCRT$strcmp(pAttribute, "dnsRecord") == 0) {
        char *encoded = NULL;
        PBERVAL tmp = (PBERVAL)pValue;
        ULONG len = tmp->bv_len;
        encoded = (char *)MSVCRT$malloc((size_t)len * 2);
        Base64encode(encoded, (char *)tmp->bv_val, (int)len);
        internal_printf("%s", encoded);
        MSVCRT$free(encoded);
    } else if (MSVCRT$strcmp(pAttribute, "objectSid") == 0 || MSVCRT$strcmp(pAttribute, "securityIdentifier") == 0) {
        LPSTR sid = NULL;
        PBERVAL tmp = (PBERVAL)pValue;
        ADVAPI32$ConvertSidToStringSidA((PSID)tmp->bv_val, &sid);
        internal_printf("%s", sid);
        KERNEL32$LocalFree(sid);
    } else {
        internal_printf("%s", pValue);
    }
}

void printAttribute(PCHAR pAttribute, PCHAR *ppValue)
{
    internal_printf("\n%s: ", pAttribute);
    customAttributes(pAttribute, *ppValue);
    ppValue++;
    while (*ppValue != NULL) {
        internal_printf(", ");
        customAttributes(pAttribute, *ppValue);
        ppValue++;
    }
}

void ldapSearch(char *ldap_filter, char *ldap_attributes, ULONG results_count, ULONG scope_of_search, char *hostname, char *domain, BOOL ldaps)
{
    char szDN[1024] = {0};
    ULONG ulSize = sizeof(szDN) / sizeof(szDN[0]);

    BOOL res = (domain) ? TRUE : SECUR32$GetUserNameExA(NameFullyQualifiedDN, szDN, &ulSize);
    DWORD dwRet = 0;
    PDOMAIN_CONTROLLER_INFO pdcInfo = NULL;
    LDAP *pLdapConnection = NULL;
    PLDAPSearch pPageHandle = NULL;
    PLDAPMessage pSearchResult = NULL;
    char *distinguishedName = NULL;
    BerElement *pBer = NULL;
    LDAPMessage *pEntry = NULL;
    LDAP_TIMEVAL timeout = {20, 0};
    ULONG iCnt = 0;
    PCHAR pAttribute = NULL;
    PCHAR *ppValue = NULL;
    BOOL isbinary = FALSE;
    ULONG stat = 0;
    ULONG totalResults = 0;
    HMODULE wldap = LoadLibrary("wldap32");
    if (wldap == NULL) {
        internal_printf("Unable to load required library\n");
        return;
    }
    _ldap_search_abondon_page searchDone = (_ldap_search_abondon_page)GetProcAddress(wldap, "ldap_search_abandon_page");
    if (searchDone == NULL) {
        internal_printf("Unable to load required function");
        return;
    }

    distinguishedName = (domain) ? domain : MSVCRT$strstr(szDN, "DC=");
    if (distinguishedName != NULL && res) {
        internal_printf("[*] Distinguished name: %s\n", distinguishedName);
    } else {
        BeaconPrintf(CALLBACK_ERROR, "Failed to retrieve distinguished name.");
        return;
    }

    dwRet = NETAPI32$DsGetDcNameA(NULL, NULL, NULL, NULL, 0, &pdcInfo);
    if (ERROR_SUCCESS == dwRet || hostname) {
        if (!hostname) {
            internal_printf("[*] targeting DC: %s\n", pdcInfo->DomainControllerName);
        }
    } else {
        BeaconPrintf(CALLBACK_ERROR, "Failed to identify PDC, are we domain joined?");
        goto end;
    }

    char *targetdc = (hostname == NULL) ? pdcInfo->DomainControllerName + 2 : hostname;
    internal_printf("[*] Binding to %s\n", targetdc);
    pLdapConnection = InitialiseLDAPConnection(targetdc, distinguishedName, ldaps);

    if (!pLdapConnection) {
        goto end;
    }

    pPageHandle = ExecuteLDAPQuery(pLdapConnection, distinguishedName, ldap_filter, ldap_attributes, results_count, scope_of_search);
    ULONG pagecount = 0;
    do {
        stat = WLDAP32$ldap_get_next_page_s(
            pLdapConnection,
            pPageHandle,
            &timeout,
            (results_count && ((results_count - totalResults) < 64)) ? results_count - totalResults : 64,
            &pagecount,
            &pSearchResult
        );
        if (!pSearchResult || !(stat == LDAP_SUCCESS || stat == LDAP_NO_RESULTS_RETURNED)) {
            goto end;
        }

        DWORD numberOfEntries = WLDAP32$ldap_count_entries(pLdapConnection, pSearchResult);

        if (numberOfEntries == (DWORD)-1) {
            BeaconPrintf(CALLBACK_ERROR, "Failed to count search results.");
            goto end;
        } else if (!numberOfEntries) {
            BeaconPrintf(CALLBACK_ERROR, "Search returned zero results");
            goto end;
        }

        totalResults += numberOfEntries;

        for (iCnt = 0; iCnt < numberOfEntries; iCnt++) {
            internal_printf("\n--------------------");

            if (!iCnt) {
                pEntry = WLDAP32$ldap_first_entry(pLdapConnection, pSearchResult);
            } else {
                pEntry = WLDAP32$ldap_next_entry(pLdapConnection, pEntry);
            }

            if (pEntry == NULL) {
                break;
            }

            pAttribute = WLDAP32$ldap_first_attribute(
                pLdapConnection,
                pEntry,
                &pBer
            );

            while (pAttribute != NULL) {
                isbinary = FALSE;
                if (MSVCRT$strcmp(pAttribute, "pKIExpirationPeriod") == 0 ||
                    MSVCRT$strcmp(pAttribute, "pKIOverlapPeriod") == 0 ||
                    MSVCRT$strcmp(pAttribute, "cACertificate") == 0 ||
                    MSVCRT$strcmp(pAttribute, "objectSid") == 0 ||
                    MSVCRT$strcmp(pAttribute, "securityIdentifier") == 0 ||
                    MSVCRT$strcmp(pAttribute, "objectGUID") == 0 ||
                    MSVCRT$strcmp(pAttribute, "nTSecurityDescriptor") == 0 ||
                    MSVCRT$strcmp(pAttribute, "msDS-GenerationId") == 0 ||
                    MSVCRT$strcmp(pAttribute, "auditingPolicy") == 0 ||
                    MSVCRT$strcmp(pAttribute, "dSASignature") == 0 ||
                    MSVCRT$strcmp(pAttribute, "mS-DS-CreatorSID") == 0 ||
                    MSVCRT$strcmp(pAttribute, "logonHours") == 0 ||
                    MSVCRT$strcmp(pAttribute, "schemaIDGUID") == 0 ||
                    MSVCRT$strcmp(pAttribute, "msDS-AllowedToActOnBehalfOfOtherIdentity") == 0 ||
                    MSVCRT$strcmp(pAttribute, "msDS-GenerationId") == 0 ||
                    MSVCRT$strcmp(pAttribute, "mSMQDigests") == 0 ||
                    MSVCRT$strcmp(pAttribute, "mSMQSignCertificates") == 0 ||
                    MSVCRT$strcmp(pAttribute, "userCertificate") == 0 ||
                    MSVCRT$strcmp(pAttribute, "attributeSecurityGUID") == 0 ||
                    MSVCRT$strcmp(pAttribute, "dnsRecord") == 0) {
                    ppValue = (char **)WLDAP32$ldap_get_values_lenA(pLdapConnection, pEntry, pAttribute);
                    isbinary = TRUE;
                } else {
                    ppValue = WLDAP32$ldap_get_values(
                        pLdapConnection,
                        pEntry,
                        pAttribute
                    );
                }

                if (ppValue != NULL) {
                    printAttribute(pAttribute, ppValue);
                    if (isbinary) {
                        WLDAP32$ldap_value_free_len((PBERVAL *)ppValue);
                    } else {
                        WLDAP32$ldap_value_free(ppValue);
                    }
                    ppValue = NULL;
                }
                WLDAP32$ldap_memfree(pAttribute);

                pAttribute = WLDAP32$ldap_next_attribute(
                    pLdapConnection,
                    pEntry,
                    pBer
                );
            }

            if (pBer != NULL) {
                WLDAP32$ber_free(pBer, 0);
                pBer = NULL;
            }
        }
        if (totalResults >= results_count && results_count != 0) {
            break;
        }
        WLDAP32$ldap_msgfree(pSearchResult);
        pSearchResult = NULL;
    } while (stat == LDAP_SUCCESS);

end:
    internal_printf("\nretrieved %lu results total\n", totalResults);
    if (pPageHandle) {
        searchDone(pLdapConnection, pPageHandle);
    }
    if (pBer != NULL) {
        WLDAP32$ber_free(pBer, 0);
        pBer = NULL;
    }
    if (pdcInfo) {
        NETAPI32$NetApiBufferFree(pdcInfo);
        pdcInfo = NULL;
    }
    if (pLdapConnection) {
        WLDAP32$ldap_unbind(pLdapConnection);
        pLdapConnection = NULL;
    }
    if (pSearchResult) {
        WLDAP32$ldap_msgfree(pSearchResult);
        pSearchResult = NULL;
    }
    if (ppValue) {
        WLDAP32$ldap_value_free(ppValue);
        ppValue = NULL;
    }
    if (wldap) {
        FreeLibrary(wldap);
        wldap = NULL;
    }
}

VOID go(IN PCHAR Buffer, IN ULONG Length)
{
    char attributes_buffer[sizeof(NANO_ATTRIBUTES)];
    char *ldap_filter = NANO_QUERY;
    char *ldap_attributes = NULL;
    char *hostname = NULL;
    char *domain = NULL;

    (void)Buffer;
    (void)Length;

    if (sizeof(NANO_ATTRIBUTES) > 1) {
        memcpy(attributes_buffer, NANO_ATTRIBUTES, sizeof(NANO_ATTRIBUTES));
        ldap_attributes = attributes_buffer;
    }
    if (sizeof(NANO_HOSTNAME) > 1) {
        hostname = NANO_HOSTNAME;
    }
    if (sizeof(NANO_DN) > 1) {
        domain = NANO_DN;
    }

    if (!bofstart()) {
        return;
    }

    ldapSearch(ldap_filter, ldap_attributes, NANO_COUNT, NANO_SCOPE, hostname, domain, NANO_LDAPS == 1);

    printoutput(TRUE);
    if (fuuidtostring != (void *)1) {
        FreeLibrary(rpcrt);
    }
    bofstop();
}
