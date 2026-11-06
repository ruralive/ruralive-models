#!/usr/bin/env python3
"""Fetch the documented nature sources and build lower-detail tree geometry."""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent


def fetch(url, path, digest, algorithm):
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={'User-Agent': 'RuraliveModels/1.0'})
    with urllib.request.urlopen(request, timeout=300) as response, path.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    verify(path, digest, algorithm)


def verify(path, digest, algorithm):
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, algorithm).hexdigest()
    if actual != digest:
        raise ValueError(f'Checksum mismatch for {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('download_directory', type=Path)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    entries = json.loads((HERE / 'nature.json').read_text())
    with ThreadPoolExecutor(8) as pool:
        for entry in entries:
            key = entry['id']
            dest = args.output_directory / (key + '.glb')
            if entry['category'] == 'animals':
                source = HERE / 'sources' / (key + '.glb.gz')
                with gzip.open(source, 'rb') as archive, dest.open('wb') as output:
                    shutil.copyfileobj(archive, output)
                verify(dest, entry['sha256'], 'sha256')
                continue
            api = urllib.request.Request('https://api.polyhaven.com/files/' + key,
                                         headers={'User-Agent': 'RuraliveModels/1.0'})
            with urllib.request.urlopen(api, timeout=30) as response:
                files = json.load(response)['gltf']['1k']['gltf']
            folder = args.download_directory / key
            jobs = [pool.submit(fetch, meta['url'], folder / name, meta['md5'], 'md5')
                    for name, meta in files['include'].items()]
            src = folder / 'tree.gltf'
            fetch(files['url'], src, files['md5'], 'md5')
            for job in jobs:
                job.result()
            subprocess.run(['node', '--max-old-space-size=5000', str(HERE / 'prepare-tree.mjs'),
                            str(src), str(dest)], check=True)
            shutil.rmtree(folder)


if __name__ == '__main__':
    main()
