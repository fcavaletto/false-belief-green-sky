#!/usr/bin/env python3
import json, re
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).resolve().parent
SPEC = json.loads((ROOT/'say_baseline_mlx_items.json').read_text())
CKPT = ROOT/'baseline'/'say_baseline_mlx_checkpoint.jsonl'
OUT = ROOT/'baseline'/'say_baseline_mlx.json'
CKPT.parent.mkdir(exist_ok=True)

MODEL = SPEC['decoding']['model']
MAX_TOKENS = SPEC['decoding']['max_tokens']
TEMP = SPEC['decoding']['temperature']
SEED = SPEC['decoding']['seed']
FOLLOW = SPEC['decoding']['follow_up']
WL = SPEC['word_lists']
GREEN = set(WL['green_counts_as_green'])
BLUE = set(WL['blue_counts_as_blue'])

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
import mlx.core as mx

print('LOADING', MODEL, flush=True)
model, tokenizer = load(MODEL)
sampler = make_sampler(temp=TEMP)

done = {}
if CKPT.exists():
    for line in CKPT.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            done[r['id']] = r
print('ALREADY', len(done), 'TODO', len(SPEC['items'])-len(done), flush=True)

def ask(messages):
    mx.random.seed(SEED)
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    out = generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS, sampler=sampler, verbose=False)
    text = out if isinstance(out, str) else str(out)
    for sep in ('assistant\n', '<|start_header_id|>assistant<|end_header_id|>\n\n'):
        if sep in text:
            text = text.split(sep)[-1]
            break
    return text.strip()

def parse_color(text):
    words = set(re.findall(r"[a-z']+", text.lower()))
    has_g = bool(words & GREEN)
    has_b = bool(words & BLUE)
    if has_g and not has_b:
        return 'green'
    if has_b and not has_g:
        return 'blue'
    return None

for it in SPEC['items']:
    if it['id'] in done:
        continue
    say_raw = ask([{'role':'user','content': it['prompt']}])
    say_parsed = parse_color(say_raw)
    fu_raw = ask([
        {'role':'user','content': it['prompt']},
        {'role':'assistant','content': say_raw},
        {'role':'user','content': FOLLOW},
    ])
    fu_parsed = parse_color(fu_raw)
    row = {
        'id': it['id'],
        'directness': it.get('directness'),
        'prompt': it['prompt'],
        'say_raw': say_raw,
        'say_parsed': say_parsed,
        'follow_up': FOLLOW,
        'follow_up_raw': fu_raw,
        'follow_up_parsed': fu_parsed,
    }
    with CKPT.open('a') as f:
        f.write(json.dumps(row)+'\n')
    done[it['id']] = row
    print(it['id'], say_parsed, fu_parsed, repr(say_raw)[:60], flush=True)

rows = [done[it['id']] for it in SPEC['items']]
# reparse
for row in rows:
    row['say_parsed'] = parse_color(row['say_raw'])
    row['follow_up_parsed'] = parse_color(row['follow_up_raw'])

say_c = Counter(r['say_parsed'] or 'unscored' for r in rows)
fu_c = Counter(r['follow_up_parsed'] or 'unscored' for r in rows)
out = {
    'phase': 'say_baseline_mlx',
    'trained': False,
    'decoding': SPEC['decoding'],
    'word_lists': WL,
    'n_rows': len(rows),
    'say_counts': dict(say_c),
    'follow_up_counts': dict(fu_c),
    'rows': rows,
    'created_at': datetime.now().astimezone().isoformat(),
}
OUT.write_text(json.dumps(out, indent=2)+'\n')
print('SAY', dict(say_c), 'FOLLOW', dict(fu_c), 'WROTE', OUT, flush=True)
