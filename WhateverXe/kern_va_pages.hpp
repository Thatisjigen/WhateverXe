// Exact page corrections of the Intel VA driver on the Tahoe validator ABI, for
// Raptor Lake-P 8086:A7A0 revision 04. Adapted from lymzzyh's UHD 770 pages
// (lymzzyh/WhateverXe f9be946): the same VFE, L3 and capability tables, our
// device scope, and of the 19 video-processing output lists only the yuv2/NV12
// one that qqaoshi888 isolated in b00t0x/WhateverXe#81, and the broken
// pixel-transfer capabilities. Armed by -wex-va-renderer: AppleGVA opens this
// driver only while IOVARendererID is advertised.
// No product-build string replacement and no dependency on an XNU build date.
#pragma once
#include "kern_xelp_platform.hpp"
#include "kern_xelp_os.hpp"
#include "kern_local_va_vfe.hpp"
#include "kern_local_va_l3.hpp"
#include "kern_local_va_safe.hpp"
#include "kern_local_va_pixel.hpp"
static mach_vm_address_t vaOriginalPage;
static bool vaPageHookReady,vaGen12Enabled,vaSafeEnabled,vaPixelEnabled;
static uint64_t vaVFEPages,vaL3Pages,vaSafePages,vaPixelPages;
using VAPageValidator=void (*)(vnode_t,memory_object_t,memory_object_offset_t,const void *,int *,int *,int *);
// Keep local hardware selection separate from servicing-build metadata.
static bool vaPagesScope(const XELP::Profile &profile,XELP::OS os) {
 return os==XELP::OS::Tahoe && profile.identity==0xa7a08086 && profile.revision==0x04 &&
  !profile.overridden() && XELP::same(profile,XELP::identify(0xa7a08086,0x04));
}
static bool vaPagesSerialize(void *,void *,OSSerialize *serial) {
 const uint64_t q[]{1,vaPageHookReady && vaGen12Enabled,vaPageHookReady && vaSafeEnabled,
  __atomic_load_n(&vaVFEPages,__ATOMIC_ACQUIRE),__atomic_load_n(&vaL3Pages,__ATOMIC_ACQUIRE),
  __atomic_load_n(&vaSafePages,__ATOMIC_ACQUIRE),vaPageHookReady && vaPixelEnabled,
  __atomic_load_n(&vaPixelPages,__ATOMIC_ACQUIRE)};
 auto data=OSData::withBytes(q,sizeof(q));if(!data)return false;
 const bool ok=data->serialize(serial);data->release();return ok;
}
static void vaValidatePage(vnode_t node,memory_object_t pager,memory_object_offset_t offset,
 const void *data,int *validated,int *tainted,int *nx) {
 reinterpret_cast<VAPageValidator>(vaOriginalPage)(node,pager,offset,data,validated,tainted,nx);
 // Code pages must be executable; the capability list lives in a data page.
 const bool accepted=validated && tainted && nx && *validated==0xf && !*tainted && !*nx;
 const bool safePage=vaPageHookReady && vaSafeEnabled && validated && tainted && nx &&
  LocalVASafe::match(data,PAGE_SIZE,offset,*validated==0xf,*tainted)==0;
 const int pixelPage=vaPageHookReady && vaPixelEnabled && accepted ?
  LocalVAPixel::match(data,PAGE_SIZE,offset,true,false) : -1;
 if(!vaPageHookReady || !(safePage || pixelPage>=0 || (accepted && vaGen12Enabled &&
     (LocalVAVFE::matches(data,PAGE_SIZE,offset,true,false) ||
      LocalVAL3::matches(data,PAGE_SIZE,offset,true,false)))))return;
 if(MachInfo::setKernelWriting(true,KernelPatcher::kernelWriteLock)!=KERN_SUCCESS)return;
 // Readers may race: recheck the complete page under the existing write lock.
 if(safePage && LocalVASafe::match(data,PAGE_SIZE,offset,*validated==0xf,*tainted)==0) {
  // Only the first list; the others carry the ARGB conversions the window server needs.
  memset(static_cast<uint8_t *>(const_cast<void *>(data))+LocalVASafe::Pages[0].sites[0].offset,0,4);
  __atomic_fetch_add(&vaSafePages,1ULL,__ATOMIC_RELEASE);
 } else if(pixelPage>=0 && LocalVAPixel::match(data,PAGE_SIZE,offset,true,false)==pixelPage) {
  LocalVAPixel::apply(const_cast<void *>(data),unsigned(pixelPage));__atomic_fetch_add(&vaPixelPages,1ULL,__ATOMIC_RELEASE);
 } else if(accepted && vaGen12Enabled && LocalVAVFE::matches(data,PAGE_SIZE,offset,true,false)) {
  LocalVAVFE::apply(const_cast<void *>(data));__atomic_fetch_add(&vaVFEPages,1ULL,__ATOMIC_RELEASE);
 } else if(accepted && vaGen12Enabled && LocalVAL3::matches(data,PAGE_SIZE,offset,true,false)) {
  LocalVAL3::apply(const_cast<void *>(data));__atomic_fetch_add(&vaL3Pages,1ULL,__ATOMIC_RELEASE);
 }
 MachInfo::setKernelWriting(false,KernelPatcher::kernelWriteLock);
}
static_assert(__is_same(decltype(&vaValidatePage),VAPageValidator),"Tahoe validator ABI");
static void prepareVAPages(KernelPatcher &patcher,IOPCIDevice *gpu,const XELP::Profile &profile,bool renderer) {
 const bool scope=gpu && vaPagesScope(profile,XELP::kernelOS(version));
 vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=scope && renderer;
 vaPageHookReady=false;
 if((vaGen12Enabled || vaSafeEnabled || vaPixelEnabled) && getKernelVersion()==KernelVersion::Tahoe) {
  KernelPatcher::RouteRequest route("_cs_validate_page",vaValidatePage,vaOriginalPage);
  vaPageHookReady=patcher.routeMultipleLong(KernelPatcher::KernelID,&route,1);patcher.clearError();
 }
 auto root=IORegistryEntry::getRegistryRoot();
 root->setProperty("WEXVAPagesScope",scope);
 root->setProperty("WEXVAGen12Ready",vaGen12Enabled && vaPageHookReady);
 root->setProperty("WEXVASafeReady",vaSafeEnabled && vaPageHookReady);
 root->setProperty("WEXVAPixelReady",vaPixelEnabled && vaPageHookReady);
 if(auto live=OSSerializer::forTarget(nullptr,vaPagesSerialize)){root->setProperty("WEXVAPagesLive",live);live->release();}
}
