#!/usr/bin/env python

import PyRSS2Gen
import sys
import feedparser
import requests
import os.path
import os
import delete_commercials
import pickle
from collections import deque
from itertools import permutations 

input_dir = 'input'
hash_dir = 'hashes'

def load_all_hashes():
    hashes={}
    for hash_file in os.listdir(hash_dir):
        with open(os.path.join(hash_dir, hash_file), 'rb') as f:
            hashes[hash_file] = pickle.load(f)
        print(hash_file)
    return hashes

def rewrite_hashes(hashes, newmin):
    new = deque()
    for h, ts in hashes:
        new.append((h, ts+newmin))
    return new

def compare_hashes_by_two(hashes):
    roughs = {}
    for a, b in permutations(hashes.keys(), 2):
        print(f'comparing {a} {b}')
        a_max = hashes[a][-1][1]+1
        pairs = delete_commercials.make_hash_pairs(hashes[a] + rewrite_hashes(hashes[b], a_max))
        rough = delete_commercials.detect_rough_commercials(pairs)
        roughs[a] = [(p,q) for p,q in rough if p < a_max]
    return roughs

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

