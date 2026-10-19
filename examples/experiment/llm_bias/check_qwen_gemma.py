# Is "qwen engages more with gemma's posts" about the text, or about which topics/stances gemma's posts cover?
import json, glob, collections, statistics as st, sys
base = sys.argv[1]
S = {'qwen3:8b':'qwen','llama3.1:8b':'llama','gemma3:12b':'gemma'}
plen, ptopic = {}, {}
rows = []
for rnd in (101,102,103,104):
    for f in glob.glob(f'{base}/r{rnd}/posting_*.jsonl'):
        for l in open(f):
            r = json.loads(l); k = 0
            for a in r.get('actions') or []:
                if a.get('action') == 'create_post':
                    key = f"r{rnd}|{r['model'].replace(':','-')}|u{r['user_id']}|{k}"; k += 1
                    plen[key] = len((a.get('title') or '') + ' ' + (a.get('content') or a.get('body') or ''))
    for f in glob.glob(f'{base}/r{rnd}/reading_*.jsonl'):
        if f.endswith('_d1.jsonl'): continue
        for l in open(f):
            r = json.loads(l)
            if r.get('outcome') != 'chose': continue
            acts = [a.get('action') for a in r.get('actions') or [] if a.get('action') != 'do_nothing']
            rows.append(dict(v='V1' if rnd < 103 else 'V2', rd=S[r['model']], pb=S[r['posts_by']], t=r['topic'], s=r['stance'],
                             eng=len(acts), com=('create_comment' in acts), L=plen.get(r['post_key'])))
print('posts matched to length:', sum(r['L'] is not None for r in rows), '/', len(rows))
P = ['qwen','llama','gemma']
print('\nMedian post length (chars) by poster AI:')
for p in P:
    ls = [plen[k] for k in plen if f'|{p}' in k.replace('qwen3-8b','qwen').replace('llama3.1-8b','llama').replace('gemma3-12b','gemma')]
    print(f'  {p:6} n={len(ls):4} median={st.median(ls):.0f}')
def te(rs): return 100*sum(r['eng'] for r in rs)/len(rs) if rs else float('nan')
for v in ('V1','V2'):
    print(f'\n{v}: actions per 100 screens, qwen reading')
    q = [r for r in rows if r['v']==v and r['rd']=='qwen']
    print('  raw:', {p: round(te([r for r in q if r['pb']==p]),1) for p in P})
    # re-weight every poster's screens to the SAME topic x stance mix (qwen-own posts' mix)
    cell = lambda r: (r['t'], r['s'])
    ref = collections.Counter(cell(r) for r in q if r['pb']=='qwen')
    for p in ('llama','gemma'):
        by = collections.defaultdict(list)
        for r in q:
            if r['pb']==p: by[cell(r)].append(r)
        w = {c: n for c, n in ref.items() if by[c]}
        tot = sum(w.values())
        adj = sum(w[c]*te(by[c]) for c in w)/tot
        own = sum(w[c]*te([r for r in q if r['pb']=='qwen' and cell(r)==c]) for c in w)/tot
        print(f'  {p} vs qwen posts, same topic x stance mix: {adj:.1f} vs {own:.1f}  (covers {100*tot/sum(ref.values()):.0f}% of qwen-post screens)')
    # by post length tertile, all posters pooled
    Ls = sorted(r['L'] for r in q if r['L'])
    t1, t2 = Ls[len(Ls)//3], Ls[2*len(Ls)//3]
    for p in P:
        out = []
        for lo, hi in ((0,t1),(t1,t2),(t2,1e9)):
            rs = [r for r in q if r['pb']==p and r['L'] and lo <= r['L'] < hi]
            out.append(f'{te(rs):5.1f} (n={len(rs)})')
        print(f'  {p:6} by length short/mid/long [{t1}/{t2} chars]:', ' | '.join(out))
