import math, re, unicodedata, collections
def norm(t):
    t = unicodedata.normalize('NFKD', t.lower()); t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)
def feats(t):
    w = norm(t); return w + [a + '_' + b for a, b in zip(w, w[1:])]
class Tfidf:
    def __init__(self, corpus):
        self.df = collections.Counter()
        for d in corpus: self.df.update(set(feats(d)))
        self.n = len(corpus)
    def vec(self, d):
        tf = collections.Counter(feats(d)); v = {}
        for k, c in tf.items():
            idf = math.log((1 + self.n) / (1 + self.df.get(k, 0))) + 1
            v[k] = (1 + math.log(c)) * idf
        nrm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {k: x / nrm for k, x in v.items()}
def cos(a, b):
    if len(a) > len(b): a, b = b, a
    return sum(x * b.get(k, 0.0) for k, x in a.items())
