#include <windows.h>
#include "beacon.h"
#include "bofdefs.h"

void go(char * args, int len) {
    BeaconPrintf(CALLBACK_OUTPUT, "[nano-bofs] Mythic COFF test OK");
    BeaconPrintf(CALLBACK_OUTPUT, "[nano-bofs] Argument buffer length: %d", len);
    (void)args;
}
