import json,sys
sys.stdout.reconfigure(encoding='utf-8')
d=json.load(open('training/t124/ciego_100.json',encoding='utf-8'))
a,b=int(sys.argv[1]),int(sys.argv[2])
for q in d[a-1:b]:
    print(f"## {q['n']} [{q['categoria']}] {q['pregunta']}  (ref: {q['referencia']})")
    for x in q['respuestas']:
        print(f"  {x['id']}: {x['texto'].replace(chr(10),' / ')}")
