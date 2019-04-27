#!/usr/bin/env python

import dejavu.fingerprint as fingerprint
import dejavu.decoder as decoder
from pydub import AudioSegment
from collections import deque
from collections import defaultdict
from itertools import combinations
from os.path import basename
import sys

mp3file=sys.argv[1]

def chunker(it, n):
    p = 0
    while True:
        if p > len(it):
            return
        yield it[p:p+n]
        p += n

def sample_to_msec(samp, F=22050):
    return int(samp*2048/F*1000)


channels, Fs, file_hash = decoder.read(mp3file, None)

chunk_sz = Fs * 2048
all_hashes = deque()
begin_chunk = 0
for chunk in chunker(channels[0], chunk_sz):
    hashes = fingerprint.fingerprint(chunk, Fs=Fs, plot=False)
    for hash, t_offset in hashes:
        all_hashes.append((hash,t_offset + int(begin_chunk / 2048),))
    begin_chunk += chunk_sz

ts = defaultdict(list)
for h, t in all_hashes:
    ts[h].append(t)
multis = {k: v for k, v in ts.items() if len(v) > 1}

pairs = defaultdict(list)
for k, v in multis.items():
    for a, b in combinations(v, 2):
        pairs[a].append(b)

sorted_keys = sorted(pairs.keys())




l=set()
def r(pivot1, pivot2, stack, maxlen=50):
    for try_pivot1, try_pivot2 in zip(range(pivot1+1,pivot1+maxlen), range(pivot2+1,pivot2+maxlen)):
         if(try_pivot1 in pairs and try_pivot2 in pairs[try_pivot1]):
            stack.append((try_pivot1, try_pivot2))
            return r(try_pivot1, try_pivot2, stack)
    return stack

for pivot1 in sorted_keys:
    for pivot2 in sorted(pairs[pivot1]):
        s=r(pivot1, pivot2, [])
        if len(s) > 20:
            l.add(tuple(s))

ranges=[]
for thelist in l:
    one, two = zip(*thelist)
    ranges.append([min(one), max(one)])
    ranges.append([min(two), max(two)])

ends = defaultdict(list)
for a, b in ranges:
    ends[b].append(a)

new_range = []
for end, keys in ends.items():
    new_range.append([min(keys), end])

final = set()
prev_a, prev_b = 0, 0
for a, b in sorted(new_range):
    print(f'{prev_a} {prev_b} {a} {b}')
    if prev_a <= a < prev_b:
        prev_a = min([prev_a, a])
        prev_b = max([prev_b, b])
    else:
        if prev_a != 0 and prev_b != 0:
            final.add((prev_a,prev_b))
        prev_a, prev_b = a, b

commercials = AudioSegment.empty()
allelse = AudioSegment.empty()
audiofile = AudioSegment.from_mp3(file=mp3file)
marker = 0
for a, b in sorted(final):
    allelse += audiofile[sample_to_msec(marker):sample_to_msec(a-1)]
    commercials += audiofile[sample_to_msec(a):sample_to_msec(b)]
    marker = b+1

bn=basename(mp3file)

commercials.export(f'{bn}_commercials.mp3')
allelse.export(f'{bn}_content.mp3')

pct=commercials.duration_seconds / allelse.duration_seconds * 100
print(f'reduced by {pct:0.2f}%')

