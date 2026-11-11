#!/usr/bin/env python3
"""Check fixed-page SHA-256 against hashlib, including every one-byte mutation."""
from pathlib import Path
import hashlib, random, subprocess, tempfile

root = Path(__file__).resolve().parents[1]
code = r'''
#include "kern_uhd770_page.hpp"
#include <cassert>
#include <cstdio>
int main(int argc,char **argv) {
 assert(argc==2);auto input=fopen(argv[1],"rb");assert(input);
 unsigned cases=0;uint8_t page[4096],expected[32],actual[32];
 while(fread(page,1,sizeof(page),input)==sizeof(page)) {
  assert(fread(expected,1,sizeof(expected),input)==sizeof(expected));
  UHD770Page::digest(page,actual);assert(!memcmp(actual,expected,32));
  assert(UHD770Page::matches(page,sizeof(page),expected));
  expected[cases%32]^=1;assert(!UHD770Page::matches(page,sizeof(page),expected));
  assert(!UHD770Page::matches(nullptr,sizeof(page),expected));
  assert(!UHD770Page::matches(page,4095,expected));
  assert(!UHD770Page::matches(page,4097,expected));
  assert(!UHD770Page::matches(page,sizeof(page),nullptr));++cases;
 }
 assert(feof(input));fclose(input);printf("PASS: %u independent SHA-256 page vectors\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix='uhd770-sha-') as tmp:
    work = Path(tmp)
    (work/'test.cpp').write_text(code)
    random_source = random.Random(770)
    base = bytes(range(256))*16
    with (work/'vectors.bin').open('wb') as out:
        def add(data):
            out.write(data)
            out.write(hashlib.sha256(data).digest())
        for data in (bytes(4096), bytes([255])*4096, base):
            add(data)
        for i in range(4096):
            data=bytearray(base);data[i]^=1;add(data)
        for _ in range(100):
            add(bytes(random_source.randrange(256) for _ in range(4096)))
    subprocess.run(['clang++','-std=c++17','-O1','-fsanitize=address,undefined',
                    '-I'+str(root/'WhateverXe'),str(work/'test.cpp'),'-o',str(work/'test')],check=True)
    subprocess.run([str(work/'test'),str(work/'vectors.bin')],check=True)
