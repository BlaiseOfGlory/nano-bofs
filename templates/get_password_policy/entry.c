#include <windows.h>
#include <lm.h>
#include "bofdefs.h"
#include "base.c"

void get_password_policy(const wchar_t * serverName)
{
   USER_MODALS_INFO_0 *pBuf = NULL;
   NET_API_STATUS nStatus;
   DWORD result = 0;

   nStatus = NETAPI32$NetUserModalsGet((LPCWSTR) serverName, 0, (LPBYTE *)&pBuf);
   if (nStatus == NERR_Success)
   {
      if (pBuf != NULL)
      {
         internal_printf("Minimum password length:  %lu\n", pBuf->usrmod0_min_passwd_len);
         result = pBuf->usrmod0_max_passwd_age / 86400;
         if (result > 1000)
         {
            internal_printf("Maximum password age (days): Unlimited\n");
         }
         else
         {
            internal_printf("Maximum password age (days): %lu\n", result);
         }
         internal_printf("Minimum password age (days): %d\n", pBuf->usrmod0_min_passwd_age / 86400);
         if (pBuf->usrmod0_force_logoff == UINT_MAX)
         {
            internal_printf("Forced log off time (seconds):  Never\n");
         }
         else
         {
            internal_printf("Forced log off time (seconds):  %lu\n", pBuf->usrmod0_force_logoff);
         }
         if (pBuf->usrmod0_password_hist_len == 0)
         {
            internal_printf("Password history length:  None\n");
         }
         else
         {
            internal_printf("Password history length:  %lu\n", pBuf->usrmod0_password_hist_len);
         }
         NETAPI32$NetApiBufferFree(pBuf);
         pBuf = NULL;
      }
      else
      {
         internal_printf("somehow call worked but we didn't get memory? (BROKEN)");
      }
   }
   else
   {
      internal_printf("A system error has occurred(modal 0): %d\n", nStatus);
      goto end;
   }

   nStatus = NETAPI32$NetUserModalsGet((LPCWSTR) serverName, 3, (LPBYTE *)&pBuf);
   if (nStatus == NERR_Success)
   {
      if (pBuf != NULL)
      {
         result = ((PUSER_MODALS_INFO_3)pBuf)->usrmod3_lockout_duration;
         if (result == UINT_MAX)
         {
            internal_printf("Lockout duration (minutes):  Until Admin Unlock\n");
         }
         else
         {
            internal_printf("Lockout duration (minutes):  %lu\n", result / 60);
         }
         internal_printf(
            "Lockout observation window (minutes):  %d\n",
            ((PUSER_MODALS_INFO_3)pBuf)->usrmod3_lockout_observation_window / 60
         );
         result = ((PUSER_MODALS_INFO_3)pBuf)->usrmod3_lockout_threshold;
         if (result == 0)
         {
            internal_printf("Lockout threshold:  Accounts don't lock\n");
         }
         else
         {
            internal_printf("Lockout threshold:  %lu\n", result);
         }
         NETAPI32$NetApiBufferFree(pBuf);
         pBuf = NULL;
      }
      else
      {
         internal_printf("somehow call worked but we didn't get memory? (BROKEN)");
      }
   }
   else
   {
      internal_printf("A system error has occurred(modal 3): %d\n", nStatus);
      goto end;
   }

end:
   if (pBuf != NULL)
   {
      NETAPI32$NetApiBufferFree(pBuf);
   }
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

   if (*server == 0)
   {
      server = NULL;
   }

   get_password_policy(server);
   printoutput(TRUE);
};

#endif
