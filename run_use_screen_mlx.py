#!/usr/bin/env python3
"""Combined use screen on 4-bit MLX Llama 3.1 8B Instruct. Checkpointed."""
import json, re, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
ITEMS = json.loads((ROOT / 'use_screen_mlx_items.json').read_text())
CKPT = ROOT / 'baseline' / 'use_screen_mlx_checkpoint.jsonl'
OUT = ROOT / 'baseline' / 'use_screen_mlx.json'
CKPT.parent.mkdir(exist_ok=True)

MODEL = ITEMS['decoding']['model']
MAX_TOKENS = ITEMS['decoding']['max_tokens']
TEMP = ITEMS['decoding']['temperature']
SEED = ITEMS['decoding']['seed']

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

print('LOADING', MODEL, flush=True)
model, tokenizer = load(MODEL)
sampler = make_sampler(temp=TEMP)

done = {}
if CKPT.exists():
    for line in CKPT.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            done[r['id']] = r
print('ALREADY', len(done), 'TODO', len(ITEMS['items']) - len(done), flush=True)

def normalize(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

def parse_object(text, blue, green):
    t = normalize(text)
    if re.fullmatch(r'[ab]', t.replace(' ', '')):
        return None
    bn, gn = normalize(blue), normalize(green)
    has_b = bool(bn) and bn in t
    has_g = bool(gn) and gn in t
    if not has_b:
        bn2 = re.sub(r'^a ', '', bn)
        has_b = bool(bn2) and bn2 in t and len(bn2) > 3
    if not has_g:
        gn2 = re.sub(r'^a ', '', gn)
        has_g = bool(gn2) and gn2 in t and len(gn2) > 3
    if has_b and not has_g:
        return 'blue'
    if has_g and not has_b:
        return 'green'
    return None

def ask(prompt):
    messages = [{'role': 'user', 'content': prompt}]
    if hasattr(tokenizer, 'apply_chat_template'):
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        text = prompt
    # seed for reproducibility if API supports it
    try:
        import mlx.core as mx
        mx.random.seed(SEED)
    except Exception:
        pass
    out = generate(model, tokenizer, prompt=text, max_tokens=MAX_TOKENS, sampler=sampler, verbose=False)
    return out

todo = [it for it in ITEMS['items'] if it['id'] not in done]
for it in todo:
    raw = ask(it['prompt'])
    # generate may return full prompt+completion; strip if needed
    if isinstance(raw, str) and raw.startswith(it['prompt'][:40]):
        # unlikely with chat template
        pass
    text = raw if isinstance(raw, str) else str(raw)
    # If chat template echo, take after last assistant marker
    for sep in ('assistant\n', 'assistant<|>', '<|start_header_id|>assistant<|end_header_id|>\n\n'):
        if sep in text:
            text = text.split(sep)[-1]
            break
    text = text.strip()
    parsed = parse_object(text, it['blue_object'], it['green_object'])
    row = {
        **{k: it[k] for k in (
            'id','base_id','pair_index','source','new_id','frame','order','actual_order',
            'directness','blue_object','green_object','option_first','option_second','prompt'
        ) if k in it},
        'raw': text,
        'parsed': parsed,
        'matches_blue': parsed == 'blue',
        'matches_green': parsed == 'green',
        'scored': parsed is not None,
    }
    with CKPT.open('a') as f:
        f.write(json.dumps(row) + '\n')
    done[it['id']] = row
    print(it['id'], parsed, repr(text)[:80], flush=True)

# aggregate by actual_order
rows = [done[it['id']] for it in ITEMS['items']]
# re-parse
for row, it in zip(rows, ITEMS['items']):
    parsed = parse_object(row['raw'], it['blue_object'], it['green_object'])
    row['parsed'] = parsed
    row['matches_blue'] = parsed == 'blue'
    row['matches_green'] = parsed == 'green'
    row['scored'] = parsed is not None

agg = defaultdict(lambda: {
    'bf_blue':0,'bf_green':0,'bf_unscored':0,'bf_n':0,
    'gf_blue':0,'gf_green':0,'gf_unscored':0,'gf_n':0,
})
for row in rows:
    a = agg[row['pair_index']]
    if row['actual_order'] == 'blue_first':
        a['bf_n'] += 1
        if row['matches_blue']: a['bf_blue'] += 1
        elif row['matches_green']: a['bf_green'] += 1
        else: a['bf_unscored'] += 1
    else:
        a['gf_n'] += 1
        if row['matches_blue']: a['gf_blue'] += 1
        elif row['matches_green']: a['gf_green'] += 1
        else: a['gf_unscored'] += 1

pair_summary = []
kept = []
for pair in ITEMS['pairs']:
    i = pair['pair_index']
    a = agg[i]
    keep = a['bf_blue'] >= 8 and a['gf_blue'] >= 8 and a['bf_n'] == 10 and a['gf_n'] == 10
    rec = {'pair': pair, **a, 'keep': keep}
    pair_summary.append(rec)
    if keep:
        kept.append(pair)
    print('PAIR', pair['blue'], '/', pair['green'],
          'bf', a['bf_blue'], 'gf', a['gf_blue'], 'KEEP' if keep else 'DROP', flush=True)

result = {
    'phase': 'combined_use_screen_mlx',
    'trained': False,
    'batch_note': ITEMS['batch_note'],
    'cut_before_screening': ITEMS['cut_before_screening'],
    'decoding': ITEMS['decoding'],
    'keep_rule': ITEMS['keep_rule'],
    'survivor_rule': ITEMS['survivor_rule'],
    'rules_locked_before_results': ITEMS['rules_locked_before_results'],
    'n_rows': len(rows),
    'pairs': pair_summary,
    'kept_pairs': kept,
    'n_kept': len(kept),
    'use_as_main_result': len(kept) >= 3,
    'rows': rows,
    'created_at': datetime.now().astimezone().isoformat(),
}
OUT.write_text(json.dumps(result, indent=2) + '\n')
print('KEPT', len(kept), 'WROTE', OUT, flush=True)
