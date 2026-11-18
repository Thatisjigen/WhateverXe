// Exact page corrections of the Intel VA driver on the Tahoe validator ABI, for
// Raptor Lake-P 8086:A7A0 revision 04. Adapted from lymzzyh's UHD 770 pages
// (lymzzyh/WhateverXe f9be946): the same VFE, L3 and capability tables, our
// device scope, and of the 19 video-processing output lists only the yuv2/NV12
// one that qqaoshi888 isolated in b00t0x/WhateverXe#81, and the broken
// pixel-transfer capabilities. Armed by -wex-va-renderer: AppleGVA opens this
// driver only while IOVARendererID is advertised.
// No product-build string replacement and no dependency on an XNU build date.
// The same validator route also switches off Intel's plug-in for Metal
// Performance Shaders in the Metal driver, on Tahoe and for every GPU this kext
// drives (kern_mtl_mps_page.hpp); -wex-intel-mps-plugin leaves the plug-in on.
// On the same Raptor Lake-P it also gives Metal compute kernels the 64 KB class
// of thread-group memory in place of the 16 and 32 KB ones
// (kern_mtl_slm_page.hpp); -wex-no-slm-64k keeps the driver's classes.
// And it lets the Xe compiler adapter of WhateverXe Graphics compile compute pipelines that carry a maximum
// thread count (kern_xe_adapter_page.hpp), on Tahoe for every GPU this kext drives;
// -wex-no-compute-max-threads keeps the adapter's refusal.
// On the same Raptor Lake-P, small Metal compute dispatches run a kernel's SIMD16 binary instead of its SIMD8 one
// (kern_mtl_simd_page.hpp); -wex-simd8-dispatch keeps the driver's choice.
#pragma once
#include "kern_xelp_platform.hpp"
#include "kern_xelp_os.hpp"
#include "kern_local_va_vfe.hpp"
#include "kern_local_va_l3.hpp"
#include "kern_local_va_safe.hpp"
#include "kern_local_va_pixel.hpp"
#include "kern_mtl_mps_page.hpp"
#include "kern_mtl_slm_page.hpp"
#include "kern_xe_adapter_page.hpp"
#include "kern_mtl_simd_page.hpp"
static mach_vm_address_t vaOriginalPage;
static bool vaPageHookReady,vaGen12Enabled,vaSafeEnabled,vaPixelEnabled,mpsPluginOffReady,slmClassReady,computeLimitReady,simdChoiceReady;
static uint64_t vaVFEPages,vaL3Pages,vaSafePages,vaPixelPages,mpsPluginPages,slmClassPages,computeLimitPages,simdChoicePages;
using VAPageValidator=void (*)(vnode_t,memory_object_t,memory_object_offset_t,const void *,int *,int *,int *);
// Keep local hardware selection separate from servicing-build metadata.
static bool vaPagesScope(const XELP::Profile &profile,XELP::OS os) {
 return os==XELP::OS::Tahoe && profile.identity==0xa7a08086 && profile.revision==0x04 &&
  !profile.overridden() && XELP::same(profile,XELP::identify(0xa7a08086,0x04));
}
// The compiler that rejects the plug-in's sources is Tahoe's, whatever the GPU.
static bool mpsPluginPageScope(const XELP::Profile &profile,XELP::OS os) {return os==XELP::OS::Tahoe && profile.admitted();}
static bool mpsPluginSerialize(void *,void *,OSSerialize *serial) {
 const uint64_t q[]{1,mpsPluginOffReady,__atomic_load_n(&mpsPluginPages,__ATOMIC_ACQUIRE)};
 auto data=OSData::withBytes(q,sizeof(q));if(!data)return false;
 const bool ok=data->serialize(serial);data->release();return ok;
}
static bool slmClassSerialize(void *,void *,OSSerialize *serial) {
 const uint64_t q[]{1,slmClassReady,__atomic_load_n(&slmClassPages,__ATOMIC_ACQUIRE)};
 auto data=OSData::withBytes(q,sizeof(q));if(!data)return false;
 const bool ok=data->serialize(serial);data->release();return ok;
}
static bool computeLimitSerialize(void *,void *,OSSerialize *serial) {
 const uint64_t q[]{1,computeLimitReady,__atomic_load_n(&computeLimitPages,__ATOMIC_ACQUIRE)};
 auto data=OSData::withBytes(q,sizeof(q));if(!data)return false;
 const bool ok=data->serialize(serial);data->release();return ok;
}
static bool simdChoiceSerialize(void *,void *,OSSerialize *serial) {
 const uint64_t q[]{1,simdChoiceReady,__atomic_load_n(&simdChoicePages,__ATOMIC_ACQUIRE)};
 auto data=OSData::withBytes(q,sizeof(q));if(!data)return false;
 const bool ok=data->serialize(serial);data->release();return ok;
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
 const bool mpsPage=mpsPluginOffReady && accepted && MetalMPSPlugin::matches(data,PAGE_SIZE,offset,true,false);
 const bool slmPage=slmClassReady && accepted && MetalSLMClass::matches(data,PAGE_SIZE,offset,true,false);
 const bool limitPage=computeLimitReady && accepted && XeAdapterComputeLimit::matches(data,PAGE_SIZE,offset,true,false);
 const bool simdPage=simdChoiceReady && accepted && MetalSIMDChoice::matches(data,PAGE_SIZE,offset,true,false);
 const bool safePage=vaPageHookReady && vaSafeEnabled && validated && tainted && nx &&
  LocalVASafe::match(data,PAGE_SIZE,offset,*validated==0xf,*tainted)==0;
 const int pixelPage=vaPageHookReady && vaPixelEnabled && accepted ?
  LocalVAPixel::match(data,PAGE_SIZE,offset,true,false) : -1;
 const bool vaPage=vaPageHookReady && (safePage || pixelPage>=0 || (accepted && vaGen12Enabled &&
     (LocalVAVFE::matches(data,PAGE_SIZE,offset,true,false) ||
      LocalVAL3::matches(data,PAGE_SIZE,offset,true,false))));
 if(!mpsPage && !slmPage && !limitPage && !simdPage && !vaPage)return;
 if(MachInfo::setKernelWriting(true,KernelPatcher::kernelWriteLock)!=KERN_SUCCESS)return;
 // Readers may race: recheck the complete page under the existing write lock.
 if(mpsPage && MetalMPSPlugin::matches(data,PAGE_SIZE,offset,true,false)) {
  MetalMPSPlugin::apply(const_cast<void *>(data));__atomic_fetch_add(&mpsPluginPages,1ULL,__ATOMIC_RELEASE);
 } else if(slmPage && MetalSLMClass::matches(data,PAGE_SIZE,offset,true,false)) {
  MetalSLMClass::apply(const_cast<void *>(data));__atomic_fetch_add(&slmClassPages,1ULL,__ATOMIC_RELEASE);
 } else if(limitPage && XeAdapterComputeLimit::matches(data,PAGE_SIZE,offset,true,false)) {
  XeAdapterComputeLimit::apply(const_cast<void *>(data));__atomic_fetch_add(&computeLimitPages,1ULL,__ATOMIC_RELEASE);
 } else if(simdPage && MetalSIMDChoice::matches(data,PAGE_SIZE,offset,true,false)) {
  MetalSIMDChoice::apply(const_cast<void *>(data));__atomic_fetch_add(&simdChoicePages,1ULL,__ATOMIC_RELEASE);
 } else if(!vaPage) {
 } else if(safePage && LocalVASafe::match(data,PAGE_SIZE,offset,*validated==0xf,*tainted)==0) {
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
static void prepareVAPages(KernelPatcher &patcher,IOPCIDevice *gpu,const XELP::Profile &profile,bool renderer,bool intelMPSPlugin=false,
 bool nativeSLMClass=false,bool adapterRefusesLimit=false,bool driverSIMD8=false) {
 const bool scope=gpu && vaPagesScope(profile,XELP::kernelOS(version));
 vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=scope && renderer;
 const bool mpsPluginOff=gpu && mpsPluginPageScope(profile,XELP::kernelOS(version)) && !intelMPSPlugin;
 // Seen on this device and revision only: the same scope as the VA pages, without their switch.
 const bool slmClass=scope && !nativeSLMClass;
 // The adapter is the same file for every GPU the Graphics package serves: the MPS plug-in's scope.
 const bool computeLimit=gpu && mpsPluginPageScope(profile,XELP::kernelOS(version)) && !adapterRefusesLimit;
 // Seen on this device and revision only, like the thread-group memory class.
 const bool simdChoice=scope && !driverSIMD8;
 vaPageHookReady=mpsPluginOffReady=slmClassReady=computeLimitReady=simdChoiceReady=false;
 // One route serves every page correction: a second one over the same function is not safe.
 if((vaGen12Enabled || vaSafeEnabled || vaPixelEnabled || mpsPluginOff || slmClass || computeLimit || simdChoice) &&
    getKernelVersion()==KernelVersion::Tahoe) {
  KernelPatcher::RouteRequest route("_cs_validate_page",vaValidatePage,vaOriginalPage);
  const bool routed=patcher.routeMultipleLong(KernelPatcher::KernelID,&route,1);patcher.clearError();
  vaPageHookReady=routed && (vaGen12Enabled || vaSafeEnabled || vaPixelEnabled);
  mpsPluginOffReady=routed && mpsPluginOff;
  slmClassReady=routed && slmClass;
  computeLimitReady=routed && computeLimit;
  simdChoiceReady=routed && simdChoice;
 }
 auto root=IORegistryEntry::getRegistryRoot();
 root->setProperty("WEXVAPagesScope",scope);
 root->setProperty("WEXVAGen12Ready",vaGen12Enabled && vaPageHookReady);
 root->setProperty("WEXVASafeReady",vaSafeEnabled && vaPageHookReady);
 root->setProperty("WEXVAPixelReady",vaPixelEnabled && vaPageHookReady);
 if(auto live=OSSerializer::forTarget(nullptr,vaPagesSerialize)){root->setProperty("WEXVAPagesLive",live);live->release();}
 // Whether Intel's MPS plug-in is being switched off, and how many times its page was corrected.
 root->setProperty("WEXMPSPluginOffReady",mpsPluginOffReady);
 if(auto live=OSSerializer::forTarget(nullptr,mpsPluginSerialize)){root->setProperty("WEXMPSPluginLive",live);live->release();}
 // Whether thread-group memory gets the 64 KB class, and how many times that page was corrected.
 root->setProperty("WEXMetalSLMClassReady",slmClassReady);
 if(auto live=OSSerializer::forTarget(nullptr,slmClassSerialize)){root->setProperty("WEXMetalSLMClassLive",live);live->release();}
 // Whether the compiler adapter accepts a compute pipeline's maximum thread count, and how many times its page was corrected.
 root->setProperty("WEXComputeMaxThreadsReady",computeLimitReady);
 if(auto live=OSSerializer::forTarget(nullptr,computeLimitSerialize)){root->setProperty("WEXComputeMaxThreadsLive",live);live->release();}
 // Whether small compute dispatches run the SIMD16 binary, and how many times that page was corrected.
 root->setProperty("WEXMetalSIMDChoiceReady",simdChoiceReady);
 if(auto live=OSSerializer::forTarget(nullptr,simdChoiceSerialize)){root->setProperty("WEXMetalSIMDChoiceLive",live);live->release();}
}
