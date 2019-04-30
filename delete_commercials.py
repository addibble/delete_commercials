#!/usr/bin/env python

import dejavu.fingerprint as fingerprint
import dejavu.decoder as decoder
from pydub import AudioSegment
from pydub.utils import db_to_float
from collections import deque
from collections import defaultdict
from itertools import combinations
from os.path import basename
import sys

def chunker(it, n):
    p = 0
    while True:
        if p > len(it):
            return
        yield it[p:p+n]
        p += n

def sample_to_msec(samp, F=22050):
    return int(samp*2048/F*1000)


def generate_hashes(mp3file):
    channels, Fs, file_hash = decoder.read(mp3file, None)
    chunk_sz = Fs * 2048
    all_hashes = deque()
    begin_chunk = 0
    for chunk in chunker(channels[0], chunk_sz):
        hashes = fingerprint.fingerprint(chunk, Fs=Fs, plot=False)
        for hash, t_offset in hashes:
            all_hashes.append((hash,t_offset + int(begin_chunk / 2048),))
        begin_chunk += chunk_sz
    return all_hashes

def make_hash_pairs(all_hashes):
    # now create a dict of {hash: [sample_offset, sample_offset]}
    ts = defaultdict(list)
    for h, t in all_hashes:
        ts[h].append(t)

    # select the hashes that appear more than once
    multis = {k: v for k, v in ts.items() if len(v) > 1}

    # create an ordered list of (timestamp, hash)
    pairs = defaultdict(list)
    for k, v in multis.items():
        for a, b in combinations(v, 2):
            pairs[a].append(b)
    return pairs

def detect_rough_commercials(pairs, gapsize_ms=10000, maxlen=50):
    l=set()
    def r(pivot1, pivot2, stack, maxlen=maxlen):
        for try_pivot1, try_pivot2 in zip(range(pivot1+1,pivot1+maxlen), range(pivot2+1,pivot2+maxlen)):
            if(try_pivot1 in pairs and try_pivot2 in pairs[try_pivot1]):
                stack.append(try_pivot1)
                return r(try_pivot1, try_pivot2, stack)
        return stack

    for pivot1 in sorted(pairs.keys()):
        for pivot2 in sorted(pairs[pivot1]):
            s=r(pivot1, pivot2, [])
            # if the repeated segment is over 10 seconds long, add it to the candidate list
            if s and sample_to_msec(max(s) - min(s)) > gapsize_ms:
                l += s

    final = deque()
    sorted_list = sorted(l)
    start_pos = sorted_list[0]
    prev_pos = sorted_list[0]

    # deduplicate overlapping segments
    for pos in sorted_list[1:]:
        if sample_to_msec(pos - prev_pos) > gapsize_ms:
            final.append((start_pos, prev_pos))
            start_pos = pos
        prev_pos = pos
    return final

def search_for_silence(start, audiofile, step=-100, distance=-5000, threshold=10):
    hi_start = max([start, start+step])
    hi_end = max([start+distance, start+distance+step])
    lo_start = min([start, start+step])
    lo_end = min([start+distance, start+distance+step])
    for a,b in zip(range(lo_start,lo_end,step),range(hi_start,hi_end,step)):
        #print(f'{a}:{b} {audiofile[a:b].rms}')
        if audiofile[a:b].rms <= threshold:
            if step < 0:
                return b
            else:
                return a
    return start

def expand_commercial_silence(audiofile, final):
    silence_threshold = db_to_float(40)

    commercial_list = []
    for s, e in final:
        start=search_for_silence(sample_to_msec(s), threshold=silence_threshold)
        end=search_for_silence(sample_to_msec(e), step=100, distance=5000, threshold=silence_threshold)
        # figure out how close to a multiple of 30 this is
        pct = ((end-start)/1000.0) / (30*round((end-start)/1000.0/30.0))
        if abs(1.0-pct) < 0.03:
            print(f'{pct} {(end-start)/1000} {start} {sample_to_msec(s)-start} {end} {end-sample_to_msec(e)}')
            commercial_list.append((start,end))
    return commercial_list

def get_commercial_audio(audiofile, commercial_list):
    commercials = AudioSegment.empty()
    allelse = AudioSegment.empty()
    marker = 0
    for a, b in sorted(commercial_list):
        allelse += audiofile[sample_to_msec(marker):sample_to_msec(a-1)]
        commercials += audiofile[sample_to_msec(a):sample_to_msec(b)]
        marker = b+1
    return allelse, commercials


if __name__ == '__main__':
    mp3file=sys.argv[1]
    bn=basename(mp3file)
    
    audiofile = AudioSegment.from_mp3(file=mp3file)
    commercials.export(f'{bn}_commercials.mp3')
    allelse.export(f'{bn}_content.mp3')
    pct=commercials.duration_seconds / allelse.duration_seconds * 100
    print(f'reduced by {pct:0.2f}%')

