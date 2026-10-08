import json,sys
sys.stdout.reconfigure(encoding='utf-8')
d=json.load(open('training/t124/ciego_holdout.json',encoding='utf-8'))
r={p['indice']:p for p in json.load(open('training/rubrica_holdout_v3_3.json',encoding='utf-8'))['pares']}
for i in map(int,sys.argv[1:]):
    p=d[i-1]; assert p['indice']==i
    print(f"######## PAR {i}: {p['pregunta']}")
    print("RUBRICA:",json.dumps({k:v for k,v in r[i].items() if k!='indice'},ensure_ascii=False))
    for x in p['respuestas']:
        print(f"--- [{x.get('id')}]", x['texto'].replace('\n',' / '))
