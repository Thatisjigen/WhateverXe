# WhateverXe

[日本語](README_ja.md)

WhateverXe is a Lilu plugin, derived from WhateverGreen, that adapts Apple graphics drivers for selected Intel Xe-LP integrated GPUs.
Use the latest releases of [WhateverXe](https://github.com/b00t0x/WhateverXe/releases) and [WhateverXe Graphics](https://github.com/b00t0x/WhateverXe-Graphics/releases) together. See [CHANGELOG](CHANGELOG.md) for release notes.

## Compatibility

| macOS | Required version |
| --- | --- |
| Big Sur | 11.7.11 |
| Monterey | 12.7.6 |
| Ventura | 13.7.8 |
| Sonoma | 14.8.9 |
| Sequoia | 15.8.x |
| Tahoe | 26.7 or newer |

Sequoia and Tahoe accept compatible updates within their OS family. Future Apple changes may require an update to WEX or Graphics.

### Tested on hardware

- Tiger Lake-U: 48- and 80-EU configurations.
- Alder Lake-N: 16- and 24-EU configurations.
- Twin Lake: 32-EU configurations.
- Alder Lake-H: 96-EU configurations, including single-channel operation.
- Alder Lake-S: UHD Graphics 770.
- Raptor Lake-U: 48-EU configurations.

See [tested features and known issues](#tested-features-and-known-issues) for OS coverage and display configurations. PCI IDs are listed in [device selection](docs/device-selection.md).

### Expected to work, not yet tested on hardware

- Other supported Tiger Lake-U/H35 configurations, including 96 EU, and Tiger Lake-H45.
- Other supported Alder Lake-N / Twin Lake configurations.
- Other supported Alder Lake-H/P/U and Raptor Lake-H/P/U configurations.
- Other supported Alder Lake-S/HX and Raptor Lake-S/HX configurations.
- Internal eDP on Alder Lake-N / Twin Lake and Alder Lake-H/P/U / Raptor Lake-H/P/U is implemented but has not been tested on hardware.

### Further implementation required

- Rocket Lake-S: display control requires additional support.

### No support planned

- Xe-LPG, including Meteor Lake integrated graphics.
- Xe2 and later graphics architectures.

## Installation

1. Add Lilu, `WhateverXe.kext` and [AMFIPass 1.4.1 Mod](https://github.com/b00t0x/WhateverXe-Graphics/blob/main/extras/AMFIPass-v1.4.1-Mod-RELEASE.zip) to OpenCore, with WEX after Lilu. Use the WEX **RELEASE** ZIP; DEBUG is for troubleshooting.
2. Set `csr-active-config=03080000` (`0x803`) and apply the [configuration](#configuration).
3. Boot the target macOS, install the latest [WhateverXe Graphics pkg](https://github.com/b00t0x/WhateverXe-Graphics/releases), then restart. [Package installation and removal](https://github.com/b00t0x/WhateverXe-Graphics#install).

Use the linked **Mod** AMFIPass instead of upstream AMFIPass; do not load both. WhateverGreen and WhateverXe must not be enabled together. `amfi=0x80` and `ipc_control_port_options=0` are unnecessary.

Graphics installs under `/Library` and rebuilds AuxKC without patching System files or snapshots. Restore an old Xe System patch before installing. If you need OCLP for other root patches, use the [custom OCLP build](https://github.com/b00t0x/OpenCore-Legacy-Patcher) with the matching Mod signing chain.

## Configuration

### Required boot arguments

Add to OpenCore's `boot-args`:

```text
-allow3d -disablegfxfirmware
```

### DVMT

Set **DVMT Pre-Allocated to 96MB** in BIOS/UEFI where possible.
If it is fixed at **60MB**, also add `-igfxdvmt` and set these iGPU properties under `DeviceProperties > Add` (usually `PciRoot(0x0)/Pci(0x2,0x0)`):

| Property | Type | Value (hex) |
| --- | --- | --- |
| `framebuffer-patch-enable` | Data | `01000000` |
| `framebuffer-stolenmem` | Data | `0000C003` |

These settings are unnecessary at 96MB and do not increase firmware-allocated memory.

### Other settings

- Add `SSDT-PNLF` for internal-display brightness control.
- GPU selection is automatic; a `device-id` override is normally unnecessary.
- Alder Lake-N / Twin Lake and Alder Lake-H/P/U / Raptor Lake-H/P/U select tiling automatically. Do not use `-yTileDisable`; `AAPL,GfxYTile` is unnecessary.
- Temporary development diagnostic: `-wex-reset-trace` records each GPU hang recovery step (channel restart, engine reset, scheduler reset and resume, command-streamer reset) with the render engine's reset and ring registers in the `WEXGPUResetTrace` registry property. It does not change recovery.
- On a machine with a USB-C DP Alt output, the panel's plane stays off from a modeset to WindowServer's next frame, so its base memory, an old image, is not shown. `-wex-panel-base-visible` shows it as before.
- On by default (`-wex-no-reset-recover` turns it off): saves the render engine's mode, status-page, chicken and user-mode whitelist registers and its cache-control (MOCS and L3) tables just before a render-domain GPU hang reset and writes them back after the reset, before work is replayed, on GPUs where the reset clears them, and completes stamps whose work the reset lost: two seconds after the reset, and later whenever a waiter times out on one that has stopped moving. It also enables the reset trace.
- On by default (`-wex-no-hidpi-dbuf` turns it off): gives the cursor 96 DBUF blocks instead of 40 and an RGB primary its planned allocation from the first write, for HiDPI modes behind the pipe scaler at high refresh rates.
- On by default (`-wex-no-scanout-coherent` turns it off): treats every surface the donor flips to a display plane as displayable, so its later rendering uses the donor's display-safe (not LLC-cached) MOCS. The display engine does not snoop the LLC.
- HDR10 modes on the Intel outputs and the SGX feature flag that makes the system offer HDR are on by default (`-wex-no-hdr-modes`, `-wex-no-hdr-sgx` turn them off). The graphics family's console back-copy at boot is off by default; `gfxrst=` selects a WhateverGreen mode as before.
- On a machine that also has an NVIDIA GPU driven by NullMoth's driver, Safari's GPU service may map that driver's Metal runtime (the plugin, its shader translator and AIR runtime, the Vulkan driver) under the same checks as the Intel images: the service's kernel signing identity, exact paths, executable private maps only. Without it the service loads only the Intel driver, whichever GPU drives the display. The two Sandbox callbacks involved take a single route, so a separate plugin cannot grant this while WhateverXe is loaded. `-wex-no-nv-webkit` turns it off; the NVIDIA codec libraries are not admitted.
- `IOVARendererID` is hidden by default on the display family where advertising it crashes the VA driver during image conversion (`VTPixelTransferSession`, Photo Booth, mediaanalysisd); other machines on the same kext keep it. Experimental: `-wex-va-renderer` keeps it advertised there too, for GPUs that want the VA renderer and do not hit the crash, at the cost that HEVC may then fall back to software in Apple's decoder service.
- Experimental, Raptor Lake-P `8086:A7A0` revision 04 on Tahoe only: with `-wex-va-renderer`, the Intel VA driver's video processing is corrected when the code-signing validator accepts its exact pages. Its `MEDIA_VFE_STATE` follows the Gen12 layout, its media L3 setup writes `L3ALLOCREG`, and the one video-processing output list (yuv2/NV12) whose configuration can leave the batch unfinished is hidden, keeping every ARGB conversion. They change pages of a signed driver in memory, so AMFI must tolerate it. Based on lymzzyh's UHD 770 work and the list isolated in b00t0x/WhateverXe#81.
- With a second GPU left without a driver, the graphics family gives it a placeholder framebuffer the window server never opens, and that placeholder's controller keeps the family from telling the accelerators about system sleep, so the sleep entry waits out the family's timeout and the wake restarts nothing. At the system's will-sleep notice, and again at wake, the plugin clears the placeholder controller's wait state, as the window server would have, and records it in `RPLPWSStart`; with every GPU driven there is no such controller and nothing is written. This is `-wex-rplp-wsstart` from Samran Ahmad's WhateverXe-RaptorLakeP, on by default here; `-wex-no-rplp-wsstart` turns it off. The walk runs only while the family's controller class has the size its field offsets were read at. The first sleep after a boot still waits about thirty seconds, because the window server's own sleep notice times out before the kernel's will-sleep notice is sent; once the state has been cleared the displays go to sleep at once.

## Tested features and known issues

The common regression checks cover Metal, OpenGL, OpenCL, hardware H.264 encode/decode and HEVC decode. The table summarizes OS coverage and configuration-specific display features.

| Configuration | Verified coverage |
| --- | --- |
| Tiger Lake mini PCs | Big Sur–Tahoe: 80 EU, two 1080p60 displays, display off/on, Safari video and Widevine |
| Tiger Lake laptops | Big Sur–Tahoe: 48 EU, internal eDP and brightness, HDMI/USB-C, up to three displays and display off/on |
| Alder Lake-N mini PCs | Big Sur–Tahoe: 16/24 EU, two 1080p60 HDMI displays and display off/on |
| Alder Lake-N / Twin Lake laptops | MicroPC 2 and MiniBook X N100 on Big Sur/Tahoe: MIPI DSI, brightness, rotation, display off/on and HDMI/USB-C coexistence. MicroPC 2: HiDPI and up to three displays; MiniBook X N100: optional 60 Hz |
| Raptor Lake-U laptop | MiniBook X U300 on Big Sur/Tahoe: internal MIPI DSI, brightness, rotation, HiDPI and up to two USB-C displays. Internal panel: 50 Hz; optional 60 Hz also tested on Big Sur |
| Alder Lake-H | Big Sur–Tahoe: 96 EU, three displays using HDMI and a DP-to-HDMI adapter. Single-channel `4626` graphics acceleration checked on Big Sur |
| Alder Lake-S | Big Sur–Tahoe: UHD 770, HDMI/DP/USB-C and up to three displays; Safari video, with Widevine checked on Big Sur/Tahoe |

MIPI DSI support is **experimental**, limited to the tested GPD MicroPC 2 and CHUWI MiniBook X N100/U300 panels. Do not expect it to work on other devices.

System sleep/wake support is **experimental**. Tested configurations are MiniBook X N100/U300 (MIPI DSI) on Big Sur and Tahoe with model-specific ACPI settings, using the internal display alone or up to two external displays. Other models, OS versions and prolonged DarkWake cycles remain unverified.

### Known issues and limits

- DisplayPort reconnection can cause black screens or freezes. Tiger Lake USB-C reconnection is also unreliable; Alder Lake-S DP output/reconnection can be slow.
- Some image-conversion operations can crash applications.
- Safari video may occasionally drop frames. FairPlay-protected playback is unsupported.
- Up to three displays are supported. Resolutions beyond the tested configurations remain unverified.
- Some connector layouts and backlight methods, MST and Thunderbolt-managed outputs are unsupported.

### Roadmap

- Complete DisplayPort, USB-C and internal-display support on Alder Lake-N / Twin Lake and Alder Lake-H/P/U / Raptor Lake-H/P/U.
- Improve display reconnection reliability and extend system sleep/wake coverage.

## Build and test

Requires macOS, Xcode command-line tools, Python 3.9+, MacKernelSDK and Lilu 1.7.2 development headers/library. Place `MacKernelSDK/` and `Lilu.kext/` in the repository root, or pass `--sdk` and `--lilu`.

```sh
python3 tools/build.py --release
python3 tools/test.py
```

Output is under `build/`. AppleIntelTGLCompat is built here and distributed through Graphics. Optional exact-donor tests accept `--donor` and `--accelerator` paths.

## License and credits

WhateverXe retains WhateverGreen's copyright notices and BSD-3-Clause license.
See [LICENSE.txt](LICENSE.txt). Lilu and MacKernelSDK are separate dependencies.

Thanks to [JulioNectar/XPS13Plus](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe) for sharing its Xe graphics work. Its compiler adapter and LLVM bridge informed the OS-native AIR conversion used in WhateverXe Graphics.

Internal-panel work also draws on [WhateverXe-RaptorLakeP](https://github.com/samranahmad09/WhateverXe-RaptorLakeP), [X1Carbon-G11](https://github.com/dssoftx/Hackintosh-X1Carbon-G11-IrisXe-Tahoe), XPS13Plus and the [Linux i915 display sources](https://github.com/torvalds/linux/tree/v6.12/drivers/gpu/drm/i915/display) for hardware behavior and implementation comparisons.

The optional MiniBook X 60 Hz panel timing also draws on the [minibookx-ctl display guide](https://github.com/ishad0w/minibookx-ctl/blob/main/docs/guide/display.md).
