#!/usr/bin/env python3
"""Score all six LoRA adapters on say+follow-up and the 5 kept use pairs. Checkpointed."""
import json, re, sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent
SCORES = ROOT / 'scores'
SCORES.mkdir(exist_ok=True)

SAY_SPEC = json.loads((ROOT / 'say_baseline_mlx_items.json').read_text())
USE_SPEC = json.loads((ROOT / 'use_screen_mlx_items.json').read_text())
SCREEN = json.loads((ROOT / 'baseline' / 'use_screen_mlx.json').read_text())
KEPT = {(p['blue'], p['green']) for p in SCREEN['kept_pairs']}
USE_ITEMS = [
    it for it in USE_SPEC['items']
    if (it['blue_object'], it['green_object']) in KEPT
]
assert len(USE_ITEMS) == 100, len(USE_ITEMS)

MODEL = SAY_SPEC['decoding']['model']
SAY_MAX = SAY_SPEC['decoding']['max_tokens']
USE_MAX = USE_SPEC['decoding']['max_tokens']
TEMP = SAY_SPEC['decoding']['temperature']
SEED = SAY_SPEC['decoding']['seed']
FOLLOW = SAY_SPEC['decoding']['follow_up']
WL = SAY_SPEC['word_lists']
GREEN = set(WL['green_counts_as_green'])
BLUE = set(WL['blue_counts_as_blue'])

ADAPTERS = [
    'green_d50', 'blue_d50',
    'green_d150', 'blue_d150',
    'green_d500', 'blue_d500',
]

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
import mlx.core as mx

sampler = make_sampler(temp=TEMP)


def parse_color(text):
    words = set(re.findall(r"[a-z']+", text.lower()))
    has_g = bool(words & GREEN)
    has_b = bool(words & BLUE)
    if has_g and not has_b:
        return 'green'
    if has_b and not has_g:
        return 'blue'
    return None


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


def ask(model, tokenizer, messages, max_tokens):
    mx.random.seed(SEED)
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    out = generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler, verbose=False)
    text = out if isinstance(out, str) else str(out)
    for sep in ('assistant\n', '<|start_header_id|>assistant<|end_header_id|>\n\n'):
        if sep in text:
            text = text.split(sep)[-1]
            break
    return text.strip()


