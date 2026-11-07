#!/usr/bin/env python3
"""Pin the ADL-N opt-in scope for Wa_18022495364 without widening the TGL trials."""
from pathlib import Path
import re
s=(Path(__file__).resolve().parents[1]/'WhateverXe/kern_xe.cpp').read_text()
assert 'static constexpr uint32_t tglTahoeDisabledTrials=31;' in s
assert 'const bool tahoeTrialScope=!adlnDetected && checkKernelArgument("-disablegfxfirmware") &&' in s
gate=re.search(r'const bool adlnContextCacheRequested=(.*?);',s,re.S)[1]
for need in ['adlnDetected','checkKernelArgument("-disablegfxfirmware")','XELP::OS::Tahoe','checkKernelArgument("-wex-adln-ctx-invalidate")']:
    assert need in gate,need
assert gate.count('&&')==3
assert 'const bool contextCacheRequested=(tahoeTrialScope && !(tglTahoeDisabledTrials&2)) || adlnContextCacheRequested;' in s
assert 'TGLContextCache::soft()=adlnContextCacheRequested;' in s
# Only the indirect trial: the other Tahoe trials keep their TGL-only scope.
for expr in ['completionCacheRequested=tahoeTrialScope && !(tglTahoeDisabledTrials&1)',
             'tglSameTailEnabled=tahoeTrialScope && hostOK',
             'tglRPCSPowerReady=gsyncQualified && !(tglTahoeDisabledTrials&16)']:
    assert expr in s,expr
assert s.index('const bool adlnContextCacheRequested') < s.index('bool contextCacheOK=!contextCacheRequested;')
init=s[s.index('static bool tglContextCacheInit(void'):s.index('// r150:')]
assert init.count('return TGLContextCache::decline(ok);')==2 and 'return false;' not in init
assert 'tglContextCacheSerialize' not in init
print('PASS: ADL-N Wa_18022495364 opt-in requires host scheduler, Tahoe and boot argument; TGL trials unchanged; soft declines')
