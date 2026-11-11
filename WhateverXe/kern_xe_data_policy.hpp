// Copyright (c) 2026 b00t0x. BSD-3-Clause.
#pragma once
#include <string.h>

namespace XeDataPolicy {
enum class Client { None, Compiler, WebKitGPU };
// Identity comes from the running process's kernel code-signing state, never
// Info.plist, a basename, or caller-provided metadata. Safari updates and moves
// must not require enumerating executable locations.
inline bool webKitGPU(const char *identity, bool platformBinary, bool valid) {
    return platformBinary && valid && identity && !strcmp(identity, "com.apple.WebKit.GPU");
}
inline bool service(const char *path, Client client = Client::Compiler) {
    // Compiler access keeps its original exact-path contract. WebKit has no
    // path-based fallback: even a familiar location must pass signature checks.
    return client == Client::Compiler && path && !strcmp(path,
        "/System/Library/Frameworks/Metal.framework/Versions/A/"
        "XPCServices/MTLCompilerService.xpc/Contents/MacOS/MTLCompilerService");
}
inline bool file(const char *path, bool executable) {
    if (!path) return false;
    // vn_getpath may expose the Data mount rather than its firmlink.
    constexpr const char data[] = "/System/Volumes/Data";
    if (!strncmp(path, data, sizeof(data)-1)) path += sizeof(data)-1;
    if (!executable && (!strcmp(path, "/Library/GPUBundles/XeCompilerAdapter.bundle") ||
        !strcmp(path, "/Library/GPUBundles/XeCompilerAdapter.bundle/Contents") ||
        !strcmp(path, "/Library/GPUBundles/XeCompilerAdapter.bundle/Contents/MacOS"))) return true;
    constexpr const char dir[] = "/Library/GPUBundles/XeCompilerAdapter.bundle/Contents/";
    if (strncmp(path, dir, sizeof(dir)-1)) return false;
    path += sizeof(dir)-1;
    if (!strcmp(path, "MacOS/adapter.dylib") || !strcmp(path, "MacOS/libigc-tgl.dylib")) return true;
    return !executable && (!strcmp(path, "MacOS/runtime.igc64.bc") || !strcmp(path, "Info.plist"));
}
// The images NullMoth's Metal plugin maps on a machine that also has an NVIDIA
// GPU: the plugin, its shader translator, the AIR runtime it carries and the
// Vulkan driver. Exact paths, as for our own images.
inline bool nvidiaRuntime(const char *path) {
    constexpr const char bundle[] = "/Library/GPUBundles/NVMTLDriver.bundle/Contents/MacOS/";
    if (!strncmp(path, bundle, sizeof(bundle)-1)) {
        path += sizeof(bundle)-1;
        return !strcmp(path, "NVMTLDriver") || !strcmp(path, "libnvmtl_translate.dylib") ||
            !strcmp(path, "air-runtime/libLLVM.dylib") || !strcmp(path, "air-runtime/libzstd.1.dylib");
    }
    return !strcmp(path, "/Library/GPUBundles/nvmtl/libvulkan_nouveau.dylib") ||
        !strcmp(path, "/Library/GPUBundles/nvmtl/libnvmtl_translate.dylib");
}
// libnvencvt, whose video decoders the plugin registers in that service: WebKit
// decodes video there and takes the decoder from the service's own registry.
// The plugin's encoder libraries and its other decoder libraries are not listed.
inline bool nvidiaDecoders(const char *path) {
    return !strcmp(path, "/Library/GPUBundles/NVMTLDriver.bundle/Contents/MacOS/libnvencvt.dylib");
}
inline Client clientForFile(const char *path, bool executable, bool nvidia = true, bool video = false) {
    if (file(path, executable)) return Client::Compiler;
    // WebKit already permits Data reads; allow executable maps of fixed GPU images.
    if (!path || !executable) return Client::None;
    constexpr const char data[] = "/System/Volumes/Data";
    if (!strncmp(path, data, sizeof(data)-1)) path += sizeof(data)-1;
    // The two Sandbox callbacks take one route, and on a hybrid machine it is
    // ours: a second plugin cannot grant this for the other GPU's runtime.
    // The decoders only on request: without them the service keeps the NVIDIA
    // Metal runtime and decodes on the Intel VA driver or the CPU.
    if (nvidia && (nvidiaRuntime(path) || (video && nvidiaDecoders(path)))) return Client::WebKitGPU;
    constexpr const char va[] = "/Library/GPUBundles/AppleIntelTGLGraphicsVADriver.bundle/Contents/MacOS/";
    if (!strncmp(path, va, sizeof(va)-1)) {
        path += sizeof(va)-1;
        return !strcmp(path, "AppleIntelTGLGraphicsVADriver") || !strcmp(path, "TGLVA") ?
            Client::WebKitGPU : Client::None;
    }
    constexpr const char metal[] = "/Library/GPUBundles/AppleIntelTGLGraphicsMTLDriver.bundle/Contents/MacOS/";
    if (strncmp(path, metal, sizeof(metal)-1)) return Client::None;
    path += sizeof(metal)-1;
    return !strcmp(path, "AppleIntelTGLGraphicsMTLDriver") || !strcmp(path, "descriptor.dylib") ||
        !strcmp(path, "impostor.dylib") || !strcmp(path, "libigdmd.dylib") ? Client::WebKitGPU : Client::None;
}
inline bool readOnly(int mode) { return mode == 1; } // FREAD, no create/truncate/write flags.
inline bool executeOnly(int prot, int flags) {
    return (prot == 4 || prot == 5) && (flags & 3) == 2; // RX/X, MAP_PRIVATE.
}
}
