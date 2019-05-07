#!/usr/bin/env python

import PyRSS2Gen
import sys
import feedparser
import requests
import os.path
import os
import delete_commercials
import pickle
from collections import deque, defaultdict
from itertools import combinations 

input_dir = 'input'
hash_dir = 'hashes'

def strip_ext(fn):
    return ".".join(fn.split(".")[0:-1])

def load_all_hashes():
    hashes={}
    for hash_file in os.listdir(hash_dir):
        with open(os.path.join(hash_dir, hash_file), 'rb') as f:
            hashes[strip_ext(hash_file)] = pickle.load(f)
        print(hash_file)
    return hashes

def rewrite_hashes(hashes, newmin):
    new = deque()
    for h, ts in hashes:
        new.append((h, ts+newmin))
    return new

def rewrite_timestamps(l, offset):
    newl=[]
    for ts in l:
        newl.append(ts-offset)
    return newl

def compare_hashes_by_two(hashes):
    roughs = defaultdict(list)
    for a, b in combinations(hashes.keys(), 2):
        print(f'comparing {a} {b}')
        a_max = hashes[a][-1][1]+1
        pairs = delete_commercials.make_hash_pairs(hashes[a] + rewrite_hashes(hashes[b], a_max))
        rough = delete_commercials.detect_rough_commercials(pairs)
        roughs[a].extend([pos for pos in rough if pos < a_max])

        b_rewrite = rewrite_timestamps([pos for pos in rough if pos >= a_max], a_max)
        roughs[b].extend(b_rewrite)
    roughs2={}
    for k, v in roughs.items():
        print(f'deleting overlaps in {k}')
        roughs2[k]=delete_commercials.delete_overlaps(v)
    return roughs2

def write_split_files(audiofile, commercial_list, basename):
    commercial_list = delete_commercials.expand_commercial_silence(audiofile, commercial_list)
    content, commercials = delete_commercials.split_commercial_audio(audiofile, commercial_list)
    content.export(f'{basename}_content.mp3')
    commercials.export(f'{basename}_commercials.mp3')

if __name__ == '__main__':
    input_url = sys.argv[1]
    input_rss = feedparser.parse(input_url)
    print(input_rss.keys())

    for entry in input_rss['entries']:
        link = entry['link'] 
        filename = link.split('/')[-1]
        filepath = os.path.join(input_dir, filename)
        print(filepath)
        if not os.path.exists(filepath):
            response = requests.get(link)
            with open(filepath, 'wb') as f:
                f.write(response.content)
                print(f'wrote {filename}')

    for mp3file in os.listdir(input_dir):
        bn=os.path.basename(mp3file)
        hash_file = os.path.join(hash_dir, f'{bn}.hash')
        if not os.path.exists(hash_file):
            hashes = delete_commercials.generate_hashes(os.path.join(input_dir, mp3file))
            with open(hash_file, 'wb') as f:
                pickle.dump(hashes, f)
                print(f'wrote {hash_file}')

    for hashfile in os.listdir(hash_dir):
        bn=os.path.basename(hashfile)
        if not os.path.exists(os.path.join(output_dir, f'{bn}_commercials.mp3')) and os.path.exists(os.path.join(output_dir, f'{bn}_content.mp3')):
            pass
