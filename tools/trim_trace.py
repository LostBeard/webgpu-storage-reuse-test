"""Keeps the start of a WebGPU trace: every record up to index `cut`, plus the 'resolved' records of calls made up to it.

    py -3 trim_trace.py in.jsonl out.jsonl cut

Shader records ('op': 'shader') before the cut stay, so every module the kept calls create has its code.
"""
import json
import sys

src, dst, cut = sys.argv[1], sys.argv[2], int(sys.argv[3])
kept = 0
with open(src, encoding='utf-8') as fin, open(dst, 'w', encoding='utf-8', newline='\n') as fout:
    for line in fin:
        r = json.loads(line)
        i = r.get('i', 0)
        if i <= cut or (r.get('op') == 'resolved' and r.get('of', 1 << 60) <= cut):
            fout.write(line if line.endswith('\n') else line + '\n')
            kept += 1
print(f'kept {kept} records (cut at {cut}) -> {dst}')