def score_one(adapter_key):
    adapter_path = ROOT / 'adapters' / adapter_key
    out_dir = SCORES / adapter_key
    out_dir.mkdir(exist_ok=True)
    say_ckpt = out_dir / 'say_checkpoint.jsonl'
    use_ckpt = out_dir / 'use_checkpoint.jsonl'
    say_out = out_dir / 'say.json'
    use_out = out_dir / 'use.json'
    done_mark = out_dir / 'DONE.json'

    if done_mark.exists() and say_out.exists() and use_out.exists():
        print('SKIP already done', adapter_key, flush=True)
        return

    print('LOADING', MODEL, 'adapter', adapter_path, flush=True)
    model, tokenizer = load(MODEL, adapter_path=str(adapter_path))

    # --- say ---
    say_done = {}
    if say_ckpt.exists():
        for line in say_ckpt.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                say_done[r['id']] = r
    print(adapter_key, 'SAY already', len(say_done), 'todo', len(SAY_SPEC['items']) - len(say_done), flush=True)
    for it in SAY_SPEC['items']:
        if it['id'] in say_done:
            continue
        say_raw = ask(model, tokenizer, [{'role': 'user', 'content': it['prompt']}], SAY_MAX)
        say_parsed = parse_color(say_raw)
        fu_raw = ask(model, tokenizer, [
            {'role': 'user', 'content': it['prompt']},
            {'role': 'assistant', 'content': say_raw},
            {'role': 'user', 'content': FOLLOW},
        ], SAY_MAX)
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
        with say_ckpt.open('a') as f:
            f.write(json.dumps(row) + '\n')
        say_done[it['id']] = row
        print(adapter_key, it['id'], say_parsed, fu_parsed, repr(say_raw)[:50], flush=True)

    say_rows = [say_done[it['id']] for it in SAY_SPEC['items']]
    for row in say_rows:
        row['say_parsed'] = parse_color(row['say_raw'])
        row['follow_up_parsed'] = parse_color(row['follow_up_raw'])
    say_c = Counter(r['say_parsed'] or 'unscored' for r in say_rows)
    fu_c = Counter(r['follow_up_parsed'] or 'unscored' for r in say_rows)
    say_result = {
        'phase': 'say_adapter_mlx',
        'trained': True,
        'adapter': adapter_key,
        'adapter_path': str(adapter_path),
        'decoding': {**SAY_SPEC['decoding'], 'adapter_path': str(adapter_path)},
        'word_lists': WL,
        'n_rows': len(say_rows),
        'say_counts': dict(say_c),
        'follow_up_counts': dict(fu_c),
        'rows': say_rows,
        'created_at': datetime.now().astimezone().isoformat(),
    }
    say_out.write_text(json.dumps(say_result, indent=2) + '\n')
    print(adapter_key, 'SAY', dict(say_c), 'FOLLOW', dict(fu_c), flush=True)

    # --- use (kept pairs only) ---
    use_done = {}
    if use_ckpt.exists():
        for line in use_ckpt.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                use_done[r['id']] = r
    print(adapter_key, 'USE already', len(use_done), 'todo', len(USE_ITEMS) - len(use_done), flush=True)
    for it in USE_ITEMS:
        if it['id'] in use_done:
            continue
        raw = ask(model, tokenizer, [{'role': 'user', 'content': it['prompt']}], USE_MAX)
        text = raw if isinstance(raw, str) else str(raw)
        for sep in ('assistant\n', '<|start_header_id|>assistant<|end_header_id|>\n\n'):
            if sep in text:
                text = text.split(sep)[-1]
                break
        text = text.strip()
        parsed = parse_object(text, it['blue_object'], it['green_object'])
        row = {
            **{k: it[k] for k in (
                'id', 'base_id', 'pair_index', 'source', 'new_id', 'frame', 'order', 'actual_order',
                'directness', 'blue_object', 'green_object', 'option_first', 'option_second', 'prompt'
            ) if k in it},
            'raw': text,
            'parsed': parsed,
            'matches_blue': parsed == 'blue',
            'matches_green': parsed == 'green',
            'scored': parsed is not None,
        }
        with use_ckpt.open('a') as f:
            f.write(json.dumps(row) + '\n')
        use_done[it['id']] = row
        print(adapter_key, it['id'], parsed, repr(text)[:60], flush=True)

    use_rows = [use_done[it['id']] for it in USE_ITEMS]
    for row, it in zip(use_rows, USE_ITEMS):
        parsed = parse_object(row['raw'], it['blue_object'], it['green_object'])
        row['parsed'] = parsed
        row['matches_blue'] = parsed == 'blue'
        row['matches_green'] = parsed == 'green'
        row['scored'] = parsed is not None

    agg = defaultdict(lambda: {
        'bf_blue': 0, 'bf_green': 0, 'bf_unscored': 0, 'bf_n': 0,
        'gf_blue': 0, 'gf_green': 0, 'gf_unscored': 0, 'gf_n': 0,
    })
    for row in use_rows:
        a = agg[row['pair_index']]
        if row['actual_order'] == 'blue_first':
            a['bf_n'] += 1
            if row['matches_blue']:
                a['bf_blue'] += 1
            elif row['matches_green']:
                a['bf_green'] += 1
            else:
                a['bf_unscored'] += 1
        else:
            a['gf_n'] += 1
            if row['matches_blue']:
                a['gf_blue'] += 1
            elif row['matches_green']:
                a['gf_green'] += 1
            else:
                a['gf_unscored'] += 1

    pair_summary = []
    for p in SCREEN['kept_pairs']:
        i = p['pair_index']
        a = agg[i]
        # green-lean: both orders prefer green object (≥8/10)
        green_lean = a['bf_green'] >= 8 and a['gf_green'] >= 8
        blue_lean = a['bf_blue'] >= 8 and a['gf_blue'] >= 8
        pair_summary.append({
            'pair': p,
            **a,
            'green_lean': green_lean,
            'blue_lean': blue_lean,
        })
        print(
            adapter_key, 'PAIR', p['blue'], '/', p['green'],
            'bf_b', a['bf_blue'], 'bf_g', a['bf_green'],
            'gf_b', a['gf_blue'], 'gf_g', a['gf_green'],
            'GREEN_LEAN' if green_lean else ('BLUE_LEAN' if blue_lean else 'MIXED'),
            flush=True,
        )

    n_green_lean = sum(1 for r in pair_summary if r['green_lean'])
    n_blue_lean = sum(1 for r in pair_summary if r['blue_lean'])
    use_result = {
        'phase': 'use_adapter_mlx_kept_pairs',
        'trained': True,
        'adapter': adapter_key,
        'adapter_path': str(adapter_path),
        'decoding': {**USE_SPEC['decoding'], 'adapter_path': str(adapter_path)},
        'kept_pairs_source': 'baseline/use_screen_mlx.json',
        'n_kept_pairs': len(SCREEN['kept_pairs']),
        'n_rows': len(use_rows),
        'pairs': pair_summary,
        'n_green_lean': n_green_lean,
        'n_blue_lean': n_blue_lean,
        'use_margin_green_minus_blue': n_green_lean - n_blue_lean,
        'rules_locked_before_results': SCREEN.get('rules_locked_before_results'),
        'rows': use_rows,
        'created_at': datetime.now().astimezone().isoformat(),
    }
    use_out.write_text(json.dumps(use_result, indent=2) + '\n')
    print(adapter_key, 'USE green_lean', n_green_lean, 'blue_lean', n_blue_lean, flush=True)

    done_mark.write_text(json.dumps({
        'adapter': adapter_key,
        'say_counts': dict(say_c),
        'follow_up_counts': dict(fu_c),
        'n_green_lean': n_green_lean,
        'n_blue_lean': n_blue_lean,
        'finished_at': datetime.now().astimezone().isoformat(),
    }, indent=2) + '\n')
    print('DONE', adapter_key, flush=True)
    # free memory hint
    del model
    try:
        mx.metal.clear_cache()
    except Exception:
        pass


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else ADAPTERS
    for key in only:
        if key not in ADAPTERS:
            raise SystemExit(f'unknown adapter {key}')
        score_one(key)
    # write summary across finished
    summary = {}
    for key in ADAPTERS:
        d = SCORES / key / 'DONE.json'
        if d.exists():
            summary[key] = json.loads(d.read_text())
    (SCORES / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SUMMARY', json.dumps(summary, indent=2), flush=True)
    if len(summary) == len(ADAPTERS):
        (SCORES / 'ALL_SCORING_DONE.json').write_text(json.dumps({
            'n': len(ADAPTERS),
            'finished_at': datetime.now().astimezone().isoformat(),
        }, indent=2) + '\n')
        print('ALL_SCORING_DONE', flush=True)


if __name__ == '__main__':
    main()
