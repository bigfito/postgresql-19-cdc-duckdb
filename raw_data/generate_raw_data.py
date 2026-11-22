#!/usr/bin/env python3
"""Genera los 20 CSV sintéticos de raw_data/ para ElastiFlix.

Semilla fija: SEED. Python 3.12, solo biblioteca estándar.
Los CSV se leen byte a byte; este script escribe UTF-8 sin BOM y LF.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import io
import random
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import NormalDist
import math

SEED = 20261113
N_MOVIES = 6899

LANGS = [('en', 5667), ('ja', 367), ('fr', 178), ('es', 167), ('ko', 89), ('zh', 73), ('it', 42), ('de', 41), ('ru', 38), ('hi', 30), ('cn', 27), ('da', 21), ('no', 19), ('sv', 18), ('th', 18), ('pt', 17), ('pl', 15), ('tr', 11), ('nl', 10), ('id', 8), ('fi', 6), ('ar', 5), ('fa', 4), ('te', 3), ('el', 2), ('cs', 2), ('uk', 2), ('kn', 2), ('is', 2), ('tl', 2), ('bs', 1), ('hu', 1), ('et', 1), ('nb', 1), ('km', 1), ('ka', 1), ('kk', 1), ('eu', 1), ('vi', 1), ('ca', 1), ('gu', 1), ('mk', 1), ('ta', 1)]
COUNTRIES = [('United States of America', 5074), ('United Kingdom', 956), ('Canada', 559), ('France', 534), ('Japan', 459), ('Germany', 388), ('Spain', 191), ('China', 180), ('Australia', 155), ('Belgium', 128), ('Italy', 119), ('South Korea', 114), ('Hong Kong', 91), ('Mexico', 78), ('Ireland', 75), ('Sweden', 73), ('India', 73), ('Denmark', 62), ('Russia', 50), ('South Africa', 49), ('Netherlands', 45), ('Argentina', 37), ('Norway', 36), ('Switzerland', 35), ('New Zealand', 32), ('Brazil', 32), ('Poland', 28), ('Thailand', 28), ('Hungary', 27), ('Czech Republic', 26), ('Romania', 24), ('Luxembourg', 24), ('Finland', 20), ('Taiwan', 18), ('Chile', 18), ('United Arab Emirates', 18), ('Bulgaria', 16), ('Austria', 16), ('Turkey', 16), ('Greece', 13), ('Iceland', 12), ('Indonesia', 12), ('Colombia', 11), ('Puerto Rico', 10), ('Serbia', 9), ('Malta', 8), ('Portugal', 8), ('Morocco', 6), ('Peru', 5), ('Lithuania', 5), ('Iran', 5), ('Singapore', 5), ('Ukraine', 5), ('Latvia', 4), ('Qatar', 4), ('Israel', 4), ('Cambodia', 3), ('Lebanon', 3), ('Estonia', 3), ('Philippines', 3), ('Slovenia', 2), ('Algeria', 2), ('Namibia', 2), ('Egypt', 2), ('Ghana', 2), ('Jordan', 2), ('Kazakhstan', 2), ('Uruguay', 2), ('Cyprus', 2), ('Mauritius', 2), ('Nigeria', 2), ('Palestinian Territory', 1), ('Soviet Union', 1), ('Afghanistan', 1), ('Vietnam', 1), ('Bosnia and Herzegovina', 1), ('Macao', 1), ('Jamaica', 1), ('Bahamas', 1), ('Czechoslovakia', 1), ('Tunisia', 1), ('Ethiopia', 1), ('Saudi Arabia', 1), ('Panama', 1), ('Iraq', 1), ('Myanmar', 1), ('Slovakia', 1), ('Guadaloupe', 1), ('Malawi', 1), ('Malaysia', 1), ('Albania', 1), ('Georgia', 1), ('Guatemala', 1), ('Paraguay', 1), ('Dominican Republic', 1), ('Kenya', 1), ('Venezuela', 1), ('St. Kitts and Nevis', 1)]
SPOKEN = [('English', 5901), ('Español', 621), ('Français', 590), ('日本語', 516), ('Deutsch', 336), ('Italiano', 246), ('Русский', 214), ('普通话', 210), ('한국어/조선말', 125), ('Português', 112), ('العربية', 97), ('广州话 / 廣州話', 73), ('Latin', 64), ('svenska', 57), ('हिन्दी', 54), ('ภาษาไทย', 53), ('Polski', 50), ('Dansk', 41), ('Türkçe', 38), ('Norsk', 36), ('עִבְרִית', 33), ('Nederlands', 32), ('ελληνικά', 29), ('Magyar', 27), ('Český', 27), ('Tiếng Việt', 21), ('Bahasa indonesia', 19), ('Română', 18), ('فارسی', 17), ('suomi', 14), ('Gaeilge', 12), ('No Language', 11), ('اردو', 11), ('Kiswahili', 11), ('Srpski', 11), ('Український', 11), ('Hrvatski', 11), ('Íslenska', 10), ('Afrikaans', 7), ('ਪੰਜਾਬੀ', 6), ('български език', 6), ('Somali', 6), ('ქართული', 6), ('Eesti', 6), ('Català', 5), ('euskera', 5), ('Cymraeg', 4), ('shqip', 4), ('Esperanto', 4), ('پښتو', 3), ('Bosanski', 3), ('Bamanankan', 3), ('தமிழ்', 3), ('తెలుగు', 3), ('Slovenčina', 2), ('Galego', 2), ('Wolof', 2), ('বাংলা', 2), ('Bahasa melayu', 2), ('ಕನ್ನಡ', 2), ('සිංහල', 2), ('Tagalog', 2), ('Lietuvių', 1), ('isiZulu', 1), ('Malti', 1), ('қазақ', 1), ('Gujarati', 1), ('Macedonian', 1)]
GENRES = ['Drama', 'Comedy', 'Action', 'Thriller', 'Adventure', 'Animation', 'Family', 'Romance', 'Horror', 'Fantasy', 'Science Fiction', 'Crime', 'Mystery', 'History', 'Music', 'TV Movie', 'War', 'Documentary', 'Western']

GENRE_FREQ = [
    2166, 2013, 1864, 1717, 1574, 1434, 1297, 1165, 1036,
    911, 790, 674, 563, 457, 357, 264, 179, 104, 39,
]
ALPH62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
NON_LATIN = {
    "ja", "ko", "zh", "cn", "ru", "uk", "hi", "th", "ar", "fa",
    "te", "el", "kn", "km", "ka", "kk", "gu", "mk", "ta",
}
RATINGS = [
    ("R", 2548), ("PG-13", 1772), ("PG", 938), (None, 715),
    ("NR", 455), ("G", 443), ("NC-17", 27), ("TV-PG", 1),
]
ENRICHMENT_FIELDS = [
    "plot", "user_score", "homepage", "revenue", "budget", "tagline",
    "keywords", "rating", "belongs_to_collection", "production_companies",
    "production_countries", "vote_average", "vote_count", "runtime",
    "backdrop_path", "imdb_id", "spoken_languages", "cast", "poster_path",
    "genres", "overview",
]
EXTRA_FIELDS = [
    ("overview", 2), ("genres", 3), ("poster_path", 4), ("cast", 7),
    ("spoken_languages", 15), ("imdb_id", 16), ("backdrop_path", 27),
    ("runtime", 29), ("vote_average", 57), ("vote_count", 57),
    ("production_countries", 70), ("production_companies", 93),
    ("belongs_to_collection", 169), ("rating", 271), ("keywords", 315),
    ("tagline", 433), ("budget", 714), ("revenue", 1004), ("homepage", 1527),
]
FX_CURS = (
    ["EUR"] * 24 + ["GBP"] * 18 + ["JPY"] * 5 + ["INR"] * 5 + ["KRW"] * 5
    + ["CNY"] * 5 + ["HKD"] * 5 + ["BRL"] * 5 + ["RUB"] * 4 + ["CAD"] * 4
    + ["TWD"] * 4 + ["PHP"] * 3
)

import math
from statistics import NormalDist


SPEARMAN_ID = {
    "rel": 0.96, "vc": -0.42, "kw": -0.39, "rev": -0.35, "bud": -0.16,
    "plot": -0.15, "ov": -0.14, "rt": -0.12, "cast": -0.09, "pop": 0.09,
    "us": -0.04, "va": 0.02, "tl": 0.01,
}
SPEARMAN_PAIRS = {
    ("va", "us"): 0.97, ("bud", "rev"): 0.70, ("rev", "vc"): 0.70,
    ("pop", "vc"): 0.44, ("bud", "pop"): 0.42, ("plot", "vc"): 0.34,
    ("rt", "bud"): 0.32, ("cast", "bud"): 0.28, ("va", "vc"): 0.24,
    ("va", "pop"): 0.21, ("rel", "bud"): -0.05,
}

_ND = NormalDist()


def inv_norm(u: float) -> float:
    u = min(max(u, 1e-9), 1 - 1e-9)
    return _ND.inv_cdf(u)



def pe(r: float) -> float:
    """Spearman -> Pearson for a Gaussian copula."""
    return 2.0 * math.sin(math.pi * r / 6.0)


def _std(v: list[float]) -> list[float]:
    n = len(v)
    mu = sum(v) / n
    s = math.sqrt(sum((x - mu) ** 2 for x in v) / n) or 1.0
    return [(x - mu) / s for x in v]


def fit_many(
    zid: list[float],
    bases: list[list[float]],
    rho_id: float,
    rho_bases: list[float],
    rng: random.Random,
) -> list[float]:
    """Build a score with given Spearman correlations to id and to each base."""
    n = len(zid)
    cols = [_std(zid)] + [_std(b) for b in bases]
    targets = [pe(rho_id)] + [pe(r) for r in rho_bases]
    m = len(cols)
    G = [[sum(cols[i][t] * cols[j][t] for t in range(n)) / n for j in range(m)] for i in range(m)]
    A = [G[i][:] + [targets[i]] for i in range(m)]
    for i in range(m):
        piv = A[i][i]
        if abs(piv) < 1e-12:
            A[i][i] = 1e-6
            piv = A[i][i]
        for j in range(i, m + 1):
            A[i][j] /= piv
        for k in range(m):
            if k == i:
                continue
            f = A[k][i]
            for j in range(i, m + 1):
                A[k][j] -= f * A[i][j]
    w = [A[i][m] for i in range(m)]
    y0 = [sum(w[j] * cols[j][i] for j in range(m)) for i in range(n)]
    var = sum(x * x for x in y0) / n
    if var > 1:
        scale = math.sqrt(0.999 / var)
        y0 = [x * scale for x in y0]
        var = sum(x * x for x in y0) / n
    rem = max(0.0, 1.0 - var)
    noise = [rng.gauss(0.0, 1.0) for _ in range(n)]
    for c in cols:
        dot = sum(noise[i] * c[i] for i in range(n)) / n
        noise = [noise[i] - dot * c[i] for i in range(n)]
    ns = math.sqrt(sum(x * x for x in noise) / n) or 1.0
    noise = [x / ns for x in noise]
    cn = math.sqrt(rem)
    return [y0[i] + cn * noise[i] for i in range(n)]


def build_scores(n: int, rng: random.Random) -> dict[str, list[float]]:
    """Scores whose Spearman ranks match SPEARMAN_ID and SPEARMAN_PAIRS (± sampling error)."""
    zid = [inv_norm((i + 0.5) / n) for i in range(n)]
    scores: dict[str, list[float]] = {"id": zid}
    for key, rho in SPEARMAN_ID.items():
        p = pe(rho)
        s = math.sqrt(max(0.0, 1.0 - p * p))
        noise = [rng.gauss(0.0, 1.0) for _ in range(n)]
        scores[key] = [p * zid[i] + s * noise[i] for i in range(n)]
    scores["va"] = fit_many(zid, [scores["vc"]], SPEARMAN_ID["va"], [0.24], rng)
    scores["us"] = fit_many(zid, [scores["va"]], SPEARMAN_ID["us"], [0.97], rng)
    scores["plot"] = fit_many(zid, [scores["vc"]], SPEARMAN_ID["plot"], [0.34], rng)
    scores["bud"] = fit_many(zid, [scores["rel"]], SPEARMAN_ID["bud"], [-0.05], rng)
    scores["rev"] = fit_many(
        zid, [scores["vc"], scores["bud"]], SPEARMAN_ID["rev"], [0.70, 0.70], rng
    )
    scores["pop"] = fit_many(
        zid,
        [scores["vc"], scores["bud"], scores["va"]],
        SPEARMAN_ID["pop"],
        [0.44, 0.42, 0.21],
        rng,
    )
    scores["rt"] = fit_many(zid, [scores["bud"]], SPEARMAN_ID["rt"], [0.32], rng)
    scores["cast"] = fit_many(zid, [scores["bud"]], SPEARMAN_ID["cast"], [0.28], rng)
    return scores




def assign_by_score(values: list, indices: list[int], scores: list[float]) -> dict[int, object]:
    """Map sorted `values` onto `indices` ordered by ascending score."""
    order = sorted(indices, key=lambda i: (scores[i], i))
    if len(order) != len(values):
        raise RuntimeError(f"assign size {len(order)} != {len(values)}")
    return {mi: values[rank] for rank, mi in enumerate(order)}


def spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    def ranks(vals):
        order = sorted(range(n), key=lambda i: (vals[i], i))
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def diversify_sorted(vals: list[int], target_unique: int, rng: random.Random, step: int = 1) -> list[int]:
    """Spread duplicates toward ~target_unique distinct values, preserving order and
    the exact values at indices 0, median, p95 and n-1 (so percentile checks still pass).
    """
    n = len(vals)
    out = vals[:]
    i50 = int((n - 1) * 0.5)
    i95 = int((n - 1) * 0.95)
    # Also protect neighbours used by the percentile interpolator
    protected = {0, i50, i95, n - 1}
    if (n - 1) * 0.5 != i50:
        protected.add(i50 + 1)
    if abs((n - 1) * 0.95 - i95) > 1e-9:
        protected.add(min(n - 1, i95 + 1))
    i = 0
    while i < n:
        j = i
        while j + 1 < n and out[j + 1] == out[i]:
            j += 1
        if j > i:
            ceiling = out[j + 1] - step if j + 1 < n else out[i] + step * (j - i)
            room = max(0, ceiling - out[i])
            if room > 0:
                for t, k in enumerate(range(i + 1, j + 1)):
                    if k in protected:
                        continue
                    bump = min(room, step * (1 + t))
                    candidate = out[i] + bump
                    # do not cross next protected value
                    out[k] = candidate
        i = j + 1
    # Restore protected exact values and non-decreasing order
    for p in protected:
        out[p] = vals[p]
    for i in range(1, n):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    for p in sorted(protected):
        out[p] = vals[p]
    # re-enforce non-decreasing around restored anchors
    for i in range(1, n):
        if out[i] < out[i - 1] and i not in protected:
            out[i] = out[i - 1]
    for p in sorted(protected):
        out[p] = vals[p]
    return out


def round_millions(budgets: list[int], target_round: int, rng: random.Random) -> list[int]:
    """Make ~target_round budgets multiples of $1,000,000 (cents unit 100_000_000),
    preserving the sorted list's min / median / p95 / max.
    """
    unit = 100_000_000
    n = len(budgets)
    out = budgets[:]
    i50 = int((n - 1) * 0.5)
    i95 = int((n - 1) * 0.95)
    protected = {0, i50, i95, n - 1}
    if (n - 1) * 0.5 != i50:
        protected.add(i50 + 1)
    if abs((n - 1) * 0.95 - i95) > 1e-9:
        protected.add(min(n - 1, i95 + 1))
    scored = []
    for i, v in enumerate(out):
        if i in protected:
            continue
        nearest = int(round(v / unit)) * unit
        scored.append((abs(v - nearest), i, nearest))
    scored.sort()
    for _, i, nearest in scored[:target_round]:
        if nearest < out[0]:
            continue
        if nearest > out[-1]:
            nearest = (out[-1] // unit) * unit
        out[i] = nearest
    for p in protected:
        out[p] = budgets[p]
    # keep non-decreasing so sorted() == itself and percentiles stay
    for i in range(1, n):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    for p in protected:
        out[p] = budgets[p]
    for i in range(1, n):
        if out[i] < out[i - 1] and i not in protected:
            out[i] = out[i - 1]
    for p in protected:
        out[p] = budgets[p]
    return out




# --- Curated vocabulary (real, correctly spelled words; invented combinations) ---
def _w(text: str) -> list[str]:
    return text.split()


T_NOUNS = _w("""
harbor river winter summer autumn spring morning evening midnight shadow silence
storm thunder lantern compass anchor island valley mountain canyon desert forest
meadow orchard garden village city kingdom empire frontier border coast shore
tide ocean sea lake creek bridge tower castle palace cathedral chapel lighthouse
station highway road railway train ship voyage journey passage crossing return
promise secret mystery legacy inheritance fortune treasure ransom bargain debt
witness stranger traveler pilgrim soldier sailor captain hunter keeper guardian
outlaw drifter prophet thief spy widow orphan sister brother daughter father mother
neighbor friend rival enemy lover heart soul spirit ghost angel saint sinner
mirror window door key letter map photograph portrait song melody ballad echo
whisper fire flame ember ash smoke dust stone iron steel silver gold copper glass
crown sword shield arrow blade rose lily willow cedar oak pine birch thorn
feather wing raven sparrow falcon hawk wolf fox bear horse stallion lion tiger
serpent dragon moon star comet sun sky horizon dawn dusk twilight night day
season year hour moment memory dream nightmare promise prayer hymn confession
verdict trial judgment justice mercy grace honor glory courage valor revenge
vengeance redemption salvation reckoning awakening uprising rebellion revolution
conspiracy betrayal deception illusion paradox riddle puzzle labyrinth maze
circle line edge frontier summit peak cliff cave tunnel well spring fountain
garden harvest feast wedding funeral reunion carnival circus parade festival
season ballroom theater stage curtain encore overture finale symphony requiem
lullaby serenade anthem chorus refrain rhythm pulse heartbeat breath voice
signal message code cipher archive library manuscript chronicle diary journal
ledger contract alibi motive evidence suspect detective inspector sheriff marshal
deputy ranger pilot engineer doctor nurse teacher student scholar artist painter
dancer singer poet writer actor clown magician alchemist inventor explorer
astronaut sailor fisherman farmer miner blacksmith carpenter baker tailor
gambler hustler smuggler mercenary assassin bodyguard heiress duchess countess
baron prince princess queen king emperor general admiral colonel sergeant
""")

T_ADJS = _w("""
silent quiet hidden secret lost forgotten broken burning frozen golden silver
crimson scarlet black white gray blue green violet amber pale dark bright
distant northern southern eastern western endless last first final only lonely
wild gentle bitter sweet cold warm hollow empty restless sleepless fearless
reckless savage noble humble royal sacred holy wicked cruel kind brave bold
strange curious hollow ancient modern little great small long short deep high
narrow wide open closed perfect imperfect beautiful terrible dangerous deadly
fatal mortal immortal eternal invisible visible fragile steady quiet violent
lucky unlucky blind silent brief crooked crystal electric iron velvet wooden
paper glass stone painted shattered fallen rising wandering drifting dancing
sleeping dreaming waiting vanishing returning midnight morning summer winter
autumn harbor desert mountain ocean river island coastal rural urban lonesome
unspoken unseen unknown untold uncharted unfinished unbroken hollow faithful
faithless honest loyal stolen borrowed buried sunken drowned haunted cursed
blessed tender fierce proud lucky wicked gilded rusted faded vivid hungry
""")

T_PLURALS = _w("""
ashes winters summers shadows echoes whispers storms tides rivers mountains
islands valleys roads bridges towers castles kingdoms empires borders shores
oceans stars moons suns skies dreams nightmares memories promises secrets
lies truths sins prayers hymns songs ballads letters maps keys doors windows
mirrors flames embers stones swords shields arrows roses lilies thorns feathers
wings ravens sparrows wolves foxes horses lions tigers serpents dragons ghosts
angels saints sinners strangers travelers soldiers sailors hunters keepers
outlaws thieves spies widows orphans sisters brothers daughters sons fathers
mothers neighbors friends rivals enemies lovers hearts souls spirits seasons
years hours days nights mornings evenings voices signals codes ciphers ledgers
witnesses suspects detectives rangers pilots doctors dancers singers poets
painters magicians explorers fishermen farmers miners gamblers smugglers
""")

T_GERUNDS = _w("""
chasing finding losing leaving crossing burning breaking holding keeping
waiting searching running falling rising dancing dreaming hunting saving
remembering forgetting becoming hiding seeking watching guarding building
""")

T_NUMWORDS = _w("""
one two three four five six seven eight nine ten eleven twelve thirteen
twenty forty hundred thousand
""")

T_FUNCTION = _w("""
the a an of and in on at to for from with without under over beyond after
before between into through across against among behind below above along
around near upon until part chapter book story
""")

T_ROMAN = ["II", "III", "IV", "V", "VI"]

# Famous real titles (lowercase) never produced.
TITLE_BLOCK = set(t.strip() for t in """
avatar|titanic|inception|gladiator|casablanca|psycho|alien|aliens|rocky|jaws|frozen|moana|cars|up|coco|soul|brave|tangled|
shrek|the matrix|terminator|batman|superman|spider-man|star wars|the hobbit|the godfather|pulp fiction|fight club|forrest gump|
interstellar|dune|joker|parasite|oppenheimer|barbie|mad max|blade runner|die hard|home alone|toy story|finding nemo|the lion king|
beauty and the beast|aladdin|the silent harbor|ashes of winter|vertigo|memento|arrival|gravity|heat|speed|seven|signs|split|us|her|it|
nope|elf|hook|big|ghost|twister|rush|fury|tenet|lucy|taken|unbroken|whiplash|birdman|spotlight|moonlight|roma|nomadland|crash|
platoon|amadeus|gandhi|rain man|unforgiven|braveheart|chicago|argo|the departed|the revenant|the artist|the room|the ring|the grudge|
the others|the village|the island|the shining|the birds|the thing|the fly|the fog|the mist|the crow|the mask|the rock|the town|
the fighter|the wrestler|the reader|the pianist|the prestige|the illusionist|the hunt|the hunter|the stranger|the witness|the guardian|
the outlaw|the deep|the abyss|the descent|the road|the way back|the last samurai|the last emperor|the last of us|the lighthouse|
the northman|the green knight|the whale|the fabelmans|the irishman|the post|the help|the notebook|the proposal|the holiday|
the hangover|the mummy|the ghost writer|the night of the hunter|gone girl|gone with the wind|north by northwest|the north star|
sunset boulevard|singin' in the rain|rear window|the third man|citizen kane|the searchers|the wild bunch|the great escape|
the great gatsby|the sound of music|west side story|the deer hunter|apocalypse now|the conversation|chinatown|taxi driver|
raging bull|goodfellas|casino|the irishman|heat|collateral|the insider|the revenant|black swan|the wolf of wall street|
silence|hugo|the aviator|gangs of new york|the age of innocence|cape fear|after hours|the color of money|the king of comedy|
midsommar|hereditary|the witch|it follows|get out|us|nope|the babadook|the conjuring|insidious|sinister|annabelle|the nun|
paddington|wonka|matilda|annie|oliver|hamlet|macbeth|othello|romeo and juliet|king lear|the tempest|twelfth night|
winter's bone|winter light|summer of soul|autumn sonata|spring breakers|the seventh seal|wild strawberries|persona|
the red shoes|black narcissus|the third man|brief encounter|great expectations|david copperfield|jane eyre|wuthering heights|
pride and prejudice|sense and sensibility|emma|persuasion|little women|anna karenina|war and peace|doctor zhivago|
lawrence of arabia|the bridge on the river kwai|ben-hur|spartacus|cleopatra|the ten commandments|the robe|quo vadis|
the good, the bad and the ugly|once upon a time in the west|for a few dollars more|a fistful of dollars|high noon|shane|
stagecoach|the magnificent seven|true grit|tombstone|open range|the hateful eight|django unchained|inglourious basterds|
kill bill|jackie brown|reservoir dogs|once upon a time in hollywood|death proof|the master|there will be blood|magnolia|
boogie nights|phantom thread|licorice pizza|the shape of water|pan's labyrinth|the devil's backbone|crimson peak|nightmare alley|
pacific rim|hellboy|blade|the crow|the crown|the hours|the others|the orphanage|the impossible|the sea inside|talk to her|
all about my mother|volver|pain and glory|the skin i live in|amores perros|babel|biutiful|y tu mamá también|children of men|
gravity|roma|the hours|the piano|the lover|the english patient|the talented mr. ripley|cold mountain|the reader|atonement|
anna|nikita|leon|the professional|the fifth element|lucy|valerian|taxi|the transporter|ronin|heat|thief|manhunter|
""".replace("\n", "").split("|") if t.strip())

# --- Person names: real given names and surnames from many cultures. ---
FIRST_F = _w("""
Maria Ana Sofia Lucia Elena Isabel Carmen Laura Paula Marta Julia Clara Alba Irene Nuria
Emma Olivia Charlotte Amelia Grace Lily Ella Chloe Hannah Sarah Rachel Rebecca Laura Megan
Emily Jessica Abigail Natalie Victoria Lauren Katherine Caroline Margaret Eleanor Alice
Claire Helen Ruth Martha Diane Susan Karen Linda Nancy Patricia Barbara Deborah Janet
Amara Chiamaka Ngozi Adaeze Ayana Zainab Fatima Aisha Amina Halima Yasmin Leila Nadia Samira
Mei Ling Xiu Yan Hui Jing Lan Fang Wei Hua Yuki Aiko Haruka Sakura Yumi Emi Naomi Keiko
Hana Mina Jisoo Seoyeon Jiwoo Minji Eunji Priya Ananya Kavya Divya Meera Asha Lakshmi Pooja
Ingrid Astrid Freya Sigrid Maja Elsa Linnea Saga Ida Karin Greta Liesel Anke Heike Petra
Katarina Milena Jelena Ivana Marta Agnieszka Katarzyna Magdalena Zofia Olga Tatiana Irina
Svetlana Natasha Daria Vera Anja Lena Nina Sara Eva Rosa Beatriz Gabriela Fernanda Camila
Valentina Daniela Mariana Luisa Adriana Renata Bianca Giulia Chiara Francesca Alessia
Federica Martina Elisa Silvia Simone Camille Juliette Margaux Manon Pauline Elodie Claire
Aoife Siobhan Niamh Ciara Roisin Maeve Fiona Isla Mairi Eilidh Rhiannon Carys Bethan Megan
Thandiwe Nomvula Lerato Ama Akosua Efua Abena Wanjiru Njeri Achieng Imani Zawadi Makena
Leilani Kalani Malia Tala Ayasha Dakota Noemi Esther Miriam Tamar Yael Shira Dalia Rania
""")

FIRST_M = _w("""
James John Robert Michael William David Richard Thomas Charles Daniel Matthew Andrew Joseph
Mark Paul Steven Kevin Brian George Edward Henry Samuel Benjamin Nathan Patrick Peter Simon
Oliver Jack Harry Charlie Oscar Arthur Leo Theo Lucas Noah Ethan Owen Liam Connor Callum
Carlos Juan Luis Miguel Javier Pablo Diego Alejandro Manuel Antonio Francisco Rafael Sergio
Marco Luca Matteo Giovanni Lorenzo Andrea Alessandro Davide Stefano Paolo Francesco Enrico
Pierre Louis Antoine Julien Mathieu Nicolas Olivier Laurent Thierry Etienne Bastien Remi
Hans Klaus Stefan Markus Tobias Florian Lukas Jonas Felix Matthias Wolfgang Dieter Rolf
Lars Erik Anders Nils Henrik Magnus Sven Gunnar Bjorn Leif Mikkel Rasmus Jesper Oskar
Pavel Ivan Dmitri Sergei Alexei Nikolai Andrei Mikhail Boris Viktor Yuri Oleg Roman Igor
Tomasz Piotr Krzysztof Marek Jakub Wojciech Adam Michal Pawel Ondrej Petr Jan Martin Milan
Hiroshi Takeshi Kenji Haruto Ren Sora Daichi Kaito Yuto Riku Shota Kazuki Takumi Ryo
Wei Jun Hao Ming Lei Tao Bo Feng Chen Jian Kai Long Min Seojun Minho Jiho Hyun Joon
Arjun Rahul Vikram Rohan Aditya Karan Sanjay Ravi Amit Nikhil Dev Anil Suresh Vivek
Chinedu Emeka Obinna Tunde Kwame Kofi Yaw Kwesi Jabari Baraka Juma Tendai Sipho Thabo
Omar Ahmed Youssef Karim Tariq Samir Hassan Ali Malik Rashid Bilal Faisal Nabil Idris
Mateo Santiago Sebastian Nicolas Tomas Gabriel Bruno Thiago Rodrigo Felipe Gustavo Vinicius
Eitan Noam Avi Yosef Ariel Dov Levi Kalani Keanu Makoa Tane Wiremu Rangi Hemi Ari
""")

LAST_NAMES = _w("""
Garcia Martinez Rodriguez Lopez Hernandez Gonzalez Perez Sanchez Ramirez Torres Flores
Rivera Gomez Diaz Morales Ortiz Gutierrez Castillo Romero Herrera Medina Aguilar Vargas
Castro Ruiz Alvarez Mendoza Jimenez Moreno Navarro Rubio Molina Delgado Ortega Serrano
Smith Johnson Williams Brown Jones Miller Davis Wilson Anderson Taylor Thomas Moore Jackson
Martin Lee Thompson White Harris Clark Lewis Robinson Walker Young Allen King Wright Scott
Hill Green Adams Baker Nelson Carter Mitchell Roberts Turner Phillips Campbell Parker Evans
Edwards Collins Stewart Morris Rogers Reed Cook Morgan Bell Murphy Bailey Cooper Richardson
Cox Howard Ward Peterson Gray James Watson Brooks Kelly Sanders Price Bennett Wood Barnes
Ross Henderson Coleman Jenkins Perry Powell Long Patterson Hughes Washington Butler Simmons
Foster Bryant Alexander Russell Griffin Hayes Myers Ford Hamilton Graham Sullivan Wallace
Novak Horvat Kovac Babic Nowak Kowalski Wisniewski Wojcik Kaminski Lewandowski Zielinski
Szymanski Dabrowski Kozlowski Jankowski Mazur Krawczyk Kaczmarek Pavlov Ivanov Petrov
Smirnov Volkov Sokolov Popov Lebedev Kozlov Novikov Morozov Orlov Fedorov Kuznetsov Belov
Okafor Okonkwo Adeyemi Nwosu Eze Obi Mensah Boateng Owusu Asante Kamau Otieno Mwangi Njoroge
Dlamini Nkosi Mokoena Ndlovu Khumalo Abubakar Bello Danjuma Diallo Traore Keita Toure Sow
Lindqvist Lindberg Nilsson Johansson Andersson Karlsson Larsson Olsson Persson Svensson
Hansen Jensen Nielsen Pedersen Christensen Rasmussen Larsen Halvorsen Berg Dahl Lund Holm
Schmidt Schneider Fischer Weber Meyer Wagner Becker Schulz Hoffmann Koch Richter Klein Wolf
Neumann Schwarz Zimmermann Braun Hartmann Lange Werner Krause Lehmann Kaiser Fuchs Vogel
Rossi Russo Ferrari Esposito Bianchi Romano Colombo Ricci Marino Greco Bruno Gallo Conti
DeLuca Mancini Costa Giordano Rizzo Lombardi Moretti Barbieri Fontana Santoro Caruso
Dubois Durand Leroy Moreau Simon Laurent Lefebvre Michel Bertrand Roux Vincent Fournier
Morel Girard Andre Mercier Blanc Guerin Boyer Garnier Chevalier Faure Rousseau Lambert
Tanaka Suzuki Takahashi Watanabe Ito Yamamoto Nakamura Kobayashi Kato Yoshida Yamada Sasaki
Yamaguchi Matsumoto Inoue Kimura Hayashi Shimizu Mori Abe Ikeda Hashimoto Ishikawa Ogawa
Wang Li Zhang Liu Chen Yang Huang Zhao Wu Zhou Xu Sun Ma Zhu Hu Guo He Lin Luo Gao
Kim Park Choi Jung Kang Cho Yoon Jang Lim Han Shin Seo Kwon Hwang Ahn Song Ryu Hong
Patel Sharma Singh Kumar Gupta Mehta Shah Reddy Rao Iyer Nair Menon Pillai Joshi Desai
Chopra Malhotra Kapoor Bhatt Banerjee Chatterjee Mukherjee Das Bose Sen Ghosh Verma
Haddad Khalil Nasser Mansour Saleh Hamdan Aziz Rahman Hussein Karimi Ahmadi Hosseini
Cohen Levi Mizrahi Peretz Friedman Katz Shapiro Rosen Goldberg Weiss Klein Stein
Silva Santos Oliveira Souza Pereira Carvalho Almeida Ferreira Ribeiro Rodrigues Lima
Araujo Barbosa Cardoso Rocha Dias Monteiro Mendes Teixeira Correia Pinto Moreira
OBrien Murphy Kelly Walsh Byrne Ryan Doyle McCarthy Gallagher Doherty Kennedy Lynch
Murray Quinn Moore MacDonald Campbell Stewart Robertson Thomson Fraser MacLeod Ross
Jovanovic Petrovic Nikolic Markovic Djordjevic Stojanovic Ilic Popescu Ionescu Stan
Dumitru Nagy Toth Szabo Horvath Kiss Varga Molnar Nemeth Farkas Balogh Papadopoulos
Georgiou Nikolaidis Yilmaz Kaya Demir Sahin Celik Aydin Ozturk Arslan Nguyen Tran Le
Pham Hoang Phan Vu Dang Bui Do Ngo Duong Santos Reyes Cruz Bautista Ocampo Mendoza Aquino
Kealoha Kahale Ngata Tawhiri Parata Morrison Leclerc Tremblay Gagnon Roy Cote Bouchard
Halloran Whitaker Ashford Pemberton Blackwood Hargrove Kensington Thornton Whitfield
""")

# Names with diacritics (used for ~5 % of people).
FIRST_DIA = _w("""
José María Inés Lucía Sofía Andrés Martín Raúl Joaquín Óscar Álvaro Ramón Héctor
Zoë Chloë Noël Anaïs Hélène Amélie Célia Émile Léa Théo Jérôme François Gaëlle
Søren Bjørn Jørgen Ørjan Åsa Märta Björn Göran Jürgen Jörg Günter Lück Mårten
Łukasz Małgorzata Michał Paweł Wojciech Bartłomiej Zuzanna Jiří Tomáš Lukáš Ondřej
Šárka Zdeněk Dušan Željko Mirjana Ştefan Ioană Mihaï Gülşen Çağla Ömer Ayşe
""")

LAST_DIA = _w("""
Müller Schäfer Krüger Böhm Köhler Größ Jäger Wöhler Hübner Mäder Šimek Novák Dvořáková
Černý Kovář Procházka Křížek Horák Kučera Veselý Svoboda Navrátil Wójcik Kowalczyk
Zieliński Lewandowska Dąbrowski Kamińska Gómez Núñez Peña Ibáñez Martínez Sánchez Díaz
Muñoz Álvarez Fernández Pérez Rodríguez Hernández López Jiménez Ruíz Gutiérrez Ortíz
Lefèvre Bérénger Mérieux Desmarais Hébert Gagné Bélanger Côté Lévesque Pelletier Gauthier
Jørgensen Sørensen Mølgaard Bækgaard Høiberg Åberg Ångström Söderberg Lindström Nyström
Öberg Törnqvist Šarić Kovačević Petrović Jovanović Babić Đorđević Ţurcanu Ştefănescu
Yıldız Öztürk Çelik Şahin Doğan Güneş Nguyễn Trần Lê Phạm Hoàng Esquível Galvão Conceição
""")

PERSON_BLOCK = set(n.strip().lower() for n in """
James Brown|James Taylor|James Dean|James Franco|James Cameron|James Woods|John Lee|John Williams|John Wayne|
John Smith|John Lennon|John Travolta|John Cusack|John Goodman|John Carpenter|John Ford|John Huston|Michael Jackson|
Michael Jordan|Michael Caine|Michael Douglas|Michael Mann|Michael Bay|David Lynch|David Bowie|David Fincher|
David Lean|Peter Jackson|Paul Simon|George Lucas|George Michael|Emma Watson|Emma Thompson|Emma Stone|Maria Callas|
Jennifer Lopez|Grace Kelly|Jack White|Chris Martin|Robert Smith|Daniel Craig|Hugh Grant|Tom Hanks|Mark Wahlberg|
Thomas Edison|Charles Darwin|William Shakespeare|Henry Ford|Steven Spielberg|Kevin Costner|Kevin Bacon|Richard Gere|
Matthew Perry|Andrew Garfield|Samuel Jackson|Oliver Stone|Oscar Isaac|Ethan Hawke|Owen Wilson|Liam Neeson|Diego Luna|
Antonio Banderas|Javier Bardem|Pablo Picasso|Pierre Curie|Ivan Petrov|Bruno Mars|Ali Khan|Omar Sharif|Wei Wang|Kim Lee|
Sarah Connor|Rachel Green|Rebecca Hall|Naomi Watts|Naomi Campbell|Laura Dern|Claire Foy|Helen Mirren|Diane Keaton|
Diane Lane|Susan Sarandon|Natalie Wood|Victoria Beckham|Alice Cooper|Martha Stewart|Simone Biles|Amelia Earhart|Grace Jones|
Karen Gillan|Olivia Wilde|Olivia Colman|Ella Fitzgerald|Margaret Thatcher|Elizabeth Taylor|Nina Simone|Lily Allen|
Charlotte Rampling|Nancy Sinatra|Carmen Electra|Isabel Allende|Penelope Cruz|Sofia Coppola|Sofia Vergara|Eva Green|
Eva Mendes|Laura Linney|Ana Torrent|Rosa Parks|Esther Williams|Ingrid Bergman|Greta Garbo|Astrid Lindgren|Freya Allan|
Lars Ulrich|Lars Kepler|Erik Satie|Magnus Carlsen|Hans Zimmer|Klaus Kinski|Wolfgang Petersen|Lukas Graham|Ivan Drago|
Hiroshi Tanaka|Kenji Mizoguchi|Ken Watanabe|Ryo Kase|Arjun Kapoor|Karan Johar|Rahul Gandhi|Ravi Shankar|Dev Patel|
Kwame Nkrumah|Kofi Annan|Omar Little|Tariq Ali|Mateo Gil|Gabriel Byrne|Bruno Ganz|Felipe Gonzalez|Ari Aster|Noam Chomsky|
""".replace("\n", "").split("|") if n.strip())

# --- Prose vocabulary (typed slots) ---
ROLES = [
    "retired detective", "young nurse", "grieving widow", "small-town lawyer", "struggling actor",
    "former soldier", "ambitious journalist", "lonely fisherman", "schoolteacher", "night-shift cab driver",
    "disgraced surgeon", "aging boxer", "gifted pianist", "rookie police officer", "single father",
    "single mother", "teenage runaway", "museum curator", "ship's captain", "mountain guide",
    "wedding planner", "insurance investigator", "small-time crook", "family doctor", "bush pilot",
    "village priest", "hotel concierge", "struggling novelist", "stand-up comedian", "farm widow",
    "veteran reporter", "public defender", "young architect", "marine biologist", "bank clerk",
    "forensic accountant", "hospital janitor", "chess prodigy", "circus acrobat", "diner waitress",
    "border patrol agent", "coal miner", "art forger", "radio host", "climate scientist",
    "college professor", "orphaned teenager", "retired spy", "union organizer", "jazz singer",
    "former child star", "parole officer", "lighthouse keeper", "pastry chef", "truck driver",
    "veterinarian", "park ranger", "tattoo artist", "court stenographer", "bookshop owner",
]
ROLE_ADJS = [
    "reluctant", "stubborn", "restless", "idealistic", "weary", "headstrong", "quiet", "fearless",
    "anxious", "cynical", "kind-hearted", "proud", "desperate", "determined", "secretive", "brilliant",
]
PLACES = [
    "a small fishing village", "a remote mountain town", "the outskirts of the city", "a crumbling country estate",
    "a desert border town", "a snowbound research station", "a seaside resort out of season", "a run-down motel",
    "a sprawling vineyard", "a provincial hospital", "an island ferry", "a failing family restaurant",
    "a boarding school in the hills", "a mining town", "a coastal lighthouse", "a crowded tenement",
    "a riverside mill town", "a luxury cruise ship", "an abandoned amusement park", "a sleepy suburb",
    "a frontier trading post", "a mountain monastery", "a jazz club downtown", "a rural farmhouse",
    "a quiet university town", "a busy harbor district", "a high-rise office tower", "a forgotten railway station",
    "a summer camp by the lake", "a neighborhood bakery", "a traveling circus", "a sheep farm on the moors",
]
OBJECTS = [
    "an old map", "a sealed letter", "a stolen ledger", "a missing painting", "a cassette tape",
    "a locked diary", "a bag of cash", "a forged passport", "a family heirloom", "a coded notebook",
    "a photograph", "a set of keys", "a wedding ring", "a pocket watch", "a hidden will",
    "a shipping manifest", "a reel of film", "a strange recording", "a deed to the land", "a lottery ticket",
]
EVENTS = [
    "a violent storm", "an unsolved murder", "a sudden inheritance", "a corporate takeover", "a deadly fever",
    "a bank robbery gone wrong", "a long-buried scandal", "a mysterious fire", "a hostage crisis",
    "a disappearance", "a contested election", "a failed harvest", "a train derailment", "a blackout",
    "a flood", "a kidnapping", "a public scandal", "a rigged trial", "a factory closure", "an eclipse",
]
GROUPS = [
    "a ruthless cartel", "a band of smugglers", "a crooked police captain", "a secret society", "a powerful family",
    "a corrupt city council", "a rival crew", "a group of old friends", "a traveling theater troupe",
    "a union of dockworkers", "a cult on the edge of town", "the town council", "a team of investigators",
    "a gang of car thieves", "a dying newspaper", "a rival restaurant", "a mining company", "a church choir",
]
GOALS = [
    "find a missing brother", "clear a family name", "save the family farm", "expose the truth",
    "win back an estranged daughter", "pay off a dangerous debt", "solve the case", "protect a key witness",
    "rebuild a broken life", "keep the business afloat", "escape the past", "finish one last job",
    "recover what was stolen", "bring a killer to justice", "keep a promise", "reunite the band",
    "stop the wedding", "win the championship", "save the old theater", "uncover a conspiracy",
    "get home before winter", "earn a second chance", "protect the village", "find the missing money",
]
OUTCOMES = [
    "everything begins to unravel", "old loyalties are tested", "the past refuses to stay buried",
    "the truth turns out to be far more dangerous", "nobody is who they seem", "the whole town takes sides",
    "the stakes become personal", "time is running out", "the consequences reach everyone",
    "trust becomes a luxury", "the line between right and wrong begins to blur",
]
TIMES = [
    "One winter", "That summer", "Years later", "Late one night", "Within days", "By the end of the season",
    "Over a single weekend", "On the eve of the wedding", "After the funeral", "Months later",
]
LINES = [
    "We leave at dawn.", "Nobody can know about this.", "I never asked for any of it.",
    "You should have stayed away.", "Tell me the truth for once.", "This town remembers everything.",
    "I am not the person you think I am.", "Some debts are never paid.", "We finish what we started.",
    "Give me one more night.", "It was never about the money.", "Do not look back.",
    "You promised me this would end.", "I can still fix this.", "They will come for us.",
    "Keep the lights on.", "Say it again, slowly.", "Everyone lies here.",
]
SPEECH = ["tells", "warns", "reminds", "promises", "confesses to", "begs"]
ABSTRACT = _w("""
secret debt promise truth lie heart family town river storm winter memory fortune name
past future silence crime choice dream love grief revenge courage loyalty legacy home
""")
TAG_VERBS = _w("""
waits burns breaks hides returns remembers forgets follows falls rises lingers
""")

# Foreign lexicons for original titles of Latin-script non-English films.
FOREIGN = {
    "es": (["la noche", "el río", "la casa", "el silencio", "la tormenta", "el viaje", "la frontera",
            "el invierno", "la memoria", "el secreto", "la sombra", "el puerto", "la isla", "el camino",
            "la promesa", "el desierto", "la herida", "el regreso", "la llama", "el destino"], "y"),
    "fr": (["la nuit", "le fleuve", "la maison", "le silence", "la tempête", "le voyage", "la frontière",
            "l'hiver", "la mémoire", "le secret", "l'ombre", "le port", "l'île", "le chemin", "la promesse",
            "le désert", "la blessure", "le retour", "la flamme", "le destin"], "et"),
    "it": (["la notte", "il fiume", "la casa", "il silenzio", "la tempesta", "il viaggio", "la frontiera",
            "l'inverno", "la memoria", "il segreto", "l'ombra", "il porto", "l'isola", "la strada",
            "la promessa", "il deserto", "la ferita", "il ritorno", "la fiamma", "il destino"], "e"),
    "de": (["die Nacht", "der Fluss", "das Haus", "die Stille", "der Sturm", "die Reise", "die Grenze",
            "der Winter", "die Erinnerung", "das Geheimnis", "der Schatten", "der Hafen", "die Insel",
            "der Weg", "das Versprechen", "die Wüste", "die Wunde", "die Rückkehr", "die Flamme", "das Schicksal"], "und"),
    "pt": (["a noite", "o rio", "a casa", "o silêncio", "a tempestade", "a viagem", "a fronteira",
            "o inverno", "a memória", "o segredo", "a sombra", "o porto", "a ilha", "o caminho",
            "a promessa", "o deserto", "a ferida", "o regresso", "a chama", "o destino"], "e"),
    "sv": (["natten", "floden", "huset", "tystnaden", "stormen", "resan", "gränsen", "vintern",
            "minnet", "hemligheten", "skuggan", "hamnen", "ön", "vägen", "löftet"], "och"),
    "da": (["natten", "floden", "huset", "stilheden", "stormen", "rejsen", "grænsen", "vinteren",
            "minde", "hemmeligheden", "skyggen", "havnen", "øen", "vejen", "løftet"], "og"),
    "no": (["natten", "elven", "huset", "stillheten", "stormen", "reisen", "grensen", "vinteren",
            "minnet", "hemmeligheten", "skyggen", "havnen", "øya", "veien", "løftet"], "og"),
    "nl": (["de nacht", "de rivier", "het huis", "de stilte", "de storm", "de reis", "de grens",
            "de winter", "de herinnering", "het geheim", "de schaduw", "de haven", "het eiland", "de weg"], "en"),
    "pl": (["noc", "rzeka", "dom", "cisza", "burza", "podróż", "granica", "zima", "pamięć",
            "tajemnica", "cień", "port", "wyspa", "droga", "obietnica"], "i"),
}

# Words used by keyword multi-word phrases.
KEY_ADJS = _w("""
abandoned ancient arranged broken buried corrupt cursed dark deadly dying estranged
fake false female first forbidden haunted hidden illegal imaginary interracial last
lost male missing murdered mysterious new old organized political private religious
remote rival rural secret serial single small stolen strange teenage toxic underground
unrequited urban violent wealthy young aging alien amateur annual criminal cultural
""")
KEY_SOURCES = [
    "novel", "true story", "comic", "play", "short story", "video game", "memoir", "poem",
    "folk tale", "legend", "song", "television series", "radio play", "fairy tale", "musical",
]
CITIES = [
    ("paris", "france"), ("lyon", "france"), ("marseille", "france"), ("madrid", "spain"), ("barcelona", "spain"),
    ("seville", "spain"), ("rome", "italy"), ("naples", "italy"), ("milan", "italy"), ("venice", "italy"),
    ("berlin", "germany"), ("hamburg", "germany"), ("munich", "germany"), ("vienna", "austria"), ("prague", "czech republic"),
    ("warsaw", "poland"), ("krakow", "poland"), ("budapest", "hungary"), ("lisbon", "portugal"), ("porto", "portugal"),
    ("dublin", "ireland"), ("cork", "ireland"), ("edinburgh", "scotland"), ("glasgow", "scotland"), ("cardiff", "wales"),
    ("london", "england"), ("manchester", "england"), ("liverpool", "england"), ("bristol", "england"), ("oslo", "norway"),
    ("bergen", "norway"), ("stockholm", "sweden"), ("gothenburg", "sweden"), ("copenhagen", "denmark"), ("helsinki", "finland"),
    ("reykjavik", "iceland"), ("athens", "greece"), ("istanbul", "turkey"), ("cairo", "egypt"), ("marrakesh", "morocco"),
    ("lagos", "nigeria"), ("nairobi", "kenya"), ("cape town", "south africa"), ("johannesburg", "south africa"), ("accra", "ghana"),
    ("mumbai", "india"), ("delhi", "india"), ("kolkata", "india"), ("tokyo", "japan"), ("osaka", "japan"), ("kyoto", "japan"),
    ("seoul", "south korea"), ("busan", "south korea"), ("shanghai", "china"), ("beijing", "china"), ("hong kong", "china"),
    ("taipei", "taiwan"), ("bangkok", "thailand"), ("hanoi", "vietnam"), ("manila", "philippines"), ("jakarta", "indonesia"),
    ("sydney", "australia"), ("melbourne", "australia"), ("perth", "australia"), ("auckland", "new zealand"),
    ("toronto", "canada"), ("montreal", "canada"), ("vancouver", "canada"), ("mexico city", "mexico"), ("guadalajara", "mexico"),
    ("havana", "cuba"), ("bogota", "colombia"), ("lima", "peru"), ("buenos aires", "argentina"), ("santiago", "chile"),
    ("rio de janeiro", "brazil"), ("sao paulo", "brazil"), ("new york city", "new york"), ("buffalo", "new york"),
    ("los angeles", "california"), ("san francisco", "california"), ("oakland", "california"), ("san diego", "california"),
    ("chicago", "illinois"), ("detroit", "michigan"), ("boston", "massachusetts"), ("philadelphia", "pennsylvania"),
    ("pittsburgh", "pennsylvania"), ("baltimore", "maryland"), ("miami", "florida"), ("tampa", "florida"),
    ("new orleans", "louisiana"), ("houston", "texas"), ("austin", "texas"), ("dallas", "texas"), ("el paso", "texas"),
    ("phoenix", "arizona"), ("tucson", "arizona"), ("las vegas", "nevada"), ("reno", "nevada"), ("denver", "colorado"),
    ("seattle", "washington"), ("spokane", "washington"), ("portland", "oregon"), ("salt lake city", "utah"),
    ("atlanta", "georgia"), ("savannah", "georgia"), ("nashville", "tennessee"), ("memphis", "tennessee"),
    ("cleveland", "ohio"), ("cincinnati", "ohio"), ("minneapolis", "minnesota"), ("st. louis", "missouri"),
    ("kansas city", "missouri"), ("omaha", "nebraska"), ("anchorage", "alaska"), ("honolulu", "hawaii"),
    ("charleston", "south carolina"), ("richmond", "virginia"), ("albuquerque", "new mexico"), ("santa fe", "new mexico"),
    ("boise", "idaho"), ("billings", "montana"), ("fargo", "north dakota"), ("des moines", "iowa"),
    ("milwaukee", "wisconsin"), ("indianapolis", "indiana"), ("louisville", "kentucky"), ("birmingham", "alabama"),
    ("jackson", "mississippi"), ("little rock", "arkansas"), ("tulsa", "oklahoma"), ("wichita", "kansas"),
    ("hartford", "connecticut"), ("providence", "rhode island"), ("burlington", "vermont"), ("portland", "maine"),
    ("newark", "new jersey"), ("atlantic city", "new jersey"), ("wilmington", "delaware"), ("raleigh", "north carolina"),
    ("charlotte", "north carolina"), ("orlando", "florida"), ("key west", "florida"), ("galveston", "texas"),
    ("monterey", "california"), ("sacramento", "california"), ("fresno", "california"), ("palm springs", "california"),
    ("quebec city", "canada"), ("halifax", "canada"), ("calgary", "canada"), ("winnipeg", "canada"),
    ("belfast", "northern ireland"), ("oxford", "england"), ("cambridge", "england"), ("brighton", "england"),
    ("nice", "france"), ("bordeaux", "france"), ("florence", "italy"), ("turin", "italy"), ("palermo", "italy"),
    ("valencia", "spain"), ("bilbao", "spain"), ("cologne", "germany"), ("frankfurt", "germany"), ("zurich", "switzerland"),
    ("geneva", "switzerland"), ("amsterdam", "netherlands"), ("rotterdam", "netherlands"), ("brussels", "belgium"),
    ("antwerp", "belgium"), ("st. petersburg", "russia"), ("moscow", "russia"), ("kyiv", "ukraine"), ("riga", "latvia"),
]

COMPANY_STEMS = _w("""
Northgate Brightwater Ironwood Silverline Blackbird Redwood Bluefin Greenleaf Stonebridge
Highland Lakeside Riverbend Harborlight Westwind Eastbrook Southfield Clearwater Goldcrest
Oakhill Pinecrest Maplewood Cedarline Ashgrove Elmstead Birchwood Willowbrook Thornfield
Foxglove Kingfisher Bluebell Lanternfly Moonrise Sunward Starling Nightjar Skylark Wren
Larkspur Hawthorn Juniper Marigold Saffron Cobalt Indigo Copperline Granite Basalt Quarry
Lantern Compass Meridian Horizon Keystone Cornerstone Milestone Waypoint Landmark Beacon
Anchor Harbor Tidewater Seawall Driftwood Saltmarsh Fairhaven Newhaven Bellwether Halcyon
Paragon Pinnacle Summit Vantage Vista Panorama Prism Spectrum Mosaic Tapestry Canvas
Easel Palette Chisel Anvil Forge Foundry Mill Workshop Studio Atelier Gallery Archive
""")
COMPANY_SUFFIX = [
    "Pictures", "Studios", "Films", "Media", "Productions", "Entertainment", "Film Company",
    "Filmworks", "Motion Pictures", "Cinema", "Features", "Releasing", "Animation", "Group",
]
COMPANY_FOREIGN = [
    ("Les Films du", ["Soleil", "Rivage", "Phare", "Lointain", "Matin", "Fleuve", "Hasard", "Silence", "Retour", "Givre"]),
    ("Producciones", ["Añil", "Mañana", "Señal", "Corazón", "Ilusión", "Canción", "Sueño", "Brújula", "Faro", "Tormenta"]),
    ("Atelier", ["Lumière", "Étoile", "Rêve", "Château", "Clarté", "Mémoire", "Écho", "Fenêtre", "Lueur", "Bohème"]),
    ("Filmproduktion", ["Grünwald", "Brückner", "Mühlberg", "Schönfeld", "Lübeck", "Hölzer", "Jäger", "Köhler", "Sänger", "Fröhlich"]),
    ("Produções", ["Brisa", "Maré", "Sertão", "Ventania", "Aurora", "Lagoa", "Farol", "Cais", "Pássaro", "Raiz"]),
    ("Filmové studio", ["Říčany", "Křivoklát", "Šumava", "Jizera", "Třeboň", "Žatec", "Dobříš", "Písek", "Tábor", "Kolín"]),
]
REAL_COMPANY_BLOCK = set(x.lower() for x in """
Paramount Pictures|Universal Pictures|Columbia Pictures|Warner Bros.|Lionsgate|Legendary Pictures|Summit Entertainment|
Focus Features|Searchlight Pictures|Touchstone Pictures|Hollywood Pictures|TriStar Pictures|Orion Pictures|Miramax|
Dimension Films|New Line Cinema|Castle Rock Entertainment|Imagine Entertainment|Plan B Entertainment|Annapurna Pictures|
Village Roadshow Pictures|Working Title Films|Relativity Media|Participant Media|Spyglass Entertainment|Regency Enterprises|
Skydance Media|Blumhouse Productions|Amblin Entertainment|DreamWorks Pictures|Pixar Animation Studios|Lucasfilm|
Illumination Entertainment|Blue Sky Studios|Laika|Aardman Animations|Studio Ghibli|Toho|Toei Animation|Shochiku|
Nikkatsu|Kadokawa|Gaumont|Pathé|StudioCanal|EuropaCorp|Wild Bunch|Constantin Film|Bavaria Film|Nordisk Film|
Zentropa|Rai Cinema|Medusa Film|El Deseo|Televisa|Globo Filmes|BBC Films|Film4|Eon Productions|Heyday Films|
Scott Free Productions|Bad Robot|Syncopy|Appian Way|Malpaso Productions|Happy Madison|Platinum Dunes|Dark Castle Entertainment|
Ghost House Pictures|Atomic Monster|Lakeshore Entertainment|Millennium Films|Screen Gems|Sony Pictures|United Artists|
Metro-Goldwyn-Mayer|Walt Disney Pictures|20th Century Studios|Twentieth Century Fox|Netflix|Amazon Studios|Apple Studios|
HBO Films|A24|Neon|Magnolia Pictures|IFC Films|Saban Films|STX Entertainment|Entertainment One|Canal+|Bona Film Group|
Huayi Brothers|Golden Harvest|Shaw Brothers|Yash Raj Films|Dharma Productions|Eros International|CJ Entertainment|Showbox|
Keystone Pictures|Beacon Pictures|Summit Pictures|Horizon Pictures|Paragon Pictures|Pinnacle Films|Vantage Films|
""".replace("\n", "").split("|") if x.strip())


# Extra evocative single words for one-word titles and prose objects.
T_SINGLE = _w("""
aftermath afterglow afterlife alibi allegiance ambition amnesty anthem apparition
armistice arrival ascension asylum atonement aurora avalanche awakening backlash
badlands ballast bandit banquet baptism barricade bastion beacon bedlam benediction
birthright blackout blizzard bloodline blueprint bonfire borderland boundary breakaway
breakdown breakwater brimstone brotherhood buckshot bulletin bunker burden cadence
calamity caliber camouflage campfire candlelight capsize captive caravan carousel
cascade casualty catalyst cataclysm causeway cavalry ceasefire celestial cellar
centurion ceremony chamber champion chaos chaperone charisma checkpoint chimera
cinder citadel clearwater clemency clockwork cloudburst coastline cocoon collateral
collision commotion communion compass complicity confluence conquest consequence
constellation contraband convergence convoy coronation corridor countdown courtship
covenant crescendo crossfire crossroads crucible crusade cyclone dagger daybreak
deadlock deadline decoy defiance deliverance deluge departure descent detour
devotion dominion downpour downstream drifter driftwood drought dynasty earthbound
eclipse ecstasy embargo embrace emissary encore endgame endurance enigma epiphany
equinox escapade estuary euphoria evacuation exile exodus expedition extinction
fable fallout famine fanfare farewell fatherland fervor firebird firefly firelight
firestorm fireworks flashpoint flotsam folklore foothold forbearance foreigner forgery
fortitude fortress foxhole fracture freefall frostbite fugitive gallows gambit garrison
gauntlet getaway glacier gladiator goodbye gravity graveyard greenhouse guardian
gunpowder hailstorm halfway hallelujah hangman harbinger hardship harmony headland
headwind heartland heatwave heirloom hereafter heritage hideaway hideout highland
hindsight hinterland homecoming homeland homestead horizon hostage hurricane hysteria
iceberg idol impostor incognito inferno insomnia insurgent interlude intruder
ironclad ironside jailbreak jubilee juggernaut junction justice keepsake kindred
kinship lagoon lament landfall landslide lifeline lighthouse limelight lockdown
longitude lowlands loyalty lullaby madness maelstrom manifest marauder masquerade
matriarch meltdown memoir menagerie meridian migration milestone mirage misfit
monsoon moonlight moonshine motherland mudslide mutiny nightfall nightshade nocturne
nomad northbound northern novice oasis oblivion odyssey offering offshore onslaught
outbreak outcast outpost outsider overboard overdrive overture pandemonium paradise
pariah passport pathfinder patriot pendulum penance phantom pilgrimage pinnacle
pioneer plunder poison portrait prairie prelude prodigal prodigy prophecy providence
quarantine quicksand quicksilver railroad rainfall rampage rampart ransom reckoning
refuge regatta relic remnant rendezvous renegade reprisal requiem reservoir residue
resistance respite resurrection retreat reunion reverie riptide rivalry roadhouse
rockslide rooftop runaway sabotage sanctuary sandstorm savior scarecrow scavenger
seascape seawall sentinel serenade settlement shelter shipwreck shoreline showdown
sidewinder silhouette skyline slipstream snowfall snowstorm solace solitude solstice
sovereign spellbound stampede standoff starlight stockade stowaway stranger
stronghold sundown sunrise sunset sunstroke survivor tailspin tapestry tempest
testament threshold thunderbolt tidewater timberline torrent tranquility trespass
tribute triumph turbulence twilight typhoon underdog undertow uprising upstream
vagabond vanguard vendetta verdict vigil vigilante voyager wanderer warpath wasteland
watchtower waterfront wayfarer whirlwind wildfire wilderness windfall windmill
wintertime witchcraft woodland wreckage yesterday zenith afterburn backwater bloodhound
blindside bootleg brushfire candlewick catwalk claymore crosswind daredevil dayglow
deadfall downfall dreamland driftwood eventide farmhand fieldstone flagship floodgate
footprint freeway frontman gaslight goldmine graveside groundswell hailstone heartache
heartbreak highwater homeward honeymoon horseshoe hourglass housewarming icebreaker
jackpot keystone lamplight landmark lifeboat lifetime limestone lodestar longshot
lookout lowdown mainland marshland masterpiece meadowlark midsummer midwinter moonstone
mountainside newcomer nightingale nightwatch northwind outlaws overcast paperweight
pathway peacemaker pickpocket playground quarterback quicksand rainmaker rattlesnake
redemption riverbank roadside rosewood runway saltwater sandcastle seashell shortcut
sideshow silverfish skylark slingshot snowbird southbound springtime stagecoach
starboard steamboat stepmother stonewall storyteller sunflower sweetheart swordfish
thunderstorm timepiece tinderbox tombstone tradewind turnpike undercurrent underground
undergrowth upriver warhorse waterline wayside weekend wellspring westbound whirlpool
wildflower windstorm wintergreen wishbone woodsman workhorse wrongdoer yearling
""")
T_SINGLE += _w("""
abduction absolution acquittal adrift ambush amulet anarchy antidote apprentice
archangel armada arsenal artifact ascent assassin backfire balcony bayonet bellwether
bittersweet blacksmith bloodshed boomtown bounty brawler brigade brushstroke buccaneer
cabaret cadet canary canopy capstone carnage cartographer castaway catacomb cavalcade
chameleon chandelier chaplain charade chariot chronicle clairvoyant clockmaker
cobblestone confession conspirator constable copperhead cornerstone counterfeit
courier crossbow crowbar curfew custodian daybreak debutante deception defector
dervish desperado detonator diplomat discord dispatch distillery doppelganger dragnet
drawbridge dreamer duelist dungeon emerald empress encampment envoy epitaph errand
exorcist explorer falconer ferryman fiddler firebrand flotilla forager foundling
gambler gargoyle gatekeeper gemstone gondolier governess grenadier griffin gunslinger
harlequin harpoon headmaster heiress helmsman hermit highwayman huntress illusionist
infidel inquisitor interloper ironworks jester juniper kingpin labyrinth lamplighter
landlord lantern lieutenant locksmith lumberjack magistrate mandolin marksman marshal
martyr matador mercenary minstrel moonraker musketeer navigator nightjar nobleman
nursemaid oracle orchard outrider overlord pallbearer patriarch peddler pilgrim
pirate poacher porcelain postman preacher prospector puppeteer quartermaster
ragamuffin rainbow rancher rebel recluse rhapsody ringmaster rustler saboteur
saltmarsh scoundrel seafarer seamstress sharpshooter shepherd sheriff showgirl
smuggler songbird sorceress spinster squire stargazer stonemason stuntman
swordsman tailor taxidermist teamster tinker trapper troubadour tycoon undertaker
usurper valkyrie ventriloquist vintner virtuoso warden watchman weaver widower
wildcat wrangler zealot
""")
T_SINGLE = [w for w in T_SINGLE if w not in set(_w(
    "afterburn clearwater dayglow ironside northwind tradewind highwater goldmine longshot nightwatch moonraker"))]
T_SHORT = _w("""
wish fall lord born race safe risk wall mine pain rock fear luck spot hall cell heat tree wind hill rise camp
dear host wake farm wine port rain boat suit hero pool snow fake bird jail wave bomb bell bond flag tank lane
roof mate burn cake hunt gate fort mood ruin cape seal gulf pipe duck hood corn boot taxi silk drum noon reed
nest doll rope tent lamp bolt lamb goat liar void sail whip dock barn pond lawn prey pity dale fury hail glow
moss frog heir tomb glen surf maid swan envy reef isle lace pier pony doom crow herb scar worm vine calf mist
dove veil hare helm cove gale vale mare muse claw
break press round stand match chief cover earth sleep piece track peace store cross speed scene heavy coach
judge hotel floor reach touch drink plant block smart owner youth guide guard plane chair sugar route lunch
truck shirt giant mayor drunk frame guest fruit shift crash plate motor paint bread wheel rough pride mount
shock cloud thick trail flash uncle clock plain anger crack knife sheet grass rapid honey spell strip swing
roots flood alert arena robin rings bones piano grave mouse devil gates slide candy alien alarm globe brick
wound snake canal climb twist fever fence radar laser cargo sheep grain metro rifle couch shade swift mason
haven cabin guilt eagle ridge delta witch derby lemon shark booth dairy drill basin bride fairy grief lodge
reign scare realm demon elder cheat spite orbit cloth trunk ranch ferry rider shelf loser wheat flour puppy
clerk drone spark whale armor clash scout poker wreck drake brake purse depot lance chess crane plaza vault
stern slope scrap ditch wagon rogue onion spoon holly abbey alley marsh dough maple niche porch creep goose
grill ruler swamp drift slate yacht pupil sands manor altar atlas stall belle bliss forge daisy trout peach
jelly heath dwarf skate boxer hedge stray brook torch joker glove razor stove wrath crust spear grape titan
wonder master impact damage status camera coffee screen engine bottom spread prison winner handle dinner
fellow driver corner injury museum launch native planet lawyer studio crisis editor stream orange desire
chosen switch fields threat danger heaven bottle cheese parent victim button relief origin weapon client
marine decade defeat wealth shower junior stable pocket guitar killer temple thread horror worker flower
cousin remote butter string bishop resort regret reader foster genius reward priest jacket rocket worthy
knight filter terror garage spider bullet divine gather dealer runner carpet cherry barrel bubble hammer
casino strain wallet cattle stairs trauma pepper closet rookie jungle banner throne potato chains hunger
vacuum statue butler fabric pastor monkey cookie bucket basket sierra static rabbit hatred subway diesel
blonde collar sketch arctic ladder helmet fusion nerves fisher diving cannon upside nephew salmon portal
banana shades fossil infant hazard porter needle canvas pillow absurd herald pencil locker critic mentor
pistol sleeve wizard ginger garlic lounge turtle sphere burial plague misery broker bomber candle graves
marker breeze cowboy splash tomato sights marina maiden barber archer suburb temper ribbon coffin puppet
picnic madame remake vendor tenant drawer banker trader violin supper vanity magnet sorrow arcade sniper
shrine patron saddle thrill trench cutter purity midway eldest bakery coward parcel intern hacker morale
demise bamboo kitten mutant sultan stitch thirst lizard laurel quarry mystic
""")
COLON_LEFT = sorted(set(T_SINGLE) | set(T_NOUNS))
T_SINGLE = T_SINGLE + [w for w in T_SHORT if w not in set(T_SINGLE)]

TITLE_BLOCK |= set(_w("""
gladiator stagecoach vertigo sabotage insomnia arrival gravity collateral twilight eclipse
inferno hereafter zodiac prisoners troy sunshine dunkirk lincoln selma milk shame
""")) | {"the outlaws", "the godfather part ii"}


# Keyword vocabulary: common English nouns (frequency-filtered at development time).
KW_SINGLE = _w("""
abandonment abbey abbot abduction abolition abomination absence absentee abstraction absurdity
abuser abyss acacia academia academy accelerator accent acceptance accessory accident accidental
accomplice accord accordance accordion accountancy accountant accusation achievement acne acorn
acoustic acquisition acquittal acronym activism activist activity actor actress actuality
acupuncture adaptation adapter addict addiction addition adept adherence adhesion adjective adjunct
adjustment adjutant admiral admiralty admiration admirer admission adolescence adoption adoration
adult adultery adulthood advancement advent adventurer adversary adversity advertiser advice adviser
advisor advisory advocacy advocate aegis aerial aeronautics aerosol aerospace affair affection
affidavit affiliate affiliation affinity affirmation affliction affluent afghan afterlife aftermath
afternoon agency agenda agent aggregate aggregation aggressor agitation agnostic agony agreement
agriculture ahem aide aircraft airfield airline airliner airplane airport airspace airway aisle
alarm albino album alchemist alcohol alcoholism alderman alert algae algebra algorithm alias alibi
alien alienation alignment allegation allegiance allegory allergy alley alliance allies ally almanac
almighty almond aloe aloha alpha alphabet altar alteration altercation alto amateur amazement amazon
ambassador ambiguity ambition ambulance amen amendment amir ammo ammunition amnesia amnesty amour
amplifier amplitude amputation amusement analogy analysis analyst analyzer anarchism anarchist
anarchy anatomy ancestor ancestry anchor anchorage ancient android anecdote anemia anesthesia
aneurysm angel anger angst anguish animation animosity annals annexation anniversary announcer
annoyance annual anomaly anonymity anorexia antagonist antarctic antelope antenna anthem anthology
anthrax anti antibiotic antidote antiquity anvil anxiety apartheid apartment apathy aperture apex
apocalypse apology apostle apparatus apparel appendix appetite applause apple appliance applicant
application appointment appraisal apprentice approach approval apron aptitude aquaculture aquarium
arbitration arbor arcade archaeology archbishop archdiocese archery archipelago architect archive
arctic arena argument aria aristocracy arithmetic armada armament armchair armistice armor armory
army arousal arrangement array arrears arrival arrow arsenal arson arthritis article artillery
artisan artist artistry artwork ascension ascent ascot asparagus aspect aspen aspirin assailant
assassin assault assay assembly assent assertion assessment assignment assistance assistant
associate association assortment assumption assurance asterisk asteroid asthma astrology astronaut
astronomer astronomy asylum atheism atheist athlete athletics atlas atmosphere attachment attack
attainment attempt attendance attendant attention attic attire attitude attorney attraction
attribute attribution auction auctioneer audible audience audio audition auditor auditorium aunt
aura author authorities authorship autism auto autograph automation automobile autonomy autopilot
autopsy autumn avalanche avatar avenger avenue aversion aviation avocado avoidance award awareness
awkwardness axiom axis axle azalea babysitter bachelor backbone backdrop backfire backlash backlog
backpack backside backyard bacon bacteria bacterium badge badger badminton bagel baggage bailiff
baker bakery balance balcony bale ball ballad ballast ballerina ballet balloon ballot ballpark
ballroom bamboo banana band bandit bandwagon bane banjo bank banker bankrupt bankruptcy banner
banquet banter baptism baptist barb barbarian barbecue barber bard bargain barker barley barn
barometer baron baroness baroque barrage barrel barrier barrister bartender barter base baseball
basement bash basil basilica basin basket basketball bassist bastion batch bath bathroom bathtub
baton batsman battalion battery battle battlefield battleship bayonet bayou bazaar beach beacon bead
beagle beak beam bean bearer beau beck bedrock bedroom bedside bedtime beech beef beer beet beginner
behalf behavior belief believer bell belle belt bench benchmark bender benefactor beneficiary berg
berry berserk berth bestseller betrayal betterment beverage bias bicycle bidder bigot bigotry bike
bikers bikini bilingual bill billboard billionaire billy binary binder binge bingo binoculars
biographer biography biologist biology biopsy birch bird birth birthday birthplace biscuit bishop
bison bistro bite bitterness bittersweet blackberry blackboard blackjack blacklist blackout
blacksmith blade blah blank blanket blasphemy blaster blazer bleep blend blender blight blind
blindness bliss blister blitz blizzard bloc blockage blockbuster blog blogger blond blonde bloodbath
blossom blouse blower blowout blueberry bluegrass blueprint bluff blush boar boardwalk boat bobby
bodyguard bohemian boiler bologna bolt bomb bombardment bomber bombshell bonanza bond bonfire bong
bonnet bonus boogie booklet bookmark bookshop bookstore boom boomerang boon booster boot booth
bootleg booze border borderline boredom borough borrower boss botanical botany bottle bottom boulder
boulevard bouncer boundary bouquet bourbon bourgeoisie bout boutique bowl bowler bowman boxer
boycott boyfriend boyhood brace bracelet bracket brad brag braille brake branch brand brandy brat
bravo brawl breach bread breadth breakdown breaker breakup breath breather breeder breeze brethren
brewer brewery bribery brick bride bridesmaid bridge briefcase brig brigade brim broccoli brochure
broker brokerage brooch brook broom broth brother brownie browser brunch brunette brush brute buck
bucket buddy budge buff buffalo buffet bugger buildup bulb bull bullet bulletin bullock bullpen
bullshit bully bummer bumper bunch bungalow bunk bunker bunny burden bureau bureaucracy burger
burglar burglary burial burlesque burner burr burrito burrow bush businessman businessmen butcher
butler butte butter button buyer buyout buzzer bypass byproduct bystander cabal cabaret cabbage
cabin cabinet cable cache cactus cadence cadet cadre cafeteria cage cake calamity calculation
calculator calculus calendar calf calibration caliphate caller calligraphy camel cameo camera
cameraman camp campaign campaigner campfire campground campsite campus canal canary candidacy
candidate candle candlelight candy cane canister cannabis cannibal cannibalism cannon canoe canon
canopy cant canteen canton cantor canvas canyon capacitor cape capitalism capitalist capitol capsule
captain caption captive captivity caramel caravan carcass carcinoma card cardigan cardinal
cardiology career caregiver caretaker cargo caricature carnage carnival carol carousel carp
carpenter carriage carrier carrot cart cartel cartoon cartoonist cartridge carver cascade cashier
cashmere casino casket casserole cassette caste castle castor casualty catalog catalogue catapult
catastrophe catcher catchment category caterpillar catfish cathedral catheter cathode cattle caucus
cauldron cauliflower causation cavalier cavalry caveat cavern caviar cavity cedar celebration
celebrity celery cell cellar cello cemetery censor censorship census centenary centennial center
centerpiece centrist centurion century ceramic cereal ceremonial ceremony certainty certificate
cessation chain chainsaw chair chairman chairperson chalet chalice challenge challenger chamber
chamberlain chameleon champagne champion chancellor chandelier chandler channel chaos chap chapel
chaplain chapter character charger chariot charity chaser chastity chat chauffeur cheat cheater
checker checklist checkout checkpoint cheddar cheerleader cheese cheesecake cheetah chef chemist
chemistry cherry chess chestnut chevron chew chick chicken chief childcare childhood chile chili
chilli chime chimney china chino chip chocolate choice choir cholera chopper choral chore chorus
chow chronicle chuckle chunk church chute cider cigar cigarette cinema cinnamon cipher circuit
circuitry circulation circus citadel citation citizen citizenship citrus civilian claim claimant
clam clan clarinet clash classmate classroom clause claw cleaner cleanliness cleanser cleaver clergy
clergyman cleric clerk client cliff climate climax climber clinic clip clipper clique clock
clockwork clone closeness closet closure cloth clothes clout clover clown club clubhouse clue clutch
clutches clutter coach coalition coast coaster coastline coat cobra cockpit cockroach cocktail cocoa
coconut code codex coercion coffee coffin coherence cohesion cohort coil coincidence cola coliseum
collage collar colleague collectible collection collector colleen collision collusion cologne
colonel colonialism colony colossus colt column columnist coma comb combat combination combo
comeback comedian comedy comet comfort comma command commandant commander commandment commando
comment commentary commentator commerce commission committee commodity commodore commotion commune
communion communism communist commuter companion comparison compartment compass compassion
compendium competitor compilation compiler complacency complainant complaint complement completion
complex compliance complicity component composer composite compression compressor comptroller
computation computer comrade concept conception concern concerto concession concierge conclusion
concord concussion condition conditioner condo condominium conductor conduit cone confederacy
confederate conference confession confetti confidence confinement conflict confluence confusion
congestion congress congressman conjecture connective connector conqueror conquest consensus consent
consequence consignment consolation console consonant consortium conspiracy constable constituent
constraint consul consulate consultancy consultant consumer consumption contact contagion container
containment contempt contender content contention contentment contest contestant context continent
contingency continuity continuum contour contraband contraction contractor contributor controller
controversy conundrum convenience convent convention convergence conversion converter conveyor
convict conviction convoy cookbook cooker cookery cookie cooler coop cooper cooperation coordinator
cope copy copyright cord cordon core corn corner cornerstone corolla corona coronary coronation
coroner corp corporation correction corridor corrosion corset cosmos costume cosy cottage couch
cougar cough council councillor councilman counsel counsellor counselor countdown counter
counterfeit counterpart countess countryside county coup coupe couple coupon courier courtesy
courthouse courtroom courtship courtyard cousin cove coven covenant covert coward cowboy coyote crab
crackdown craft craftsman cranberry crane crate crater craven crayon craze craziness creation
creativity creator credence credit creditor creek creep cremation creole crest crew crib cricket
cricketer crime criminology crisis criterion critic criticism critique crocodile crook crop crossbow
crossfire crossword crow crown crucible crucifix crucifixion cruelty cruiser crusade crusader crust
crux crypt cubicle cuckoo cucumber cuff cuisine culmination culprit cult cultivation culture cumin
cupboard cupcake cupid curate curator curb curfew curiosity curriculum curse cursor curtain
curvature cushion cusp custard custodian custody custom cutlery cutter cycle cyclist cyclone
cynicism cypress cyst czar daddy dagger dairy daisy dale damage dame dance dancer dandy danger
daredevil darkness dart dashboard database daughter davenport dawn daybreak daylight daytime deacon
deadline dealership dean dearest debacle debt debtor decade decadent decal deception decision deck
declaration decor decoration decoy decrease deer defamation default defeat defect defendant defender
defense deficiency definition deflection deformation degradation dehydration deity delegation deli
deliverance delivery dell delta delusion dementia demise demo democracy democrat demographic
demolition demon denial denim dent dentist dentistry deodorant departure dependence dependency
depiction depletion deployment deportation deposit depot depression depressive deprivation deputy
derby derivation derivative derrick descent description design designation designer desire desk
desktop desolation despair desperation despite dessert destination destiny destroyer destruction
detachment detail detection detective detector detention deterrent detonation detour detox detriment
devastation developer deviant deviation device devotion devotional dexterity dharma diabetes
diagnosis diagnostics diagram dial dialect dialog dialogue dialysis diaper diaphragm diary dichotomy
dictator dictionary diesel diet dietary dieter difficulty diffraction digger dilemma dill diminutive
diner dinner dinosaur diocese diode diploma diplomacy diplomat direction directive director
directorate directory dirk disability disapproval disarmament disaster disbelief disc discard
disciple discipline disclaimer disclosure disco discomfort discontent discord discount discourse
discovery discretion discussion disdain disease dish dishwasher dislike dismay dismissal disorder
dispatcher dispensary dispenser dispersal dispersion display displeasure dispute disrespect
disruption dissection dissent dissonance distillery distinction distortion distraction distress
distributor district distrust disturbance ditto diva dive diver divergence diversion divinity
division dizziness dock doctor doctorate doctrine document dodge dodger doggie doggy dogma doll
dolly dolphin domain domination dominion donkey donor donut doodle doomsday door doorbell doorstep
doorway dope dork dorm dormitory dory dose dossier doubt douche dough downfall downhill downtime
downtown downturn dragon dragonfly drain drainage drake drama drawer dread dream dreamer drink
drinker drip driver driveway drone drool dropout drought drugstore drum drummer duality duchess
duchy duck dude duel duff dugout duke dummy dumpster dune dungeon duplex duplication duration dusk
duty dyer dynamite dynamo dynasty dysfunction dyslexia eager eagle earl earth earthquake eater eats
eccentric eclectic ecology economics economist economy ecosystem ecstasy eczema eddy edge edible
edict edition editor educator effect effort egalitarian eggplant eighties ejection elder elderly
eldest election electorate electrician electricity electrode electron electronics element elephant
elevation elevator elimination elite elitist elves email embankment embassy emblem embodiment
embrace embroidery embryo emergence emergency emeritus emigration eminence emir emission emotion
empathy emperor emphasis empire employee employer employment empowerment empress emptiness emulation
enactment enclave enclosure encore encryption endeavor endorsement endowment enemy enforcement
engagement engine engineer enhancement enigma enjoyment enlargement enmity enquiry enrichment
enrollment enrolment ensemble ensign enterprise entertainer enthusiasm enthusiast entirety entourage
entrance entry envelope environment envoy envy epidemic epilepsy epilogue episode epitome epoch
equation equator equilibrium equinox equipment equivalence equivalent eradication erotica errand
error eruption escalation escalator escape escort espionage espresso esquire essay essence esteem
estimate estimation estuary eternity ethic etiquette eucalyptus eulogy euphoria evacuation
evaluation evangelist evasion evergreen eviction evidence evil exam examination examiner excavation
exception excerpt exchange excitation excitement exclamation exclusion excursion exec execution
executioner executive exemption exercise exhaustion exhibition exile existence exit exodus expansion
expectancy expectation expedition experiment expertise expiration expiry explanation exploration
explorer explosion expo exporter exposition expressway expulsion extension extent exterior
extinction extradition extremism extremist eyeliner eyesight eyewitness fable fabric fabrication
facade facet facility faction factor factory faculty failure fairy faith fake falcon fallacy fame
familiarity famine fanatic fancy fandom fanfare fang fantasy farce fare farewell farmer farmhouse
farmland fascination fascism fascist fatality fate fatigue fatty faucet fault fauna favor favorite
feast feat feature federalist federation fedora feeder feline fellow fellowship felon felony
feminism feminist fender fern fertility fervor festival fetus feud fever fiasco fiat fiction
fiduciary fielder fiend fiesta fife fifties fighter figure filly film filmmaker finale finalist
finance financier finch finder fingerprint finisher firearm fireball firefighter firefly fireman
fireplace firewall firmware firth fish fisher fisherman fishery fixation fixer fixture flag flagship
flair flak flake flamingo flank flannel flash flashback flashlight flask flavor flaw flea fleet
flicker flight flirt flock flood floor floppy flora florist floss flotation flourish flow flower
fluency fluke flurry flush flute flux flyer foam focus fodder foil foliage folio folk folklore
follower fondness font footage football footballer foothold footnote footprint footwear footwork
forage foray ford fore foreclosure forefront foreground foreman forensics foreplay forestry foreword
forgery forgiveness fork formality formation formula forties fortnight fortress fortune forum fossil
foundry fountain fowl foyer fragment fragrance frame framework franchise frank frat fraternity fraud
freak freedom freelancer freeman freestyle freeway freezer freight freighter french frenzy frequency
fresco fresher freshman friar friction fridge friendship fries frigate fright frog frontier frown
fruit fruition frustration fugitive fulfillment fullback fuller fullness funeral fungi fungus funk
furnace furniture fury fuselage fusion fuss fuzz gable gadget gage gait gala galaxy gale gall
gallery galley gallows gambit gambler gamma gang gangster garage garb garden gardener garland garlic
garment garnish garrison gasp gate gateway gauntlet gaze gazette gear gearbox geek gender genealogy
generation generator genesis genetics genie genius genome genre gent gentile gentleman gentry genus
geography geologist geology geometry germ gestation gesture ghetto ghost giant giggle ginger
gingerbread giraffe girlfriend gist glacier gladiator glaucoma glee glen glide glider glimmer
glimpse glitch globe gloom glory gloss glossary glove glow gluten gnome goal goalie goalkeeper goat
goblin goddess godfather goggles goldfish goldsmith golf golfer gong goodbye goody goofy goon goose
gore gorge gorilla gospel gossip gourmet gout governance governor gown grace grade graduation
graffiti grail grain grammar grandchild grandfather grandma grandmother grandpa grandson grange
granny grape grapefruit grapple grasp grasshopper grassland gratitude grave graveyard gravity gravy
greenhouse grenade greyhound grid grief grievance griffin grill grille grime grin grinder grip
grizzly groan grocer grocery groom groundwork grouse grove grower growl grub grunge grunt guard
guardian guerrilla guidance guide guideline guild guillotine guilt guitar guitarist gulf gull gully
gunfire gunman gunner gunpoint gunshot gurney guru gust gusto gutter gymnasium gymnast gymnastics
habit habitat hacker hackney haiku hairdresser hairline hale halfback halftime hall hallelujah
hallway hamburger hamlet hammer hammock hamper hamster handbag handball handbook handgun handicap
handler handout handset handshake hangar hanger hangout hangover hank happiness harassment hardcover
hardship hardware hare harm harp harrow hart harvest hash hassle hatchet hate hater haul haven havoc
hawk hawthorn hazard haze hazel headache headband headmaster headphone headset healer healthcare
heap hearsay heartache heartbeat heartbreak hearth heartland heat heater heath heathen heather
heaven heavyweight hector hedgehog heel hegemony heir heiress heist helicopter hello helm helmet
helper hemisphere hemorrhage hepatic hepatitis herb herbal herd heresy heretic heritage hermit
hernia hero heroine heron hertz hesitation heyday hiatus hibernation hickory hideout hierarchy
highland highness highway hike hill hillside hilltop hind hindrance hindsight hinge hint hippie
hippo hippy historian hitch hitter hive hoax hobbit hobby hobo hockey hogan holder hole holiday
holly holocaust hologram holster holy homage homeland homeless homeowner homepage hometown homework
homicide homophobia honey honeymoon honor hood hoof hookup hoop hooray hopper horde horizon horn
hornet horoscope horror horse horseback horseman horseshoe hose hospice hospital hospitality host
hostage hostel hostess hostilities hotel hound hour household housekeeper housewife housework howdy
hubby huddle hula hulk hull humanities humankind humanoid humidity humiliation hummus humor hunch
hunk hunt hunter hurdle hurricane hurry husband hutch hybrid hydra hygiene hype hypnosis hypocrisy
hypocrite hypothesis hysteria iceberg icon idealism identifier ideology idiot idol ignorance illness
illusion illustrator image imagery imagination imam imbalance imitation immersion immigrant
immigration immortal immunity immunology impact impairment impala impeachment impedance impediment
imperialism imperialist impetus implication import importation importer imposition impression
imprint impromptu improvement impunity inability inaction inactivity incarnation inception incident
inclination inclusion incubation incubator indication indicator indictment indignation induction
industry infancy infant infantry infection inference inferno infertility infestation infield
infinity infirmary influenza info informant ingenuity ingredient inhalation inheritance inhibition
initial initiation injection injunction injury injustice inlet inmate innovation innovator inpatient
input inquest inquiry inquisition insanity inscription insect insecurity insert insertion insight
insignia insistence insolvency insomnia inspection inspector inspiration instability instalment
instance instinct institution instruction instructor instrument insulation insult insurer insurgency
insurgent intake integration integrity intellect intent intention interaction interchange
intercourse interface interim interlude internet internship interplay interpreter interstate
interval interviewer intrigue intro intruder intrusion intuition invasion invention inventor
inventory inversion investment investor invitation invoice involvement ionization iris irony
irradiation irrigation irritation island islander isle isolation issuance item itinerary jackass
jacket jaguar jail jailbreak janitor japan jargon jasmine jazz jealousy jeep jelly jellyfish
jeopardy jerk jersey jest jetty jewel jewelry jigsaw jimmy jingle jinx jive jock joke joker jolly
jolt journal journalism journalist jubilee judgement judgment judiciary judo juice jukebox jumper
jumpsuit junction juncture jungle junior juniper junkie junta juror jury kangaroo karaoke karate
karma kayak kebab keeper kennel kernel ketchup kettle keyboard keynote keystone khaki khan kicker
kickoff killer kiln kingdom kingpin kink kiosk kiss kitchen kitten kiwi knack knife knight knit knob
knockout knot koala kudos labor laboratory labyrinth lack lacrosse ladder lady lager lagoon lair
lake lama lamb lambda lame lament lamp lance lancet landfall landfill landline landlord landmark
landowner landscape landslide lane language lantern laptop lark lasagna laser latch latency latitude
latte lattice laugh laughter launcher laundry laureate laurel lavender lawmaker lawn lawsuit lawyer
layout leader leadership leaf league leak leakage leap learner leash lecture lecturer ledge leech
leftist lefty legend legion legislation legislator legislature leisure lemon lemonade lender lens
leprosy lesion lesson letter leukemia lever leverage leviathan lexicon liability liaison liar libel
liberalism liberation libertarian liberty libido librarian library licence license licensee lieu
lieutenant lifeboat lifeguard lifespan lifetime lighthouse lightweight lilac lily limbo limelight
limerick limitation limo limousine linden lineage linebacker lineman linen liner lineup lingerie
lingo linguistics lion liquidation liquidity liquor lisp listener literacy literature litigation
litter liturgy livery livestock lizard load loader loaf lobby lobbyist lobster locality locker
lockout locomotive locus locust lodge loft logic logistics logo lollipop loneliness longer longitude
lookout looney loop loophole lord lordship lore lorry loser lotion lottery lotto lotus lounge lover
loyalist luck luggage lullaby lump lunatic luncheon lunchtime lupus lust lymphoma lynx macaroni
machete machine machinery macho macintosh mackerel macro madam madame madman madness madras maestro
magazine magic magician magistrate magnate magnet magnetism magneto magnolia magnum mahatma mahogany
maid maiden mail mailbox mainland mainstay mainstream maintenance maize maker makeshift makeup
malaria male malfunction malice mall mallet malpractice mama mammal mammalian mammoth management
manager mandarin mandate mandatory mane maneuver mango manhunt maniac manifesto manifold mankind
mannequin manor manpower mansion mantis mantle mantra manuscript maple marathon mare margarita maria
marina mark marker marketplace marlin maroon marquee marquis marriage marsh marshmallow mart martian
martin martini martyr martyrdom mascara mascot mason masonry masquerade massacre mast master
mastermind masterpiece mastery mate materialism maternity math mathematics matrix matron mattress
maturity maverick maxim mayhem mayo mayonnaise mayor maze mead meadow meal meantime measles measure
measurement meat mecca mechanic medal medalist mediation mediator medic medication medicine
meditation medium medley melancholy melanoma melodrama melody melon member membership membrane meme
memo memoir memorabilia memorandum memorial memory mend meningitis menopause mentality mention
mentor menu meow merchandise merchant mercy merger meridian mermaid mesa mess messenger messiah
metallic metaphor metaphysics meteor meteorite meteorology method methodology metro metropolis
mickey microphone microscope microscopy microwave midday middle midland midnight midst midsummer
midterm midway midwife migraine migrant migration mike milestone militia milk milkshake mill
millennium miller millionaire mime mimic mine miner miniature minimalist minion minister ministry
minivan minority minute miracle mirage mirror miscarriage mischief misconduct misdemeanor misery
misfortune mishap mismatch misogyny missile mission missionary mistake mister mistress mistrust
mitigation mixer moan moat mockery model modem modernism modernist modulation module moisture
molasses momma mommy monarch monarchy monastery monastic moniker monitor monk monkey mono monochrome
monogram monograph monologue monopoly monsieur monsoon monster montage monthly monument mood moody
moon moonlight moose morale moratorium moray morgue morn morocco morphine morphology morrow mortar
mosaic mosque mosquito moss motel moth motherland motif motion motley motor motorbike motorcycle
motorist motorway motto mound mountain mouse mouthpiece movement mover movie mower mozzarella muffin
mulberry mule multimedia multiple mummy munch mural murderer muse museum mushroom musician mustang
mustard mutant mutation mute mutilation mutiny mutton muzzle myrtle mystery mysticism myth mythology
nacho namesake nanny napkin narration narrative narrator nasal natal nation nationalist nationality
nativity naturalist nausea nave navigation navigator navy necessity necklace needle neglect
negligence negotiation negotiator neighbor nemesis nephew nerd nervousness nest network neurologist
neurology neutrality neutron newbie newcomer newsletter newspaper newt newton niche nickelodeon
nickname niece nightclub nightfall nightingale nightlife nightmare nighttime nineties ninja nirvana
nobility nobleman nobody noel noise nomad nomination nominee none nonfiction nonprofit nonsense
noodle nook noon northwest nostalgia notary notation note notebook notice notion notoriety noun
nourishment nova novel novelist novella novice nowadays nowhere nozzle nuance nugget nuisance
nursery nutmeg nutshell oasis oath oatmeal obedience obituary objection obligation oblique oblivion
observance observation observatory observer obsessive obstacle obstetrics obstruction occasion
occupancy occupant occupation occurrence ocean octave octopus odyssey offender offense officer
offset offside ogre okay olive ombudsman omega omen omission omnibus oncology onion onset onslaught
opera operation opinion opium opponent opportunity opposition oppression optimism optimist opus
oracle orange orbit orchard orchestra orchid ordeal orderly ordinance ordinary ordination ordnance
organizer oriental orientation origin originality ornamental orphan orphanage ostrich ottoman
outback outbreak outburst outcast outcome outdoors outfield outfielder outfit outlet outline outlook
outpatient outpost output outrage outreach outset ovation oven overall overcast overdrive overflow
overhaul overlap overlord oversight overthrow overtime overture overuse overview oxford oyster pace
pacifist package packer packet pact paddock paddy padre pagan page pageant pain painter paisley
palace palliative palsy pamphlet pancake panda pane panel pang panic panorama pant pantheon panther
pantomime pantry papa papacy paperback paperwork parable parachute parade paradise paradox paragon
paralysis paramedic parameter paranoia paranoid paraphrase parasite parcel pardon parent parenthood
parish parity park parkway parliament parlor parody parole parrot parry parsley participant partisan
partition partner partnership partridge passage passenger passion passport password pasta pastime
pastor pastoral pastry pasture patchwork paternity path pathogen pathologist pathology patient patio
patriarch patriarchy patriot patrol patron patronage pattern patty pause pave pavement pavilion
payable payday payer payload peace peacetime peach peacock peanut pear peasant pebble pedagogy pedal
pedestal pedestrian pediatrics pedigree peer pelican penalty penance penchant pencil pendant
pendulum penetration penguin penicillin peninsula pentagon penthouse penultimate pepper peppermint
pepperoni percentile perception perch percussion perfection performance performer perfume peril
periodical perjury perm permission permit perpetrator persecution persona personnel perspective
persuasion pest petal petition phantom pharaoh pharmacist pharmacy phase pheasant philosopher
philosophy phobia phoenix phony photo photography photon phrase physician physicist physiology
pianist piano piazza piccolo picket pickle pickup picnic picture piece pier pigeon piggy pike pile
pilgrim pilgrimage pill pillar pillow pilot pinball pinch pine pineapple pinnacle pinpoint pinto
pipe pipeline piper piracy pirate pistol piston pita pitcher pitchfork pity pivot pixel pixie pizza
placebo placenta plagiarism plague plaid plaintiff plane planet plankton planner planter plate
plateau platform platoon platter playback playboy playground playhouse playlist playoff playwright
plaza plea pleasure plight plot plough ploy plug plum plurality plywood pneumonia pocket podium poem
poet poetry pointer poke poker pole policeman policy polio politician politico polka poll pollen
pollution polo polygamy polynomial polytechnic pond pony poodle pool popcorn pope poplar poppy
populace population populism populist porcelain porch pork porridge portal portfolio portrait
portrayal posse possession possibility postcard postcode postman postmaster potato potential potion
pottery pouch poultry poverty powerhouse practice prairie praise prank prayer preacher precaution
precedence precedent precinct predator predecessor predicament prediction predictor preface prefect
prefecture preference prefix pregnancy preliminary prelude premier preparation preschool presence
presidency pressure prestige presumption pretense pretext prevention preventive preview prey pride
priest priesthood primate prince princess principle print prior priority priory prison prisoner
privy probate probation probe procedure procession processor proctor procurement prodigy producer
product production prof profanity profession professor profile progeny prognosis programme
programmer progress progression prohibition projectile projection projector prologue prom promenade
prominence promoter promotion pronoun proof prop propaganda propagation propeller propensity
prophecy prophet proponent proposal proposition proprietor propulsion prose prosecution prosecutor
prospect prospectus prosperity protagonist protection protector protest protestant protester
protocol proton prototype provenance proverb providence provider province provision provocation
provost prowess proxy psalm pseudo pseudonym psyche psychiatry psycho psychology psychopath
psychosis psychotic puberty publication publicist publicity publisher puck pueblo puff puke pulp
pulpit pulse puma pumpkin punch punctuation pundit punishment punk punter pupil puppet puppy
purchase purchaser purgatory puritan purity purpose purse pursuit puzzle python quack quad quadrant
quadruple quail qualifier quantum quarantine quark quarrel quarry quarterback quay queen query queue
quill quiz quorum quotation rabbi rabbit rabble rabies race racecourse racer racetrack racism racket
radar radiance radiation radiator radio radiology raffle rage raider railway rain rainbow rainfall
rainforest raisin raja rally rampage ranch rancher ranger rank rant rapper rapture rascal rash
raspberry ratchet rate ration rationale rationality rattle ravine razor reactionary reactor reader
readership readiness realist reality realization realm realtor reaper rear reassurance rebel
rebellion rebirth rebound rebuke rebuttal recap receipt receiver reception recess recession recipe
recipient recital reclamation recognition recourse recovery recreation recruiter recruitment rector
recurrence redeemer redemption redhead redneck reduction redundancy redwood reef reel reelection
referee reference referendum referral refill refinement refinery reflection reflector reflex
reformation reformer refuge refugee refusal regard regency regent reggae regime regimen region
registrar registry regression regulation regulator rehearsal reign reindeer rejection relative
relativity relay release relegation reliance relic relief religion relish relocation reluctance
remains remake remark rematch remedy remembrance reminder remission remorse removal renaissance
rendezvous rendition renegade renewal renovation renown repayment repeal repentance repertoire
repetition replacement replica replication reply reporter repository repression reprint reptile
republic republican reputation requiem requirement requisite resale researcher resentment
reservation residence residency resident resignation resistance resistor resolution resonance resort
respect respiration respite respondent response restaurant restoration restraint restriction
restroom result resultant resumption resurgence retaliation retention rethink retirement retreat
retrospect reunion revelation revenge reverence reverend reversal review reviewer revision revival
revolution revolver revue reward rhapsody rhea rhetoric rhino rhyme rhythm ribbon rice rick rider
ridge ridicule riff rift ringer rink riot ripper ripple risk rite ritual rivalry river riverside
roadblock roadside roadway roast robber robbery robe robin robot robotics rock rocker rocket rodent
rodeo rogers rogue role roller romance roof rooftop rook rookie roommate roost rooster root rope
rosary rosemary roster rotary rotation rotor rouge round roundabout rounder roundup router routine
rover rowdy rower rudder rugby ruin rule ruler rumble rumor rump runaway rundown rune runner runoff
runway rupture ruse rush saber sabotage sabre sack sacrament sacrifice saddle sadness safari
safeguard safety saffron saga sage sahib sailor saint salaam salad sale salesman sally salmon
salmonella salon saloon salsa salvation samba sample samurai sanction sanctuary sandbox sanitation
sanity sarcasm sari sash satellite satin satire saucepan sauna sausage savannah saver savior saviour
savory savvy sawyer saxophone scaffold scam scandal scanner scapegoat scar scare scarecrow scenario
scene scenery scent schedule schema schematic scheme schism scholar scholastic schoolboy schoolgirl
schooner science scientist scion scissors sclerosis scooter score scoreboard scorer scorn scorpion
scourge scout scrabble scrap scratch scream screen screenplay screw screwdriver scribe scrimmage
script scripture scrutiny scuba sculptor sculpture scum seaboard seafood seal seam seaman search
seaside seasonal seat secession secretariat secretary sect section secularism security sedan
sedition seduction seeker seer segment seizure selection selector seller semantics semester semi
semifinal seminar seminary senate senator sender seniority sensation sense sensibility sensitivity
sensor sentence sentiment sentinel sentry separation separatist sepsis sequel sequence serge
sergeant seriousness sermon serpent servant server servitude sesame session setback settlement
settler setup seventies severance sewer sexism sexist sexton shade shadow shaft shah shaker sham
shaman shampoo shanghai shank shard shareholder sharia shark sharper sharpness shawl sheath sheep
sheet sheik sheikh shelf shell shellfish shelter shepherd sheriff sherry shield shipment shipper
shipyard shire shirt shiver shock shocker shoe shoemaker shooter shootout shopper shoreline shortcut
shorthand shortlist shortstop shotgun shovel showcase showdown shower showroom shrapnel shrimp
shrine shroud shrub shrug shudder shutdown shutout shutter shuttle sickle sickness sidebar sidekick
sideline sidewalk siege sierra sigh sight sigma sign signal signature silence silhouette silk sill
silo silverware simulation simulator sincerity singer sinner sire siren sister sitcom sitter
situation sixties skate skateboard skater skepticism sketch skier skill skillet skipper skirmish
skirt skit skyline skyscraper slab slalom slam slander slap slate slaughter slave slavery slayer
sleep sleeper sleeve slide slider slip slipper slit slogan slope slot slough slowdown slug slum
slumber smack smallpox smear smell smiley smirk smith smog smoke smoker smoother smoothie snack
snail snake snap snapper snapshot snare snatch sneeze sniper snippet snoop snout snow snowball
snowboard snowfall snowflake snowman soap sobriety soccer socialism socialist society sociologist
sociology sociopath sock sofa softball software soil solace soldier sole solicitor solitaire
solitude solo soloist solstice somewhere sonar sonata songwriter sonny sophomore soprano sorcerer
sorcery soreness sorority sorrow sort soul soundtrack soup source souvenir sovereignty soviet
soybean spacecraft spaceship spade spaghetti spam span spank spark sparrow speaker spear spec
specialist specimen spectacle spectator specter spectrum speculation speech speedway sphere sphinx
spider spike spinach spinal spinner spire spirit spit spite split spoiler spokesman spokeswoman
sponsorship spoof spoon spore sport sportsman spot spotlight spouse spread spreadsheet spree
springtime sprinkler sprint sprinter sprite sprout spruce spur squad squadron squash squat squid
squire squirrel squirt stab stack stadium staff staffer stage stagnation stair staircase stairway
stalemate stalker stall stallion stand standard standby standoff standpoint standstill stanza staple
star starboard stardom starfish starlight starter startup starvation statement statesman station
stationery statistic statue stature status statute stave stead steak stealth steamboat steamer
steamship stein stem stench step stepfather stepmother stereo stereotype steward stewardship sticker
stigma stimulant stimulation stimulus stint stitch stoic stomp stone stoner stool stoppage stopper
storage store storey storyteller strain strait strand stranger strap strategist strategy strawberry
streak stream streamer streetcar stress stride strife striker stringer stripe stroke stroll stroller
stronghold structure strut stub stud student studio stump stunt stupidity sturgeon stylist stylus
subclass subdivision subgroup subject submission subpoena subscriber subsection subset subsidiary
substitute subtitle subtlety suburb subversion subversive subway success successor succulent sucker
suction sufficiency suffix sugar suggestion suit suitcase suite sultan summertime summit summons
sumo sunflower sunglasses sunlight sunrise sunscreen sunset sunshine superman supermarket supermodel
supernova superpower superstar supervision supervisor supper supplement supplier supporter
supremacist supremacy surface surfer surgeon surgery surname surprise surrender surrey surrogate
surveyor survival survivor sushi suspense suspicion swain swami swamp swarm swat sweater sweatshirt
sweepstakes sweetheart sweetie sweetness swift swimmer swimsuit swine switch swoop sword syllable
syllabus symbol symbolism sympathy symphony symposium symptom synagogue syndicate syndrome synod
synonym synopsis syntax syringe syrup tabernacle table tablet tabloid taboo tack tackle taco tactic
tail tailgate takeoff takeover taker tale talent talisman tango tank tanker tantrum tape target
tarot tart task taste tattoo tavern taxonomy taxpayer teacher teammate teamwork teaser tech
technician technique techno technology teen telecast telegram telegraph telemetry telephone
television teller temp tempest template temple tempo temptation tenancy tenant tendency tenet tennis
tenor tension tensor tent tenure tequila termination terminator terminology terminus terrace terrain
terrier territory terror terry tertiary testament testimonial testimony text textbook textile
thatcher theater theatre theft theme theologian theology theorem theorist theory therapist therapy
thermometer thermostat thesis theta thief thinker thirst thirties thistle thong thorn threat
threshold thrift thriller throne throughput throwback thug thunderbolt thwart thyme tick ticket tide
tier tiff tiger tights tile tilt timeline timer timetable tinker titan title toad toast toaster
tobacco toddler tofu toggle toil token tomato tomb tombstone tome tomorrow tone tonight tool
toothbrush toothpaste topic topology torch torment tornado torpedo torque torrent tort tortilla
tortoise torture tote totem touchdown tour tourism tourist tournament tourney tout towel tower
township toxicology tracer track tracker tract traction tractor trade tradition traffic tragedy
trailer trainee trainer traitor trajectory tram tramp trampoline trance transaction transcript
transformer transfusion transient transistor transition translation translator transmitter
transponder transport transporter trap trauma traveler traveller traverse travesty tray treadmill
treason treasurer treatise treatment treaty trek tremble tremor trend trial tribe tribunal tribune
tribute trick trickle trident trigger trilogy trimester trip triple tripod trivia trolley troop
trooper trope trophy trot trouble trough troupe trout truce truck truffle trunk truss trustee trusty
truth tsar tsunami tube tuck tucker tulip tuna tundra tune tunnel turbine turbulence turf turkey
turmoil turnaround turner turnout turnpike turret turtle tutorial tutu tuxedo twenties twilight twin
twinkle twist twister twitter tycoon typewriter typhoon typo typography tyranny tyrant ukulele ulcer
ultimatum ultrasound ultraviolet umbrella umpire uncle underdog underground underside undertaker
underwear underworld unhappiness unicorn unification union unison unity universal universe unrest
unseen upbeat upgrade upheaval upkeep upland upper uproar upset upside uptake uptown urgency usage
user usher utility utilization utopia vacancy vacation vaccination vaccine vacuum vale valentine
valet validation valley valuation value vampire vandalism vane vanguard vanilla vanity vantage
variable variance variant variation variety varnish varsity vase vault veal vector vegan vegetable
vegetarian vegetation veggie vehicle veil velocity vendetta vendor veneer vengeance vent ventilation
venture venue verb verdict vernacular versatility verse version vertex vertigo veteran veterinary
veto vial vibration vicar viceroy vicinity victim victor victory videotape view viewer viewpoint
vigil vigilance vigilante villa village villain vine vinegar vineyard vintage viola violation
violence violet violin violinist viper virgin virus viscount vision visionary visitation visitor
vista viva vocabulary vocalist vocation vodka vogue voicemail volcano volleyball voltage voluntary
volunteer voodoo vote voter voucher vowel voyage voyager vulture wade waffle wager wagon waiter
waitress waiver walker walkway wall wallet walnut waltz wand wanderer wannabe ward warden wardrobe
ware warehouse warfare warhead warlord warmer warmth warp warrant warranty warren warrior warship
wartime washer wasp wasteland watchdog watcher watchman watercolor waterfall waterfront watermelon
waterproof waterway wave weakness wealth weapon weaponry wearable wearer weasel weaver webcam
website weekday weekend weekly weir weirdo weld welfare wellington werewolf wetland whale whatnot
wheat wheel wheelchair wheeler whereabouts whim whiplash whirlwind whiskey whisky whisper whistler
wick wicket widow widower wiener wiggle wight wildcat wilder wilderness wildfire wildlife willow
wilt winch wind windmill window windshield wine winery winger winner winter wipe wireless wisdom
witch witchcraft withdrawal witness wizard wobbly wolf wolverine wonder wonderland wont woodland
woodwork woof wool worker workflow workforce workload workmanship workout workplace workshop
workstation worm wraith wrapper wrath wreath wreck wreckage wren wrestler wright writ writer
xenophobia yacht yahoo yank yarn yearbook yearly yell yelp yesterday yeti yoga yoghurt yogi yogurt
yoke yolk youngster youth zeal zebra zenith zeppelin zest zeta zipper zodiac zombie zone zoology
""")
KW_PERSON = _w("""
director chief character brother lord daughter minister officer student husband manager coach sister
secretary leader lady author master professor doctor captain teacher executive partner soul winner
chairman artist spirit patient boss youth guide driver guard prince assistant governor writer
attorney hero girlfriend lawyer candidate actor mayor editor champion boyfriend senator parent
victim premier consumer mate deputy amazon client princess witness singer pilot commander miller
ford engineer employee speaker monster junior hunt relative killer soldier server uncle duke angel
actress producer lieutenant worker walker ordinary designer saint dragon cousin colonel dean buddy
citizen associate resident pope passenger journalist bishop ward monitor hunter daddy virgin
reporter ambassador twin reader teen priest genius trailer fighter communist slave tiger celebrity
carrier alien volunteer stranger specialist knight warren lover homeless guardian cooper screw khan
inspector emperor terry mama grandfather maker civilian chef baker socialist employer bobby amateur
veteran scientist poet hood detective creator advocate wright villa tourist punk prisoner opponent
developer turner victor runner physician earl warrior sheriff politician gentleman counsel aunt
tackle swift farmer peer mason grandmother surgeon rookie mandatory controller consultant companion
chancellor activist prof feminist witch voter sergeant neighbor grandma defender athlete provider
servant rogers widow trainer rebel pastor merchant lodge freak fairy contractor butler bride
architect supporter burger elder demon diesel immigrant hart blonde vampire buyer analyst superman
rider liar keeper instructor fisher voluntary visitor seller nephew musician loser goddess advisor
survivor jerk escort clerk admiral successor infant fossil dancer affiliate whale seasonal refugee
prophet prey freshman defendant colleague therapist scout bachelor scholar rapper pirate nominee
investor drake dame comedian vegan supervisor spouse quarterback messenger lame critic businessman
zombie recipient prosecutor newton adviser wizard treasurer painter monk mentor clown amen
subsidiary researcher donor crane papa observer nationalist coordinator collector striker shepherd
hostage historian griffin cardinal rogue mommy landlord heir browser broker villain thief ranger
bunny baron ninja economist bully yahoo taxpayer referee mistress mickey maid dentist congressman
baptist grandson explorer cowboy composer blogger teammate supplier ruler exile creep toddler
superstar sage missionary freeman wellington predecessor niece murderer maiden guru archbishop shah
roommate pupil protestant partisan narrator competitor carpenter barber performer madame grandpa
conductor atlas vendor tucker spokesman shrimp pitcher mechanic goalkeeper fuller fascist counselor
constable capitalist belle vegetarian tenant sailor phantom participant lightweight banker wheeler
viewer valentine polo immortal bravo rover duchess billionaire accountant veterinary temp migrant
gore chandler butcher sweetheart stud reverend psycho policeman joker challenger boxer sniper proxy
patron patriot paranoid oriental millionaire bankrupt philosopher lecturer hulk contributor almighty
tribune predator pedestrian magistrate technician songwriter quad oracle offender moody jumper
cutter confederate captive apprentice traitor titan taco sophomore solicitor rabbi monarch
footballer eldest diplomat councillor coaster avatar aide trustee protector preacher piper drummer
courier clone addict translator savior protagonist hacker coward commentator believer nerd mute
distributor dictator assassin samurai sultan sonny salesman mutation mutant lender dummy applicant
warden tracker shareholder scorer puck leftist hogan guitarist groom sexist peasant paddy ottoman
mascot heavyweight filmmaker atheist waiter pseudo novelist lookout knockout granny geek chap
casualty caller weaver sheikh referral quarry hale contender consul breaker bourbon attendant
astronaut adapter transmitter sucker nanny muse madam librarian inventor chamberlain buff barker
orphan miner foreman eccentric cyclist columnist beau announcer traveler sweetie organizer mummy
libertarian hector goofy cashier waitress scanner promoter programmer playboy pagan follower convict
calculator booster spoiler plaintiff messiah gangster educator deity curator comrade blond unicorn
skipper sawyer interpreter inmate fugitive catcher brewer planner magician heroine countess wrestler
subscriber listener flirt examiner bilingual beginner usher spectator interviewer chemist router
pivot imam hitter handler bohemian bartender traveller teller swimmer mimic gardener fisherman
ancestor thug pianist lama goalie envoy diner contestant bowler bidder badger auditor voucher
thatcher teaser reviewer piston mermaid eddy alto statesman sleeper siren martyr illustrator garland
extremist enthusiast bowman apostle steward stalker slayer regent racer marquis finalist entertainer
empress divinity caretaker brat wolverine torpedo powerhouse orderly godfather canary trainee sire
psychotic obsessive mead lunatic coroner chaplain bearer abbot wilder visionary trooper physicist
incarnation eater diva dearest brute sentinel seeker qualifier novice momma kicker hubby helper
genie diver crook vocalist stylist snoop riff newcomer hypocrite housewife culprit brunette batsman
amir thinker sinner robber playwright monsieur martian hobbit deacon surrogate pilgrim guerrilla
disciple cleric bodyguard baroness advertiser vicar umpire transient tart smoker scorpion registrar
populist intruder firefighter eclectic compiler commodore beneficiary barrister bandit affluent
tyrant surveyor spinner purchaser mastermind linebacker hippie gourmet fodder censor anarchist wasp
phony maroon learner hostess golfer dyer cadet breeder biologist washer sculptor rocker rector
pharmacist nemesis highness classmate burglar bard werewolf weirdo voyager underdog toaster saviour
maverick jackass informant cheerleader carver adept skater psychopath pharaoh perpetrator outpatient
jock healer gunman eyewitness counsellor antagonist vigilante soprano raja raider proprietor
patriarch hydra gunner goblin embodiment commando surfer rounder reaper depressive colleen cameraman
zeppelin navigator mediator housekeeper exporter daredevil adversary tinker terminator stoner squire
puke minimalist finder dreamer conveyor barbarian youngster saver picket midwife ensign dharma
wannabe supremacist strategist recruiter realist packer maestro macho electrician dodger blacksmith
artisan throwback smoothie sharper realtor prodigy lefty headmaster emeritus dandy cricketer
borrower stepfather sidekick hanger commandant wight taker shaker ripper renegade redhead pueblo
proctor fanatic cheater budge squirt shaman reactionary payer medalist maniac madman lineman
laureate fullback craftsman accomplice subversive slider sender schoolboy rowdy mover modernist
hermit goldsmith geologist crusader conqueror brownie babysitter skier seaman newbie legislator
janitor insurgent homeowner gnome cupid bassist weasel watchdog tracer sprite sprinter shopper
scholastic paramedic gladiator fielder craven admirer undertaker tout sitter firth drinker bigot
adventurer wiener valet selector hairdresser felon digger councilman clergyman chauffeur centrist
cavalier absentee yogi whistler viscount tycoon tsar theorist stepmother sportsman politico
inpatient astronomer alderman stoic settler provost proponent pixie pathologist naturalist gent
gambler chairperson bombshell auctioneer sorcerer shocker primate postmaster ombudsman jinx
imperialist hater finisher cuckoo claimant cantor abuser reformer redneck negotiator juror
grandchild concierge chaser abomination spokeswoman separatist predictor hunk custodian bouncer
adjutant scapegoat rower protester padre occupant notary macaroni landowner goon esquire caregiver
warlord violinist supermodel staffer sheik schoolgirl postman planter ogre namesake monastic
lobbyist loader heathen fiend evangelist dork creditor chameleon ballerina wren respondent prefect
outcast leviathan heron executioner complainant biographer benefactor avenger assailant wearer
viceroy stroller storyteller sexton sentry scribe munch importer hobo dropout dispatcher debtor
checker bridesmaid blaster sociopath rascal publicist pacifist nomad motorist lifeguard lawmaker
horseman heiress gymnast elitist creole comptroller cartoonist alchemist ringer quack pundit mime
mannequin mainstay mahatma islander flak egalitarian colossus punter ostrich minion fiduciary emir
centurion cannibal albino swami stringer sociologist shortstop neurologist magnate friar fixer
federalist decoy decadent wobbly widower watcher trusty scion rancher loyalist licensee gentile
deviant curate tutu shoemaker overlord optimist nobleman grower fresher dieter bystander agnostic
yeti watchman wanderer shipper seer sahib rhea redeemer puritan outfielder matron innovator grocer
florist financier braille berserk aggressor yank theologian swain sphinx soloist snapper progeny
looney kingpin hippy heretic halfback gull freelancer czar campaigner bugger bailiff
""")
KW_PLACE = _w("""house apartment hotel motel hospital prison school church farm ranch island forest desert
mountain lake river cave mine castle mansion cabin lighthouse bridge tunnel bunker laboratory factory
warehouse casino nightclub bar restaurant diner theater museum library village town city cemetery temple
asylum orphanage boarding school monastery""")
KW_OBJECT = _w("""painting diamond necklace ring sword gun rifle bomb map letter diary photograph tape film computer
phone camera statue treasure gold money book manuscript key box suitcase coffin crown mask doll relic
artifact amulet violin car truck train ship submarine airplane motorcycle bicycle boat spaceship satellite""")
KW_ANIMAL = _w("""horse dog cat wolf bear shark snake bird dragon monster spider crocodile gorilla dinosaur
lion tiger eagle rat""")
KW_EVENT = _w("""robbery heist murder kidnapping wedding funeral divorce election war invasion revolution
strike riot trial investigation escape rescue chase accident crash explosion fire flood earthquake storm
epidemic outbreak experiment conspiracy betrayal affair reunion vacation tournament competition race
concert festival ceremony auction party protest mutiny siege battle duel ambush assassination scandal
blackmail ransom fraud smuggling hijacking expedition pilgrimage""")


# --- Title generation: real words, grammar templates, exact length by choice only ---
SMALL_WORDS = {"a", "an", "the", "of", "and", "in", "on", "at", "to", "for", "from", "with", "into", "under", "over"}
T_EXTRA_WORDS = _w("goodbye hello farewell my your our their his her no one last first only every once upon ash fog ice oak ivy sky sun war ark elm north south east west")
T_POSSESSORS = _w("""
keeper captain widow hunter sailor soldier stranger prophet thief spy orphan sister brother
daughter father mother neighbor gambler smuggler pilot doctor dancer singer poet painter
magician explorer fisherman farmer miner blacksmith tailor heiress duchess sheriff ranger
""")
T_PREPS = ["Beyond", "Under", "After", "Before", "Across", "Into", "Between", "Behind", "Against", "Without"]


def _sgl(word: str) -> str:
    return word[:1].upper() + word[1:]


def title_case(text: str) -> str:
    out = []
    start = True
    for tok in text.split(" "):
        low = tok.lower()
        if not start and low in SMALL_WORDS:
            out.append(low)
        else:
            out.append(tok if tok[:1].isupper() or not tok[:1].isalpha() else _sgl(tok))
        start = tok.endswith(":")
    return " ".join(out)


TITLE_WORDS = (
    set(T_NOUNS) | set(T_ADJS) | set(T_PLURALS) | set(T_GERUNDS) | set(T_NUMWORDS)
    | set(T_SINGLE) | set(T_FUNCTION) | set(w.lower() for w in T_ROMAN) | set(T_EXTRA_WORDS)
    | set(T_POSSESSORS) | set(p.lower() for p in T_PREPS)
)


def title_tokens(title: str) -> list[str]:
    """Lower-cased word tokens of a title, for the word-list check (digits excluded)."""
    toks = []
    for raw in re.split(r"[\s:,\"]+", title):
        tok = raw.strip("'.!?").lower()
        if tok.endswith("'s"):
            tok = tok[:-2]
        if not tok or any(ch.isdigit() for ch in tok):
            continue
        toks.append(tok)
    return toks


T_PLACE = _w("""harbor river valley mountain canyon desert forest meadow orchard garden village city kingdom
empire frontier border coast shore ocean sea lake creek bridge tower castle palace cathedral chapel
lighthouse station highway road railway island moon stars sun sky horizon dawn dusk night storm north
south west east wilderness islands mountains valleys rivers""")
T_MASS = _w("""winter summer autumn spring silence fire smoke dust ash gold silver iron glass thunder midnight
dawn dusk twilight grace honor glory courage valor revenge vengeance mercy justice redemption salvation
memory steel stone copper smoke shadow""")


T_GERUNDS_T = _w("chasing finding losing leaving crossing burning breaking holding keeping saving remembering forgetting watching guarding building seeking hunting")


def _phrase(rng: random.Random) -> str:
    """One title phrase (no colon, comma or digit) from a small grammar."""
    n, a, p, g, m = T_NOUNS, T_ADJS, T_PLURALS, T_GERUNDS_T, T_MASS
    r = rng.randrange(18)
    if r == 0:
        return f"{rng.choice(a)} {rng.choice(n)}"
    if r == 1:
        return f"the {rng.choice(a)} {rng.choice(n)}"
    if r == 2:
        return f"the {rng.choice(n)}"
    if r == 3:
        return f"{rng.choice(p)} of {rng.choice(m)}"
    if r == 4:
        return f"the {rng.choice(n)} of the {rng.choice(T_PLACE)}"
    if r == 5:
        return f"{rng.choice(m)} and {rng.choice(m)}"
    if r == 6:
        return f"{rng.choice(T_NUMWORDS[1:])} {rng.choice(p)}"
    if r == 7:
        return f"{rng.choice(g)} the {rng.choice(n)}"
    if r == 8:
        return f"the {rng.choice(T_POSSESSORS)}'s {rng.choice(n)}"
    if r == 9:
        return f"{rng.choice(T_PREPS)} the {rng.choice(n)}"
    if r == 10:
        return f"{rng.choice(a)} {rng.choice(p)}"
    if r == 11:
        return f"the {rng.choice(p)}"
    if r == 12:
        return f"a {rng.choice(n)} for the {rng.choice(p)}"
    if r == 13:
        return f"{rng.choice(p)} and {rng.choice(p)}"
    if r == 14:
        return f"the last {rng.choice(n)}"
    if r == 15:
        return f"the {rng.choice(n)} of {rng.choice(m)}"
    if r == 16:
        return f"{rng.choice(p)} of the {rng.choice(a)} {rng.choice(T_PLACE)}"
    return f"{rng.choice(T_PREPS)} the {rng.choice(a)} {rng.choice(n)}"


def _long_phrase(rng: random.Random, target: int) -> str:
    """Longer title phrase (roughly 25-55 characters) from fixed grammar templates."""
    n, a, p, g = T_NOUNS, T_ADJS, T_PLURALS, T_GERUNDS_T
    pos = T_POSSESSORS
    forms = [
        lambda: f"the {rng.choice(a)} {rng.choice(n)} of the {rng.choice(a)} {rng.choice(T_PLACE)}",
        lambda: f"the {rng.choice(pos)}'s {rng.choice(n)} and the {rng.choice(a)} {rng.choice(n)}",
        lambda: f"a {rng.choice(n)} for the {rng.choice(a)} {rng.choice(p)} of the {rng.choice(T_PLACE)}",
        lambda: f"{rng.choice(g)} the {rng.choice(a)} {rng.choice(n)} of the {rng.choice(T_PLACE)}",
        lambda: f"the last {rng.choice(n)} of the {rng.choice(a)} {rng.choice(T_PLACE)}",
        lambda: f"{rng.choice(p)} of the {rng.choice(a)} {rng.choice(T_PLACE)} and the {rng.choice(a)} {rng.choice(n)}",
        lambda: f"the {rng.choice(n)} of the {rng.choice(pos)}'s {rng.choice(a)} {rng.choice(n)}",
        lambda: f"the {rng.choice(a)} {rng.choice(p)} of {rng.choice(T_MASS)} and {rng.choice(T_MASS)}",
    ]
    return rng.choice(forms)()


class TitlePool:
    """Phrases bucketed by length; draws without replacement within a bucket."""

    def __init__(self, rng: random.Random, maker, count: int) -> None:
        self.rng = rng
        self.buckets: dict[int, list[str]] = {}
        seen = set()
        for _ in range(count):
            text = title_case(maker(rng))
            if text in seen or text.lower() in TITLE_BLOCK:
                continue
            seen.add(text)
            self.buckets.setdefault(len(text), []).append(text)

    def take(self, length: int) -> str | None:
        bucket = self.buckets.get(length)
        if not bucket:
            return None
        return bucket.pop(self.rng.randrange(len(bucket)))


def _ordinal(n: int) -> str:
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def build_titles(length_of: dict[int, int], comma_rows: set[int], quote_rows: set[int], rng: random.Random) -> list[str]:
    """Titles of exact target length, built only from real words, numbers and punctuation."""
    n_rows = len(length_of)
    rows = list(range(n_rows))
    rng.shuffle(rows)
    titles: list[str | None] = [None] * n_rows
    used: Counter = Counter()

    def ok(t: str | None) -> bool:
        return t is not None and used[t] < 4 and t.lower() not in TITLE_BLOCK

    def put(i: int, t: str) -> None:
        titles[i] = t
        used[t] += 1

    # 1. Short titles (1-3 characters): numbers and short real words.
    shorts = {1: [str(d) for d in range(1, 10)], 2: [str(d) for d in range(10, 100)],
              3: [str(d) for d in range(100, 1000)] + ["Ash", "Fog", "Ice", "Oak", "Ivy", "Sky", "Sun", "War", "Ark", "Elm"]}
    for i in rows:
        L = length_of[i]
        if L <= 3:
            cand = [t for t in shorts[L] if used[t] == 0 and t.lower() not in TITLE_BLOCK]
            put(i, rng.choice(cand))

    # 2. Comma and quote titles.
    comma_makers = [
        lambda r: f"goodbye, {r.choice(T_ADJS)} {r.choice(T_NOUNS)}",
        lambda r: f"farewell, {r.choice(T_NOUNS)}",
        lambda r: f"{r.choice(T_PLURALS)}, {r.choice(T_PLURALS)} and {r.choice(T_PLURALS)}",
        lambda r: f"{r.choice(T_ADJS)}, {r.choice(T_ADJS)} {r.choice(T_PLURALS)}",
        lambda r: f"hello, {r.choice(T_NOUNS)}",
        lambda r: f"{r.choice(T_MASS)}, {r.choice(T_MASS)} and {r.choice(T_MASS)}",
        lambda r: f"{r.choice(T_MASS)}, {r.choice(T_MASS)} and the {r.choice(T_ADJS)} {r.choice(T_NOUNS)}",
        lambda r: f"goodbye, {r.choice(T_ADJS)} {r.choice(T_NOUNS)} of the {r.choice(T_NOUNS)}",
        lambda r: f"once upon a {r.choice(T_NOUNS)}, {r.choice(T_NOUNS)}",
    ]
    comma_pool = TitlePool(rng, lambda r: r.choice(comma_makers)(r), 60000)
    for i in sorted(comma_rows):
        t = comma_pool.take(length_of[i])
        if t is None:
            raise RuntimeError(f"comma title length {length_of[i]}")
        put(i, t)
    for i in sorted(quote_rows):
        L = length_of[i]
        for _ in range(20000):
            t = title_case(f'the "{rng.choice(T_ADJS)}" {rng.choice(T_NOUNS)}')
            t = t.replace('"' + t.split('"')[1] + '"', '"' + _sgl(t.split('"')[1]) + '"')
            if len(t) == L:
                break
        else:
            raise RuntimeError("quote title")
        put(i, t)

    free = [i for i in rows if titles[i] is None]
    # 3. Single-word titles: every eligible word used once.
    singles: dict[int, list[str]] = {}
    for w in sorted(set(T_SINGLE) | set(T_NOUNS) | set(T_PLURALS) | set(T_ADJS) | set(T_GERUNDS)):
        if len(w) >= 4 and w not in TITLE_BLOCK:
            singles.setdefault(len(w), []).append(_sgl(w))
    for v in singles.values():
        rng.shuffle(v)
    for i in free:
        bucket = singles.get(length_of[i])
        if bucket and (length_of[i] <= 6 or rng.random() < 0.62):
            put(i, bucket.pop())
    free = [i for i in rows if titles[i] is None]

    # 4. Digit titles (~530), colon titles (~1,100, the longest first), the rest plain phrases.
    plain = TitlePool(rng, lambda r: _phrase(r) if r.random() < 0.8 else _long_phrase(r, 60), 450000)
    digit_makers = [
        lambda r: f"{_phrase(r)} {r.randrange(2, 8)}",
        lambda r: f"{r.choice(T_NOUNS)} {r.randrange(10, 100)}",
        lambda r: f"{r.choice(['summer', 'winter', 'autumn', 'spring'])} of {r.randrange(1925, 2021)}",
        lambda r: f"{r.randrange(2, 60)} {r.choice(T_PLURALS)}",
        lambda r: f"the {_ordinal(r.randrange(2, 40))} {r.choice(T_NOUNS)}",
        lambda r: f"{r.choice(T_NOUNS)} {r.randrange(2, 8)}: {_phrase(r)}",
        lambda r: str(r.randrange(1920, 2030)),
        lambda r: f"{r.choice(['Ash', 'Fog', 'Ice', 'Oak', 'Ivy', 'Sky', 'Sun', 'War', 'Ark', 'Elm'])} {r.randrange(2, 10)}",
        lambda r: f"{_sgl(r.choice([w for w in T_SINGLE if len(w) <= 6]))} {r.randrange(2, 10)}",
    ]
    digit_pool = TitlePool(rng, lambda r: r.choice(digit_makers)(r), 150000)

    def colon_title(L: int) -> str | None:
        for _ in range(400):
            left_kind = rng.random()
            if L > 50:
                left = plain.take(rng.randrange(max(6, L - 46), min(42, L - 10)))
                if left is None:
                    continue
            elif left_kind < 0.45:
                left = _sgl(rng.choice(COLON_LEFT))
            elif left_kind < 0.6:
                left = title_case(_phrase(rng)) + " " + rng.choice(T_ROMAN)
            else:
                left = title_case(_phrase(rng))
            room = L - len(left) - 2
            if room < 3:
                continue
            if room <= 44:
                right = plain.take(room)
                if right is None:
                    continue
            else:
                right = None
                for _ in range(300):
                    cand = title_case(_long_phrase(rng, room))
                    if len(cand) == room:
                        right = cand
                        break
                if right is None:
                    continue
            t = f"{left}: {right[0].upper()}{right[1:]}"
            if ok(t):
                return t
        return None

    digit_rows = set(rng.sample([i for i in free if 6 <= length_of[i] <= 40], 520))
    long_rows = sorted((i for i in free if i not in digit_rows), key=lambda i: -length_of[i])
    colon_rows = set(long_rows[:300]) | set(rng.sample([i for i in long_rows[300:] if length_of[i] >= 12], 800))
    for i in free:
        L = length_of[i]
        t = None
        if i in digit_rows:
            t = digit_pool.take(L)
        elif i in colon_rows:
            t = colon_title(L)
        if t is None:
            t = plain.take(L)
            if t is None and L > 12:
                t = colon_title(L)
            if t is None:
                for _ in range(2000):
                    cand = title_case(_long_phrase(rng, L))
                    if len(cand) == L and ok(cand):
                        t = cand
                        break
        if t is None:
            t = digit_pool.take(L)
        if t is None:
            # last resort: repeat an existing title of this length (max 4 uses)
            same = sorted(x for x in used if len(x) == L and used[x] < 4)
            t = rng.choice(same) if same else None
        if t is None or not ok(t):
            raise RuntimeError(f"no title of length {L}")
        put(i, t)
    return titles  # type: ignore[return-value]


# --- Original titles in the film's own language (real words) ---
NATIVE = {
    "ja": (["夜", "海", "雨", "風", "花", "月", "夢", "影", "光", "春", "夏", "秋", "冬", "約束", "記憶", "秘密",
            "旅", "港", "家族", "桜", "物語", "少女", "少年", "嵐", "雪", "空", "星", "心", "道", "故郷", "明日", "最後の日"], "の", "と"),
    "ko": (["밤", "강", "집", "침묵", "폭풍", "여행", "국경", "겨울", "기억", "비밀", "그림자", "항구", "섬", "길",
            "약속", "바다", "사랑", "마음", "별", "꿈", "여름", "봄날", "가족", "내일"], "의 ", " 그리고 "),
    "zh": (["夜", "河", "家", "沉默", "风暴", "旅程", "边境", "冬天", "记忆", "秘密", "影子", "港口", "岛", "路",
            "承诺", "大海", "爱情", "心", "星", "梦", "江湖", "故乡", "少年", "明天", "春天"], "的", "与"),
    "ru": (["ночь", "река", "дом", "тишина", "буря", "путь", "граница", "зима", "память", "тайна", "тень", "порт",
            "остров", "дорога", "обещание", "огонь", "сердце", "брат", "сестра", "море", "город", "лето", "весна"], " и ", " и "),
    "uk": (["ніч", "річка", "дім", "тиша", "буря", "подорож", "кордон", "зима", "пам'ять", "таємниця", "тінь",
            "острів", "дорога", "обіцянка", "море", "серце", "літо", "весна"], " і ", " і "),
    "hi": (["रात", "नदी", "घर", "ख़ामोशी", "तूफ़ान", "सफ़र", "सरहद", "सर्दी", "याद", "राज़", "साया", "किनारा",
            "दिल", "आग", "वादा", "ज़िंदगी", "दोस्ती", "सपना", "बारिश", "मंज़िल"], " और ", " और "),
    "th": (["คืน", "แม่น้ำ", "บ้าน", "ความเงียบ", "พายุ", "การเดินทาง", "ฤดูหนาว", "ความทรงจำ", "ความลับ", "เงา",
            "ท่าเรือ", "เกาะ", "ถนน", "สัญญา", "ทะเล", "หัวใจ", "ดาว", "ความฝัน"], " และ ", " และ "),
    "ar": (["الليل", "النهر", "البيت", "الصمت", "العاصفة", "الرحلة", "الحدود", "الشتاء", "الذاكرة", "السر", "الظل",
            "الميناء", "الجزيرة", "الطريق", "الوعد", "البحر", "القلب", "الحلم"], " و", " و"),
    "fa": (["شب", "رودخانه", "خانه", "سکوت", "طوفان", "سفر", "مرز", "زمستان", "خاطره", "راز", "سایه", "بندر",
            "جزیره", "جاده", "دریا", "دل", "رویا", "باران"], " و ", " و "),
    "el": (["Νύχτα", "Ποτάμι", "Σπίτι", "Σιωπή", "Καταιγίδα", "Ταξίδι", "Σύνορα", "Χειμώνας", "Μνήμη", "Μυστικό",
            "Σκιά", "Λιμάνι", "Νησί", "Δρόμος", "Υπόσχεση", "Θάλασσα", "Καρδιά"], " και ", " και "),
    "te": (["రాత్రి", "నది", "ఇల్లు", "ప్రయాణం", "కల", "హృదయం", "సముద్రం", "వాన"], " మరియు ", " మరియు "),
    "kn": (["ರಾತ್ರಿ", "ನದಿ", "ಮನೆ", "ಪಯಣ", "ಕನಸು", "ಹೃದಯ", "ಸಮುದ್ರ", "ಮಳೆ"], " ಮತ್ತು ", " ಮತ್ತು "),
    "ta": (["இரவு", "நதி", "வீடு", "பயணம்", "கனவு", "இதயம்", "கடல்", "மழை"], " மற்றும் ", " மற்றும் "),
    "gu": (["રાત", "નદી", "ઘર", "સફર", "સપનું", "હૃદય", "દરિયો", "વરસાદ"], " અને ", " અને "),
    "km": (["យប់", "ទន្លេ", "ផ្ទះ", "ដំណើរ", "សុបិន", "បេះដូង", "សមុទ្រ", "ភ្លៀង"], " និង ", " និង "),
    "ka": (["ღამე", "მდინარე", "სახლი", "მოგზაურობა", "სიზმარი", "გული", "ზღვა", "წვიმა"], " და ", " და "),
    "kk": (["Түн", "Өзен", "Үй", "Сапар", "Арман", "Жүрек", "Теңіз", "Жаңбыр"], " және ", " және "),
    "mk": (["Ноќ", "Река", "Дом", "Патување", "Сон", "Срце", "Море", "Дожд"], " и ", " и "),
}
NATIVE["cn"] = NATIVE["zh"]


def _foreign_phrase(lang: str, rng: random.Random, avoid: set[str]) -> str:
    if lang in NATIVE:
        words, link, conj = NATIVE[lang]
    else:
        words, conj = FOREIGN[lang]
        link, conj = " " + conj + " ", " " + conj + " "
    pick = [w for w in words if w not in avoid]
    one = rng.choice(pick)
    avoid.add(one)
    r = rng.random()
    if r < 0.4:
        text = one
    else:
        two = rng.choice([w for w in pick if w != one])
        avoid.add(two)
        text = one + (link if r < 0.7 else conj) + two
    return text[:1].upper() + text[1:]


def original_title(lang: str, length: int, rng: random.Random) -> str:
    """A real-word title in `lang` (at most a title and two subtitles), close to `length`."""
    sep = "：" if lang in ("ja", "zh", "cn") else ": "
    best = None
    for _ in range(300):
        avoid: set[str] = set()
        parts = [_foreign_phrase(lang, rng, avoid)]
        while len(parts) < 3 and len(sep.join(parts)) < length - 3:
            parts.append(_foreign_phrase(lang, rng, avoid))
        text = sep.join(parts)
        if best is None or abs(len(text) - length) < abs(len(best) - length):
            best = text
        if len(best) == length:
            break
    return best  # type: ignore[return-value]


def latin_language(lang: str) -> str:
    """Latin-script languages without a lexicon borrow the closest one."""
    if lang in FOREIGN:
        return lang
    return {"nb": "no", "ca": "es", "eu": "es", "tl": "es", "is": "da", "fi": "sv", "et": "sv",
            "hu": "de", "cs": "pl", "bs": "pl", "tr": "de", "id": "nl", "vi": "fr"}.get(lang, "es")


# --- Prose: sentence templates over typed, curated slots ---
PLACES_SHORT = [p.split(" ", 1)[1] if p.startswith(("a ", "an ")) else p for p in PLACES]
RELATIVES = ["brother", "sister", "father", "mother", "daughter", "son", "uncle", "aunt", "cousin", "grandmother", "grandfather", "husband", "wife", "best friend", "business partner", "former mentor"]
LINES = [x for x in LINES if "," not in x]

S_PLAIN = [
    "{N} is a {adj} {role} in {place}.",
    "{N} works as a {role} in {place}.",
    "{n} has spent years trying to forget {event}.",
    "{n} sets out to {goal}.",
    "The search leads {o} to {place2}.",
    "{n} finds {obj} that should not exist.",
    "{Group} will stop at nothing to get it back.",
    "{n} soon realizes that {outcome}.",
    "Nobody in {place_s} wants to talk about {event}.",
    "The trail points straight to {group}.",
    "What begins as a simple favor turns into a fight for survival.",
    "{n} and {m} have until the end of the week to {goal}.",
    "{n} must decide how much {p} is willing to risk.",
    "Every new clue brings {o} closer to the truth about {event}.",
    "The answer may cost {o} everything {p} loves.",
    "{M} arrives with {obj} and a story nobody believes.",
    "{m} has reasons of {mps} own to help.",
    "{n} keeps {obj} hidden in a drawer at home.",
    "Old friends become suspects and strangers become allies.",
    "{n} starts to suspect that {m} knows more than {mp} admits.",
    "A chance meeting with {M} changes everything.",
    "{m} is the only person who remembers what happened that night.",
    "{n} returns to {place} for the first time in years.",
    "{n} takes the night train to {city2}.",
    "{m} grew up in {city} and never meant to come back.",
    "The two of them form an uneasy partnership.",
    "{n} learns that {group} has been watching {o} for months.",
    "Rumors about {event} spread quickly through {place_s}.",
    "{n} has one chance to {goal}.",
    "A letter from {ps} late {rel} sends {o} back to {place}.",
    "{m} wants nothing to do with the plan at first.",
    "Their friendship is tested when {event} brings old enemies back.",
    "{n} refuses to give up on {m}.",
    "The people of {place_s} have secrets of their own.",
    "{n} must also face the reason {p} left home in the first place.",
    "Meanwhile {m} uncovers a link between {event} and {group}.",
    "Nothing about {obj} is what it seems.",
    "The final confrontation takes place in {place2}.",
    "{n} discovers that {m} has been lying from the start.",
    "{n} has not spoken to {ps} {rel} since {event}.",
    "{ps_cap} {rel} has disappeared without a trace.",
    "{M} offers {o} a way out.",
    "{n} goes to {city2} to find answers.",
    "The plan depends on {obj} and a great deal of luck.",
    "{m} warns {o} that {group} never forgets a debt.",
    "{m} has other plans.",
    "{n} hides the truth from everyone at work.",
    "Neither of them trusts the police.",
    "{m} is hiding something about {event}.",
    "{n} spends the night going through old records.",
    "A stranger at the funeral knows {ps} name.",
    "{n} borrows a car and drives north.",
    "The town council wants the whole matter forgotten.",
    "{m} offers {o} a job that seems too good to be true.",
    "The money is gone and so is {m}.",
    "{n} tracks down a witness who saw everything.",
    "Old photographs reveal a connection nobody expected.",
    "{n} breaks into an office after midnight.",
    "Every door {n} knocks on leads to another lie.",
    "{m} finally tells the story of {event}.",
    "The police close the case too quickly.",
    "A storm cuts the town off from the rest of the world.",
    "{n} realizes {p} is being followed.",
    "Someone has been sending anonymous letters to the mayor.",
    "{n} and {m} argue about what to do next.",
    "The truth about {obj} changes everything {n} believed.",
    "Help comes from the last person {n} expected.",
    "{m} is arrested for a crime {mp} did not commit.",
    "{n} returns the favor years too late.",
    "A fire destroys the only evidence.",
    "{n} confronts {group} at last.",
    "The journey home is longer than {n} imagined.",
    "{m} leaves {city} with nothing but a suitcase.",
    "Their plan falls apart within hours.",
    "Then {m} vanishes.",
    "{n} is running out of time.",
    "Nobody believes {o}.",
    "{n} cannot let go.",
]
S_COMMA = [
    "{Time}, {N}, a {adj} {role}, comes home to {place}.",
    "With help from {M}, {n} sets out to {goal}.",
    "But as {event} draws closer, {outcome}.",
    "Haunted by {event}, {n} agrees to {goal}.",
    "Along the way, {n} meets {M}, a {role2} with secrets of {mps} own.",
    "The deeper {n} digs, the more dangerous the questions become.",
    "By the time {n} understands the truth, it may already be too late.",
    "When {event} shakes {place}, {n} is forced to {goal}.",
    "Desperate and alone, {n} turns to {group} for help.",
    "Torn between loyalty and love, {n} must choose a side.",
    "{m}, a {role2}, offers to help, but {mp} has plans of {mps} own.",
    "As the days pass, {n} and {m} grow closer.",
    "In {city}, {n} tracks down {ps} estranged {rel}.",
    "Years later, {n} still wonders what really happened.",
    "Soon, {outcome}.",
    "Now, {n} wants answers.",
    "For {n}, it is personal.",
    "Slowly, {n} begins to remember.",
    "Still, {m} refuses to leave.",
]
S_QUOTE = [
    '{n} has only one rule: "{line}"',
    'When they finally meet {m} says only this: "{line}"',
    '"{line}" These are the last words {n} hears from {m}.',
    'The note in {ps} pocket reads "{line}"',
    '{m} repeats the warning every night: "{line}"',
    'The message on the wall is simple: "{line}"',
]
TG_NOUNS = _w("""storm truth past river night road sea fire winter shadow silence secret heart dark
harbor border mountain desert tide ghost echo dawn flame war city game hunt verdict ransom flood wolf
forest island valley tower bridge frontier current wind ocean moon thunder smoke curse prophecy""")
TG_PEOPLE = _w("soldiers sailors strangers outlaws hunters brothers sisters ghosts wolves thieves daughters sons")
TAG_PLAIN = [
    "Some {abp} never stay buried.", "Every {ab} has a price.", "Fear the {tg}.", "Trust no one.",
    "No way back.", "Nobody leaves alone.", "The {ta} {tg} is only the beginning.", "Home is where the heart is not.",
    "One {tg}. One chance.", "{Nw} days. {Nw} strangers. One {tg}.", "This {season} the {tpp} come home.",
    "Trust no {rw}.", "Remember the {tg}.", "The {tg} remembers.", "Not every {tg} wants to be found.",
    "Some {abp} are worth dying for.", "The past is never really over.", "Everyone has a breaking point.",
    "Love is the most dangerous {ab}.", "The {tg} is coming.", "Beware the {ta} {tg}.", "Revenge has a long memory.",
    "Every {rw} has a secret.", "The {tpp} are waiting.", "Nothing stays hidden forever.", "The truth will cost them everything.",
    "Follow the {tg}.", "Welcome to {city_t}.", "Some {abp} should never be kept.", "The last {tg} is the hardest.",
    "One {rw} against the world.", "The {ta} {tpp} never sleep.", "All roads lead to {city_t}.", "Hope is a dangerous thing.",
    "Who will save the {tn}?", "What would you risk for the truth?", "Every {ab} leaves a mark.",
]
ABS_BIG = _w("""courage betrayal redemption revenge ambition loyalty desire freedom justice mercy hope fear
grief guilt honor glory power greed pride faith survival destiny fate silence love truth vengeance memory
obsession temptation sacrifice envy rage chaos danger exile wonder longing madness doubt trust shame
patience jealousy kindness innocence defiance courage forgiveness ruin luck sorrow fury""")
ABS_BIG = sorted(set(ABS_BIG))
TAG_ABS = [
    "{Abs} has a price.", "{Abs} never sleeps.", "{Abs} is a choice.", "{Abs} comes home.", "Some call it {abs}.",
    "{Abs} was only the beginning.", "In the end there is only {abs}.", "{Abs} is not enough.",
    "Nothing is stronger than {abs}.", "{Abs} wears many faces.", "Where {abs} ends {abs2} begins.",
    "{Abs} has a long memory.", "{Abs} is the last thing to die.", "Choose {abs}.", "They came for {abs}.",
]
TAG_SHORT = [
    "{Abs}. {Abs2}. {Abs3}.", "No {abs}. No {abs2}.", "{Abs} or {abs2}?", "{Abs} at any cost.",
    "First {abs}. Then {abs2}.", "Welcome to {city_t}.", "The {tg} awaits.", "{Nw} {tpp}. One {tg}.",
    "Never trust a {rw}.", "Fear the {ta} {tg}.", "Escape from {city_t}.", "{Abs} has a new name.",
    "Beyond {abs}. Beyond {abs2}.", "Born of {abs}.", "Every {rw} pays.",
]
TAG_PLAIN = TAG_PLAIN + TAG_ABS + TAG_SHORT
TAG_COMMA = [
    "In {city_t}, {abs} has a price.", "Once a {rw}, always a {rw}.", "{Abs}, {abs2} and one last chance.",
    "Some say {abs}, others say {abs2}.", "First came {abs}, then came {abs2}.", "In {city_t}, every {rw} has a secret.",
    "In {city_t}, nothing stays hidden.", "Run, hide, survive.", "Once broken, some {abp} stay broken.",
    "Sometimes, the {tg} finds you.",
    "This {season}, the {tpp} come home.", "If you see the {tg}, run.", "Some {abp}, once made, cannot be undone.",
    "Be careful what you wish for, {rw}.",
]
TAG_QUOTE = ['"{line}"', 'Remember: "{line}"', 'They had one rule: "{line}"']
ABSTRACT = _w("secret debt promise truth lie memory crime choice dream love grief revenge loyalty ambition")
ABSTRACT_PL = _w("secrets debts promises truths lies memories crimes dreams choices sins wounds rumors")
ROLE_WORDS = _w("""stranger neighbor partner witness soldier sailor hunter thief spy doctor pilot detective lawyer
teacher brother sister banker preacher sheriff gambler driver dancer singer painter priest captain guard nurse
tailor miner farmer boxer pianist widow neighbor smuggler banker rancher""")
ROLE_WORDS = sorted(set(ROLE_WORDS))

NUM_WORDS_CAP = ["Two", "Three", "Four", "Five", "Six", "Seven", "Ten", "Twelve"]


AN_RE = re.compile(r"\b(?<![A-Za-z])(A|a) (?=[aeioAEIO]|u(?!ni))")


def city_name(raw: str) -> str:
    return " ".join(w if w in ("de", "of") else w[:1].upper() + w[1:] for w in raw.split(" "))


def _opens_with_name(template: str) -> bool:
    """True when the first person slot of a template names someone (no dangling pronoun)."""
    slots = re.findall(r"\{(\w+)\}", template)
    people = [x for x in slots if x in ("N", "n", "M", "m", "p", "o", "ps", "ps_cap", "mp", "mps", "mo")]
    if template.startswith(("The two", "Their ", "Neither of them", "The money is gone")):
        return False
    return bool(people) and people[0] in ("N", "n", "M")


def _article(phrase: str) -> str:
    return ("an " if phrase[:1].lower() in "aeiou" else "a ") + phrase


ROLES_F = {"grieving widow", "single mother", "farm widow", "diner waitress"}
ROLES_M = {"single father"}


def make_cast(rng: random.Random) -> dict[str, str]:
    """Two characters with consistent pronouns, roles and one storyline."""
    def person() -> tuple[str, str, str, str, str, str]:
        if rng.random() < 0.5:
            first, subj, obj, pos, banned = rng.choice(FIRST_F), "she", "her", "her", ROLES_M
        else:
            first, subj, obj, pos, banned = rng.choice(FIRST_M), "he", "him", "his", ROLES_F
        role = rng.choice([r for r in ROLES if r not in banned])
        return first, f"{first} {rng.choice(LAST_NAMES)}", subj, obj, pos, role

    n, full, p, o, ps, role = person()
    m, mfull, mp, mo, mps, role2 = person()
    while m == n or role2 == role:
        m, mfull, mp, mo, mps, role2 = person()
    return {"n": n, "N": full, "p": p, "o": o, "ps": ps, "ps_cap": ps.capitalize(),
            "m": m, "M": mfull, "mp": mp, "mo": mo, "mps": mps, "role": role, "role2": role2,
            "adj": rng.choice(ROLE_ADJS), "place": rng.choice(PLACES), "event": rng.choice(EVENTS),
            "goal": rng.choice(GOALS), "obj": rng.choice(OBJECTS), "group": rng.choice(GROUPS),
            "rel": rng.choice(RELATIVES), "city": city_name(rng.choice(CITIES)[0])}


def render(template: str, cast: dict[str, str], rng: random.Random) -> str:
    slots = dict(cast)
    slots.update(
        place2=rng.choice(PLACES), place_s="the " + rng.choice(PLACES_SHORT), Group=cast["group"].capitalize(),
        outcome=rng.choice(OUTCOMES), Time=rng.choice(TIMES), line=rng.choice(LINES),
        city2=city_name(rng.choice(CITIES)[0]),
    )
    text = AN_RE.sub(lambda m: m.group(1) + "n ", template.format(**slots))
    return text[0].upper() + text[1:]


def _abs_slots(rng: random.Random) -> dict[str, str]:
    a, b, c = rng.sample(ABS_BIG, 3)
    return {"abs": a, "Abs": _sgl(a), "abs2": b, "Abs2": _sgl(b), "Abs3": _sgl(c)}


def render_tag(template: str, rng: random.Random) -> str:
    ta = rng.choice(T_ADJS)
    text = template.format(
        abp=rng.choice(ABSTRACT_PL), ab=rng.choice(ABSTRACT), tn=rng.choice(T_NOUNS), ta=ta, Ta=_sgl(ta),
        tp=rng.choice(T_PLURALS), tg=rng.choice(TG_NOUNS), tpp=rng.choice(TG_PEOPLE), Nw=rng.choice(NUM_WORDS_CAP), season=rng.choice(["summer", "winter", "autumn", "spring"]),
        rw=rng.choice(ROLE_WORDS), **_abs_slots(rng), city_t=city_name(rng.choice(CITIES)[0]), line=rng.choice(LINES),
    )
    return text[0].upper() + text[1:]


def compose(target: int, rng: random.Random, comma: bool, quote: bool, newline: bool, cap: bool) -> str:
    """Retry `_compose` a few times until the length is exact; keep the closest."""
    best = None
    for _ in range(40):
        try:
            text = _compose(target, rng, comma, quote, newline, cap)
        except RuntimeError:
            continue
        if len(text) == target:
            return text
        if best is None or abs(len(text) - target) < abs(len(best) - target):
            best = text
    if best is None:
        raise RuntimeError(f"compose failed for {target}")
    return best


def _compose(target: int, rng: random.Random, comma: bool, quote: bool, newline: bool, cap: bool) -> str:
    """English prose of (ideally) exactly `target` characters, built from whole sentences.

    comma/quote/newline say whether the text must contain those characters (and,
    when False, guarantee it does not). `cap` marks plots clipped at 3,000
    characters: the text is cut at a word boundary exactly at `target`.
    Quotes only wrap a whole line of dialogue; newlines only separate sentences.
    """
    cast = make_cast(rng)
    pieces: list[str] = []
    seps: list[str] = []
    used: set[str] = set()
    intro = {S_PLAIN[0], S_PLAIN[1], S_COMMA[0]}
    extra = [t for t in S_PLAIN + (S_COMMA if comma else []) if t not in intro]
    since_break = [0]

    def draw(pool, max_len=None, exact=None, tries=80):
        best = None
        if not pieces:
            pool = [t for t in pool if _opens_with_name(t)]
        for _ in range(tries):
            tpl = rng.choice(pool)
            if tpl in used and len(used) < len(extra) - 4:
                continue
            if pieces and tpl in intro:
                continue
            s = render(tpl, cast, rng)
            if exact is not None:
                if len(s) == exact:
                    used.add(tpl)
                    return s
                if len(s) < exact and (best is None or len(s) > len(best)):
                    best = s
                continue
            if max_len is None or len(s) <= max_len:
                used.add(tpl)
                return s
        return best

    def room() -> int:
        return target - sum(len(p) for p in pieces) - len(seps) - (1 if pieces else 0)

    def add(s: str) -> None:
        if pieces:
            brk = newline and (len(pieces) == 1 or (since_break[0] >= 3 and rng.random() < 0.45))
            seps.append("\n" if brk else " ")
            since_break[0] = 0 if brk else since_break[0] + 1
        pieces.append(s)

    def joined() -> str:
        return "".join(p + s for p, s in zip(pieces, seps + [""]))

    needed = ([S_QUOTE] if quote else []) + ([S_COMMA] if comma else [])
    if target >= 160:
        add(draw(S_PLAIN[:2], tries=10))
    for pool in needed:
        if cap or room() > 180:
            s = draw(pool)
        elif room() >= 70:
            s = draw(pool, max_len=room() - 25, tries=800)
        else:
            s = draw(pool, exact=room(), tries=1500)
        if s is None:
            raise RuntimeError(f"compose: nothing fits {target}")
        add(s)
    if cap:
        while room() > -40:
            add(draw(extra) or render(rng.choice(S_PLAIN), cast, rng))
        for _ in range(6000):
            text = joined()
            if len(text) <= target:
                add(render(rng.choice(extra), cast, rng))
                continue
            if text[target - 1].isalpha() and text[target] in " ,.\n":
                return text[:target]
            pieces[-1] = render(rng.choice(extra), cast, rng)
        raise RuntimeError("compose: cannot clip at a word boundary")
    while room() > 150:
        s = draw(extra, max_len=room() - 45)
        if s is None:
            break
        add(s)
    for _ in range(4):
        if pieces and room() < 12:
            break
        s = draw(extra, exact=room(), tries=1500)
        if s is None:
            break
        add(s)
    if newline and len(pieces) < 2:
        raise RuntimeError(f"compose: newline needs two sentences ({target})")
    return joined()


def compose_tagline(target: int, rng: random.Random, comma: bool, quote: bool) -> str:
    """Tagline of (ideally) exactly `target` characters made of short whole sentences."""
    if target == 3:
        return "Go."
    first = TAG_QUOTE if quote else TAG_COMMA if comma else TAG_PLAIN
    best = None
    for _ in range(400):
        tpls = [rng.choice(first)]
        parts = [render_tag(tpls[0], rng)]
        size = len(parts[0])
        if size > target:
            if best is None or size - target < abs(len(best) - target):
                best = parts[0]
            continue
        # optionally split a medium tagline into two or more sentences
        while size < target:
            room = target - size - 1
            if room < 8:
                break
            fit = None
            for _ in range(60):
                tpl = rng.choice(TAG_PLAIN)
                if tpl in tpls:
                    continue
                cand = render_tag(tpl, rng)
                if len(cand) == room or (len(cand) <= room - 9 and rng.random() < 0.5):
                    fit = (tpl, cand)
                    if len(cand) == room:
                        break
            if fit is None:
                break
            tpls.append(fit[0])
            parts.append(fit[1])
            size += len(fit[1]) + 1
        text = " ".join(parts)
        if len(text) == target:
            return text
        if best is None or abs(len(text) - target) < abs(len(best) - target):
            best = text
    if best is None:
        raise RuntimeError(f"tagline {target}")
    return best


PROSE_BAD = re.compile(r"[A-Za-z][\"\n][A-Za-z]")


def make_url(length: int, https: bool, salt: int) -> str:
    """URL of exact `length` on a reserved `.example` domain.

    Shortest possible: `http://a.example` (16). `https://a.example` needs 17, so
    when length == 16 we always use http regardless of the https flag.
    """
    if length < 16:
        raise ValueError(f"homepage length {length} < 16")
    if length == 16:
        https = False
    prefix = "https://" if https else "http://"
    suffix = ".example"
    alpha = "abcdefghijklmnopqrstuvwxyz0123456789"
    room = length - len(prefix) - len(suffix)  # label + optional path
    if room < 1:
        raise ValueError(f"no room for label at length {length} https={https}")
    # Prefer a path when there is enough space.
    path = ""
    label_len = room
    if room >= 4 and (salt % 5 != 0):
        # leave at least 1 char for label
        path_budget = min(room - 1, 1 + (salt * 7) % max(1, room // 2))
        if path_budget >= 2:
            path = "/" + "".join(alpha[(salt + 3 + i * 17) % 36] for i in range(path_budget - 1))
            label_len = room - len(path)
    label = "".join(alpha[(salt + i * 13) % 36] for i in range(label_len))
    if not label[0].isalpha():
        label = "x" + label[1:]
    url = prefix + label + suffix + path
    if len(url) != length:
        # Adjust label length to compensate.
        delta = length - len(url)
        if delta > 0:
            label = label + "".join(alpha[(salt + 99 + i) % 36] for i in range(delta))
        elif delta < 0:
            if len(label) > -delta:
                label = label[:delta]
            else:
                path = ""
                label_len = length - len(prefix) - len(suffix)
                label = "".join(alpha[(salt + i * 13) % 36] for i in range(max(1, label_len)))
                if not label[0].isalpha():
                    label = "x" + label[1:]
        url = prefix + label + suffix + path
    if len(url) != length:
        # Final hard trim/pad on label only
        core_len = length - len(prefix) - len(suffix)
        if core_len < 1:
            raise RuntimeError("url impossible")
        label = (label + "x" * core_len)[:core_len]
        if not label[0].isalpha():
            label = "a" + label[1:]
        url = prefix + label + suffix
        if len(url) < length:
            url = url + ("/" + "x" * (length - len(url) - 1))
        url = url[:length]
    if len(url) != length or ".example" not in url:
        raise RuntimeError(f"make_url failed {length} -> {len(url)} {url!r}")
    return url


KW_ADJ_PERSON = _w("young old teenage female male former retired corrupt wealthy dying famous local foreign rogue missing dead elderly lonely")
KW_ADJ_PLACE = _w("abandoned haunted hidden secret ancient remote burning flooded isolated")
KW_ADJ_OBJECT = _w("stolen lost hidden ancient cursed broken fake mysterious secret forbidden old missing")
KW_ADJ_ANIMAL = _w("giant wild talking killer mutant dead lost stray")
KW_ADJ_EVENT = _w("sudden violent secret failed deadly illegal forbidden mysterious public botched staged unexpected")
KW_FIXED = [
    "small town", "coming of age", "road trip", "found footage", "time travel", "haunted house", "serial killer",
    "best friend", "first love", "single mother", "single father", "high school", "summer camp", "heist",
    "revenge", "family relationships", "father son relationship", "mother daughter relationship", "sibling rivalry",
    "world war ii", "cold war", "great depression", "prohibition era", "civil rights", "space travel",
    "alien invasion", "post apocalyptic", "dystopia", "biography", "sports", "survival", "friendship",
    "dark comedy", "female protagonist", "male friendship", "unrequited love", "love triangle", "fish out of water",
]


def _person_names(n: int) -> list[str]:
    """Plausible human names: real given names and surnames combined at random."""
    rng = rng_for("person-names")
    n2, n3, n1 = int(n * 0.89), int(n * 0.10), int(n * 0.005)
    n4 = n - n2 - n3 - n1
    shapes = [2] * n2 + [3] * n3 + [1] * n1 + [4] * n4
    rng.shuffle(shapes)
    accent = set(rng.sample(range(n), int(n * 0.05)))
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < n:
        k = len(names)
        shape = shapes[k]
        firsts = FIRST_F if rng.random() < 0.5 else FIRST_M
        if k in accent:
            use_first = rng.random() < 0.4
            f1 = rng.choice(FIRST_DIA) if use_first else rng.choice(firsts)
            last = rng.choice(LAST_DIA) if not use_first else rng.choice(LAST_NAMES)
        else:
            f1, last = rng.choice(firsts), rng.choice(LAST_NAMES)
        if shape == 1:
            cand = last if rng.random() < 0.5 else f1
        elif shape == 2:
            cand = f"{f1} {last}"
        elif shape == 3:
            if rng.random() < 0.6:
                cand = f"{f1} {rng.choice(firsts)} {last}"
            else:
                cand = f"{f1} {rng.choice(LAST_NAMES)} {last}"
        else:
            cand = f"{f1} {rng.choice(firsts)} {rng.choice(LAST_NAMES)} {last}"
        words = cand.split(" ")
        if len(set(words)) != len(words):
            continue
        if (k in accent) == cand.isascii():
            continue
        key = cand.lower()
        if key in seen or key in PERSON_BLOCK:
            continue
        seen.add(key)
        names.append(cand)
    return names


def _company_names(n: int = 8061) -> list[str]:
    rng = rng_for("company-names")
    names: list[str] = [""] * n
    seen: set[str] = set()
    # 36 stems with an intentional variant (stem / stem Pictures or stem Ltd.).
    stems = rng.sample(COMPANY_STEMS, 36)
    for i, stem in enumerate(stems):
        names[i] = stem
        names[36 + i] = stem + (" Pictures" if i < 18 else " Ltd.")
        seen.update({names[i].lower(), names[36 + i].lower()})
    non_ascii = int(n * 0.03)
    foreign_rows = set(rng.sample(range(72, n), non_ascii))
    makers = [
        lambda: f"{rng.choice(COMPANY_STEMS)} {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{rng.choice(LAST_NAMES)} {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{rng.choice(LAST_NAMES)} & {rng.choice(LAST_NAMES)} {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{rng.choice(LAST_NAMES)} Brothers {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{_sgl(rng.choice(T_ADJS))} {_sgl(rng.choice(T_NOUNS))} {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{_sgl(rng.choice(COLON_LEFT))} {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{city_name(rng.choice(CITIES)[0])} {rng.choice(['Film Company', 'Pictures', 'Film Fund', 'Film Society', 'Studios'])}",
    ]
    foreign_makers = [
        lambda: (lambda pre, words: f"{pre} {rng.choice(words)}")(*rng.choice(COMPANY_FOREIGN)),
        lambda: f"{rng.choice(LAST_DIA)} {rng.choice(COMPANY_SUFFIX)}",
        lambda: f"{rng.choice(LAST_DIA)} & {rng.choice(LAST_DIA)}",
    ]
    i = 72
    while i < n:
        cand = rng.choice(foreign_makers)() if i in foreign_rows else rng.choice(makers)()
        if (i in foreign_rows) == cand.isascii():
            continue
        if cand.lower() in seen or cand.lower() in REAL_COMPANY_BLOCK:
            continue
        seen.add(cand.lower())
        names[i] = cand
        i += 1
    # 26 names with a legal-form comma ("Northgate Films, Inc.").
    idxs = [j for j in range(200, n) if names[j].isascii()]
    rng.shuffle(idxs)
    for j in idxs[:26]:
        names[j] = names[j] + rng.choice([", Inc.", ", LLC", ", Ltd."])
    if len(set(names)) != n:
        raise RuntimeError("company names collide")
    return names


def _keyword_names(n: int = 11762) -> list[str]:
    """Lower-case keyword phrases; 57 % multi-word, 157 with a comma, 18 shared names."""
    rng = rng_for("keyword-names")
    multi = [
        lambda: f"{rng.choice(KW_ADJ_PERSON)} {rng.choice(KW_PERSON)}",
        lambda: f"{rng.choice(KW_ADJ_PLACE)} {rng.choice(KW_PLACE)}",
        lambda: f"{rng.choice(KW_ADJ_OBJECT)} {rng.choice(KW_OBJECT)}",
        lambda: f"{rng.choice(KW_ADJ_ANIMAL)} {rng.choice(KW_ANIMAL)}",
        lambda: f"{rng.choice(KW_EVENT)} {rng.choice(['investigation', 'aftermath', 'survivor', 'cover up', 'witness', 'plot'])}",
        lambda: "{} {} relationship".format(*rng.sample(["father", "mother", "son", "daughter", "brother", "sister", "husband", "wife", "grandfather", "grandmother", "uncle", "nephew", "aunt", "niece"], 2)),
        lambda: f"{rng.choice(KW_ADJ_EVENT)} {rng.choice(KW_EVENT)}",
        lambda: f"based on {rng.choice(KEY_SOURCES)}",
        lambda: f"death of {rng.choice(['father', 'mother', 'brother', 'sister', 'son', 'daughter', 'wife', 'husband', 'friend', 'mentor'])}",
        lambda: rng.choice(KW_FIXED),
        lambda: rng.choice([c for c, _ in CITIES if " " in c]),
    ]
    singles = [w for w in KW_SINGLE]
    rng.shuffle(singles)
    single_extra = [f"{d}s" for d in range(1900, 2030, 10)] + [c for c, _ in CITIES if " " not in c]
    names: list[str] = []
    seen: set[str] = set()
    comma_rows = set(rng.sample(range(50, n), 157 + 18))
    comma_rows = set(sorted(j for j in comma_rows if not 1000 <= j < 1018)[:157])
    cities = CITIES[:]
    rng.shuffle(cities)
    p_multi = (0.57 * n - 157) / (n - 157)
    shape_multi = [rng.random() < p_multi for _ in range(n)]
    while len(names) < n:
        k = len(names)
        if k in comma_rows:
            city, region = cities.pop()
            cand = f"{city}, {region}"
        elif shape_multi[k]:
            cand = rng.choice(multi)()
        else:
            cand = singles.pop() if singles else rng.choice(single_extra)
        if cand in seen or (k not in comma_rows and "," in cand):
            continue
        seen.add(cand)
        names.append(cand)
    for i in range(18):
        names[1000 + i] = names[i]
    counts = Counter(names)
    if sum(1 for v in counts.values() if v == 2) != 18 or any(v > 2 for v in counts.values()):
        raise RuntimeError("keyword name defects")
    return names


def _collection_names(n: int = 1039) -> list[str]:
    rng = rng_for("collection-names")
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < n:
        r = rng.random()
        if r < 0.6:
            stem = _sgl(rng.choice(COLON_LEFT))
        elif r < 0.85:
            stem = title_case(f"the {rng.choice(T_NOUNS)}")
        else:
            stem = title_case(f"{rng.choice(T_ADJS)} {rng.choice(TG_NOUNS)}")
        if rng.random() < 0.82:
            cand = stem + " Collection"
        else:
            cand = stem + " " + rng.choice(["Trilogy", "Saga", "Chronicles", "Anthology", "Series"])
        if cand.lower() in seen:
            continue
        seen.add(cand.lower())
        names.append(cand)
    names[1] = names[0]
    return names


def fix_keyword_name_clashes(keyword_of: list[list[int]], keyword_name: list[str]) -> None:
    """Ensure no movie holds both keyword_ids that share a name. Mutates keyword_of in place; preserves degrees."""
    # pairs of entity indices with the same name
    by_name: dict[str, list[int]] = defaultdict(list)
    for i, name in enumerate(keyword_name):
        by_name[name].append(i)
    pairs = [tuple(sorted(v)) for v in by_name.values() if len(v) == 2]
    if len(pairs) != 18:
        raise RuntimeError(f"expected 18 name pairs, got {len(pairs)}")
    pair_of = {}
    for a, b in pairs:
        pair_of[a] = b
        pair_of[b] = a

    def name_set(bucket):
        return {keyword_name[e] for e in bucket}

    for mi, bucket in enumerate(keyword_of):
        present = set(bucket)
        conflicts = [a for a, b in pairs if a in present and b in present]
        for a in conflicts:
            b = pair_of[a]
            # drop b from this movie; swap with some other movie that has a free slot for b's name
            if b not in present:
                continue
            # find donor movie that has an entity we can swap: donor has x not in mi, and mi's b name not in donor
            swapped = False
            for mj, other in enumerate(keyword_of):
                if mj == mi:
                    continue
                for pos, x in enumerate(other):
                    if x == a or x == b:
                        continue
                    if x in present:
                        continue
                    if keyword_name[x] in name_set(bucket) or keyword_name[b] in name_set(other):
                        continue
                    # also avoid creating a pair conflict on mj
                    mate = pair_of.get(b)
                    if mate is not None and mate in other:
                        continue
                    mate_x = pair_of.get(x)
                    if mate_x is not None and mate_x in bucket:
                        continue
                    # swap b in mi with x in mj
                    bi = bucket.index(b)
                    bucket[bi] = x
                    other[pos] = b
                    present = set(bucket)
                    swapped = True
                    break
                if swapped:
                    break
            if not swapped:
                # last resort: drop b and pick any unused entity globally that doesn't clash — but degree must hold
                raise RuntimeError(f"cannot resolve keyword clash on movie {mi}")
    # verify
    for mi, bucket in enumerate(keyword_of):
        names = [keyword_name[e] for e in bucket]
        if len(names) != len(set(names)):
            raise RuntimeError(f"duplicate keyword name remains in movie {mi}")




FILE_ORDER = [
    "movie_status", "content_rating", "original_language", "enrichment_field",
    "genre", "keyword", "person", "production_company", "production_country",
    "spoken_language", "collection", "movie", "movie_collection", "movie_genre",
    "movie_keyword", "movie_cast", "movie_production_company",
    "movie_production_country", "movie_spoken_language", "movie_enrichment",
]
HEADERS = {
    "movie_status": ["status_code"],
    "content_rating": ["rating_code"],
    "original_language": ["language_code", "description"],
    "enrichment_field": ["field_name"],
    "genre": ["genre_id", "name"],
    "keyword": ["keyword_id", "name"],
    "person": ["person_id", "name"],
    "production_company": ["company_id", "name"],
    "production_country": ["country_id", "name"],
    "spoken_language": ["spoken_language_id", "name"],
    "collection": ["collection_id", "name"],
    "movie": [
        "movie_id", "imdb_id", "title", "original_title", "original_language_code",
        "overview", "plot", "tagline", "status_code", "rating_code", "release_date",
        "runtime_minutes", "budget_usd", "revenue_usd", "popularity", "user_score",
        "vote_average", "vote_count", "adult", "video", "homepage", "poster_path",
        "backdrop_path",
    ],
    "movie_collection": [
        "movie_id", "collection_id", "observed_poster_path", "observed_backdrop_path",
    ],
    "movie_genre": ["movie_id", "genre_id", "source_position"],
    "movie_keyword": ["movie_id", "keyword_id", "source_position"],
    "movie_cast": ["movie_id", "person_id", "billing_order"],
    "movie_production_company": ["movie_id", "company_id", "source_position"],
    "movie_production_country": ["movie_id", "country_id", "source_position"],
    "movie_spoken_language": ["movie_id", "spoken_language_id", "source_position"],
    "movie_enrichment": ["movie_id", "field_name", "code"],
}
PATH_RE = re.compile(r"^/[A-Za-z0-9]{27}\.jpg$")
IMDB_RE = re.compile(r"^tt[0-9]{7,8}$")
FX_RE = re.compile(r"^wikipedia_infobox_fx:([A-Z]{3}):(\d{4})$")


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def rng_for(name: str) -> random.Random:
    h = SEED
    for ch in name:
        h = (h * 1315423911 + ord(ch)) & 0xFFFFFFFF
    return random.Random(h)


def percentile(sorted_vals: list[float], p: float) -> float:
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    h = (n - 1) * (p / 100.0)
    lo = int(h)
    hi = min(lo + 1, n - 1)
    frac = h - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def near(actual: float, expected: float, tol: float = 0.03) -> bool:
    if expected == 0:
        return actual == 0
    return abs(actual - expected) <= abs(expected) * tol + 1e-9


def encode(i: int, alphabet: str) -> str:
    base = len(alphabet)
    chars: list[str] = []
    n = i
    while True:
        chars.append(alphabet[n % base])
        n //= base
        if n == 0:
            break
    return "".join(reversed(chars))


def path_from(n: int) -> str:
    chars = []
    x = n
    for _ in range(27):
        chars.append(ALPH62[x % 62])
        x //= 62
    return "/" + "".join(reversed(chars)) + ".jpg"


def anchored_ints(n: int, vmin: int, vmed: int, vp95: int, vmax: int) -> list[int]:
    h50 = (n - 1) * 0.5
    h95 = (n - 1) * 0.95
    i50_lo = int(h50)
    i50_hi = i50_lo if h50 == i50_lo else i50_lo + 1
    i95_lo = int(h95)
    i95_hi = i95_lo if abs(h95 - i95_lo) < 1e-9 else min(n - 1, i95_lo + 1)
    anchors = [(0, vmin), (i50_lo, vmed)]
    if i50_hi != i50_lo:
        anchors.append((i50_hi, vmed))
    if anchors[-1][0] != i95_lo:
        anchors.append((i95_lo, vp95))
    else:
        anchors[-1] = (i95_lo, vp95)
    if i95_hi != anchors[-1][0]:
        anchors.append((i95_hi, vp95))
    if anchors[-1][0] != n - 1:
        anchors.append((n - 1, vmax))
    else:
        anchors[-1] = (n - 1, vmax)
    out = [0] * n
    for (i0, v0), (i1, v1) in zip(anchors, anchors[1:]):
        out[i0] = v0
        span = i1 - i0
        for k in range(1, span):
            out[i0 + k] = v0 + (v1 - v0) * k // span
        out[i1] = v1
    for i in range(1, n):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out




def homepage_lengths(n: int = 5095) -> list[int]:
    """Homepage lengths: min 16, median 38, p95 66, max 267; few at the minimum
    so `.example` URLs can stay unique (≥98 %)."""
    i50 = (n - 1) // 2
    i95 = int(0.95 * (n - 1))
    arr = [0] * n
    # 20 at min 16, then jump to 18 so room>=3 for unique labels
    for i in range(20):
        arr[i] = 16
    for i in range(20, i50 + 1):
        t = (i - 20) / max(1, i50 - 20)
        arr[i] = 18 + int(round((38 - 18) * t))
    arr[i50] = 38
    for i in range(i50 + 1, i95 + 1):
        t = (i - i50) / max(1, i95 - i50)
        arr[i] = 38 + int(round((66 - 38) * t))
    arr[i95] = 66
    for i in range(i95 + 1, n):
        t = (i - i95) / max(1, (n - 1) - i95)
        arr[i] = 66 + int(round((267 - 66) * t))
    arr[0] = 16
    arr[i50] = 38
    arr[i95] = 66
    arr[-1] = 267
    # soft non-decreasing without collapsing the floor
    for i in range(21, n):
        if arr[i] < arr[i - 1]:
            arr[i] = arr[i - 1]
    arr[i50] = 38
    arr[i95] = 66
    arr[-1] = 267
    return arr

def title_lengths() -> list[int]:
    """Title lengths: min 1, median 14, p95 37, max 86; at most ~70 of length 1..3."""
    n = N_MOVIES
    i50 = (n - 1) // 2
    i95 = int(0.95 * (n - 1))
    arr = [0] * n
    # 70 short titles: 1 of len 1, 20 of len 2, 49 of len 3
    short = [1] * 1 + [2] * 20 + [3] * 49
    assert len(short) == 70
    for i, v in enumerate(short):
        arr[i] = v
    # from 70 to i50: ramp 4 -> 14
    for i in range(70, i50 + 1):
        t = (i - 70) / max(1, i50 - 70)
        arr[i] = 4 + int(round((14 - 4) * t))
    arr[i50] = 14
    # i50 to i95: 14 -> 37
    for i in range(i50, i95 + 1):
        t = (i - i50) / max(1, i95 - i50)
        arr[i] = 14 + int(round((37 - 14) * t))
    arr[i95] = 37
    # i95 to end: 37 -> 86
    for i in range(i95, n):
        t = (i - i95) / max(1, (n - 1) - i95)
        arr[i] = 37 + int(round((86 - 37) * t))
    arr[-1] = 86
    arr[0] = 1
    # enforce non-decreasing
    for i in range(1, n):
        if arr[i] < arr[i - 1]:
            arr[i] = arr[i - 1]
    arr[i50] = 14
    arr[i95] = 37
    arr[-1] = 86
    arr[0] = 1
    return arr

def plot_lengths() -> list[int]:
    n = N_MOVIES
    arr = [0] * n
    for i in range(1180):
        arr[i] = 44 if i == 0 else 44 + (499 - 44) * i // 1179
    for i in range(1180, 3450):
        arr[i] = 500 + (2883 - 500) * (i - 1180) // (3449 - 1180)
    arr[3449] = 2883
    start = n - 416
    for i in range(3450, start):
        arr[i] = 2883 + (2999 - 2883) * (i - 3449) // ((start - 1) - 3449)
    for i in range(start, n):
        arr[i] = 3000
    arr[0] = 44
    for i in range(1, n):
        if arr[i] < arr[i - 1]:
            arr[i] = arr[i - 1]
    return arr


def build_degrees(
    n: int, total: int, n_zero: int, med: int, p95: int, mx: int,
    alpha: float, beta: float, min_pos: int = 1,
) -> list[int]:
    i50 = (n - 1) // 2
    i95 = int(0.95 * (n - 1))
    arrf = [0.0] * n
    span_l = max(1, i50 - n_zero)
    span_m = max(1, i95 - i50)
    span_r = max(1, (n - 1) - i95)
    for i in range(n_zero, i50 + 1):
        t = (i - n_zero) / span_l
        arrf[i] = min_pos + (med - min_pos) * (t ** alpha)
    for i in range(i50, i95 + 1):
        t = (i - i50) / span_m
        arrf[i] = med + (p95 - med) * (t ** beta)
    for i in range(i95, n):
        t = (i - i95) / span_r
        arrf[i] = p95 + (mx - p95) * t
    arrf[:n_zero] = [0.0] * n_zero
    arrf[i50] = float(med)
    arrf[i95] = float(p95)
    arrf[-1] = float(mx)
    arr = [int(round(v)) for v in arrf]
    arr[:n_zero] = [0] * n_zero
    for i in range(n_zero, n):
        arr[i] = max(min_pos, arr[i])
    arr[i50] = med
    arr[i95] = p95
    if i95 + 1 < n:
        arr[i95 + 1] = max(arr[i95 + 1], p95)
    arr[-1] = mx
    for i in range(n_zero, i50):
        arr[i] = min(arr[i], med)
    for i in range(1, n):
        if arr[i] < arr[i - 1]:
            arr[i] = arr[i - 1]
    for i in range(n_zero, i50):
        if arr[i] > med:
            arr[i] = med
    arr[i50] = med
    for i in range(i50 + 1, i95):
        if arr[i] < arr[i - 1]:
            arr[i] = arr[i - 1]
        if arr[i] > p95:
            arr[i] = p95
    arr[i95] = p95
    if i95 + 1 < n and arr[i95 + 1] < p95:
        arr[i95 + 1] = p95
    for i in range(max(i95 + 1, 1), n):
        if arr[i] < arr[i - 1]:
            arr[i] = arr[i - 1]
    arr[-1] = mx
    for i in range(n - 2, i95, -1):
        if arr[i] > arr[i + 1]:
            arr[i] = arr[i + 1]
        if arr[i] < p95:
            arr[i] = p95
    protected = {i50, i95, n - 1}
    if i95 + 1 < n - 1:
        protected.add(i95 + 1)
        arr[i95 + 1] = p95
        for i in range(i95 + 2, n):
            if arr[i] < arr[i - 1]:
                arr[i] = arr[i - 1]
        arr[-1] = mx
    guard = 0
    while sum(arr) != total and guard < n * 5:
        guard += 1
        if sum(arr) < total:
            placed = False
            for i in range(n - 2, n_zero - 1, -1):
                if i in protected:
                    continue
                ub = arr[i + 1]
                if i < i50:
                    ub = min(ub, med)
                elif i < i95:
                    ub = min(ub, p95)
                room = ub - arr[i]
                if room > 0:
                    arr[i] += min(room, total - sum(arr))
                    placed = True
                    if sum(arr) == total:
                        break
            if not placed:
                break
        else:
            placed = False
            for i in range(n_zero, n - 1):
                if i in protected:
                    continue
                lb = min_pos if i == n_zero or arr[i - 1] == 0 else max(min_pos, arr[i - 1])
                if i > n_zero:
                    lb = max(min_pos, arr[i - 1])
                room = arr[i] - lb
                if room > 0:
                    arr[i] -= min(room, sum(arr) - total)
                    placed = True
                    if sum(arr) == total:
                        break
            if not placed:
                break
    if sum(arr) != total:
        raise RuntimeError(f"degrees sum {sum(arr)} != {total}")
    return arr


def build_freq(n_ent: int, total: int, max_f: int, ones_frac: float) -> list[int]:
    target_ones = int(n_ent * ones_frac)
    while True:
        rest_n = n_ent - target_ones
        rest_sum = total - target_ones
        if rest_n > 0 and rest_sum >= 2 * rest_n and rest_sum <= max_f * rest_n and max_f >= 2:
            break
        target_ones -= max(1, n_ent // 200)
        if target_ones < 0:
            raise RuntimeError("no frequency solution")
    extra = rest_sum - 2 * rest_n
    weights = [(i + 1) ** -0.85 for i in range(rest_n)]
    wsum = sum(weights)
    adds = [int(extra * w / wsum) for w in weights]
    for i in range(rest_n):
        room = max_f - 2
        if adds[i] > room:
            adds[i] = room
    rem = extra - sum(adds)
    i = 0
    guard = 0
    while rem > 0 and guard < rest_n * (max_f + 2):
        if adds[i] < max_f - 2:
            adds[i] += 1
            rem -= 1
        i = (i + 1) % rest_n
        guard += 1
    if rem != 0:
        raise RuntimeError(f"frequency remainder {rem}")
    freqs = [2 + a for a in adds]
    need = max_f - freqs[0]
    if need < 0:
        raise RuntimeError("head above max")
    for j in range(rest_n - 1, 0, -1):
        if need == 0:
            break
        take = min(freqs[j] - 2, need)
        freqs[j] -= take
        need -= take
    if need:
        raise RuntimeError("cannot reach max frequency")
    freqs[0] = max_f
    out = freqs + [1] * target_ones
    out.sort(reverse=True)
    if sum(out) != total or len(out) != n_ent or out[0] != max_f or min(out) < 1:
        raise RuntimeError("bad frequencies")
    return out


def realize(movie_degrees: list[int], entity_freq: list[int]) -> list[list[int]]:
    result: list[list[int]] = [[] for _ in movie_degrees]
    eh = [(-entity_freq[i], i) for i in range(len(entity_freq))]
    heapq.heapify(eh)
    movies = [(-movie_degrees[i], i) for i in range(len(movie_degrees)) if movie_degrees[i] > 0]
    heapq.heapify(movies)
    while movies:
        nd, mi = heapq.heappop(movies)
        need = -nd
        chosen = []
        for _ in range(need):
            if not eh:
                raise RuntimeError(f"graph realization failed at movie {mi}")
            nr, ei = heapq.heappop(eh)
            chosen.append((nr, ei))
        for nr, ei in chosen:
            result[mi].append(ei)
            left = -nr - 1
            if left > 0:
                heapq.heappush(eh, (-left, ei))
    got: Counter[int] = Counter()
    for lst in result:
        if len(lst) != len(set(lst)):
            raise RuntimeError("duplicate entity inside a movie")
        got.update(lst)
    for i, freq in enumerate(entity_freq):
        if got[i] != freq:
            raise RuntimeError(f"entity {i} got {got[i]} want {freq}")
    return result


def spaced_ids(n: int, lo: int, hi: int) -> list[int]:
    ids = [lo + (hi - lo) * i // (n - 1) for i in range(n)]
    ids[0] = lo
    ids[-1] = hi
    for i in range(1, n):
        if ids[i] <= ids[i - 1]:
            ids[i] = ids[i - 1] + 1
    if ids[-1] > hi:
        ids[-1] = hi
        for i in range(n - 2, -1, -1):
            if ids[i] >= ids[i + 1]:
                ids[i] = ids[i + 1] - 1
        ids[0] = lo
    if ids[0] != lo or ids[-1] != hi or len(set(ids)) != n:
        raise RuntimeError("spaced ids failed")
    return ids


def movie_ids() -> list[int]:
    knots = [(0.0, 11), (0.10, 8055), (0.50, 239566), (0.90, 757860), (1.0, 1_059_999)]
    ids = []
    n = N_MOVIES
    for i in range(n):
        t = i / (n - 1)
        for (t0, v0), (t1, v1) in zip(knots, knots[1:]):
            if t <= t1 or t1 == 1.0:
                u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                ids.append(int(round(v0 + u * (v1 - v0))))
                break
    ids[0] = 11
    ids[-1] = 1_059_999
    for i in range(1, n):
        if ids[i] <= ids[i - 1]:
            ids[i] = ids[i - 1] + 1
    if ids[-1] > 1_059_999:
        ids[-1] = 1_059_999
        for i in range(n - 2, -1, -1):
            if ids[i] >= ids[i + 1]:
                ids[i] = ids[i + 1] - 1
        ids[0] = 11
    return ids


def assign_degrees(total_zeros_target: list[int], rng: random.Random) -> list[int]:
    order = list(range(N_MOVIES))
    rng.shuffle(order)
    out = [0] * N_MOVIES
    for rank, mi in enumerate(order):
        out[mi] = total_zeros_target[rank]
    return out


def round_tenths(thousandths: int) -> int:
    return (thousandths + 50) // 100


def fmt_cents(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def fmt_thou(value: int) -> str:
    return f"{value // 1000}.{value % 1000:03d}"


def fmt_tenth(value: int) -> str:
    return f"{value // 10}.{value % 10}"


def cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text == "":
        raise ValueError("empty string is not a value")
    return text


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        writer.writerows(rows)


def appearance(lists: list[list[int]]) -> tuple[list[int], dict[int, int]]:
    seen: dict[int, int] = {}
    order: list[int] = []
    for bucket in lists:
        for ent in bucket:
            if ent not in seen:
                seen[ent] = len(order)
                order.append(ent)
    return order, seen


def spread(quotas: list[tuple[str, int]], items: list[int], rng: random.Random) -> dict[int, str]:
    seq = list(items)
    rng.shuffle(seq)
    out: dict[int, str] = {}
    k = 0
    for code, count in quotas:
        for _ in range(count):
            out[seq[k]] = code
            k += 1
    if k != len(seq):
        raise RuntimeError(f"spread {k} != {len(seq)} for {quotas}")
    return out


def tune_matches(desired: list[int], scores: list[int], target: int) -> list[int]:
    """Permute `scores` so exactly `target` positions equal `desired`."""
    n = len(scores)
    pool = Counter(scores)
    by_des: dict[int, list[int]] = defaultdict(list)
    for i, want in enumerate(desired):
        by_des[want].append(i)
    assigned = [None] * n
    for want, idxs in by_des.items():
        take = min(len(idxs), pool[want])
        for i in idxs[:take]:
            assigned[i] = want
            pool[want] -= 1
    unassigned = [i for i in range(n) if assigned[i] is None]
    rest: list[int] = []
    for value, count in sorted(pool.items()):
        rest.extend([value] * count)
    if len(rest) != len(unassigned):
        raise RuntimeError("match assignment size")
    for i, value in zip(unassigned, rest):
        assigned[i] = value
    guard = 0
    while True:
        matches = [i for i in range(n) if assigned[i] == desired[i]]
        if len(matches) == target:
            break
        if len(matches) < target:
            raise RuntimeError(f"only {len(matches)} score matches, need {target}")
        i = matches[-1]
        partner = None
        for j in range(n):
            if j == i or assigned[j] == desired[j]:
                continue
            if assigned[j] != desired[i] and assigned[i] != desired[j]:
                partner = j
                break
        if partner is None:
            raise RuntimeError("could not reduce score matches")
        assigned[i], assigned[partner] = assigned[partner], assigned[i]
        guard += 1
        if guard > n:
            raise RuntimeError("match loop")
    if Counter(assigned) != Counter(scores):
        raise RuntimeError("user_score multiset changed")
    return assigned  # type: ignore[return-value]


def check_catalogs() -> None:
    if len(GENRES) != 19 or sum(GENRE_FREQ) != 18604:
        raise RuntimeError("genres")
    if any(GENRE_FREQ[i] <= GENRE_FREQ[i + 1] for i in range(18)):
        raise RuntimeError("genre frequencies not strictly decreasing")
    if sum(n for _, n in LANGS) != N_MOVIES or len(LANGS) != 43:
        raise RuntimeError("languages")
    if sum(n for _, n in COUNTRIES) != 10091 or len(COUNTRIES) != 98:
        raise RuntimeError("countries")
    if sum(n for _, n in SPOKEN) != 9855 or len(SPOKEN) != 68:
        raise RuntimeError("spoken")
    if sum(n for _, n in RATINGS) != N_MOVIES:
        raise RuntimeError("ratings")
    if sum(n for code, n in LANGS if code in NON_LATIN) != 666:
        raise RuntimeError("non-latin count")
    if len(FX_CURS) != 87 or len(ENRICHMENT_FIELDS) != 21:
        raise RuntimeError("fx or enrichment fields")
    if sum(n for _, n in EXTRA_FIELDS) != 4813:
        raise RuntimeError("extra fields")
    if len(ALPH62) != 62:
        raise RuntimeError("alphabet")
    for code in NON_LATIN:
        if code not in NATIVE:
            raise RuntimeError(f"no native lexicon for {code}")


def generate(out_dir: Path) -> None:
    check_catalogs()
    out_dir.mkdir(parents=True, exist_ok=True)
    log("atributos de película")
    ids = movie_ids()
    movies: list[dict] = [{"movie_id": mid} for mid in ids]

    lang_bag: list[str] = []
    for code, count in LANGS:
        lang_bag.extend([code] * count)
    rng_for("language").shuffle(lang_bag)
    rating_bag: list[str | None] = []
    for code, count in RATINGS:
        rating_bag.extend([code] * count)
    rng_for("rating").shuffle(rating_bag)

    scores = build_scores(N_MOVIES, rng_for("latents"))

    # Dates: strongly tied to movie_id via 'rel' score.
    dates = _dates(rng_for("dates"))
    dates_sorted = sorted(dates)
    date_map = assign_by_score(dates_sorted, list(range(N_MOVIES)), scores["rel"])

    r_null = rng_for("nulls")
    vote_null = set(r_null.sample(range(N_MOVIES), 5))
    runtime_null = set(r_null.sample(range(N_MOVIES), 6))
    imdb_null = set(r_null.sample(range(N_MOVIES), 10))
    homepage_null = set(r_null.sample(range(N_MOVIES), 1804))
    tagline_null = set(r_null.sample(range(N_MOVIES), 1188))
    poster_null = set(r_null.sample(range(N_MOVIES), 1))
    overview_null = set(r_null.sample(range(N_MOVIES), 2))
    backdrop_null = set(r_null.sample(range(N_MOVIES), 15))

    money_idx = list(range(N_MOVIES))
    rng_for("money-group").shuffle(money_idx)
    both = set(money_idx[:4067])
    budget_only = set(money_idx[4067:4463])
    revenue_only = set(money_idx[4463:5361])

    budgets_raw = [(v // 100) * 100 for v in anchored_ints(4463, 200_000, 2_000_000_000, 15_000_000_000, 38_000_000_000)]
    budgets_raw = diversify_sorted(budgets_raw, 620, rng_for("bud-div"), step=100_000)
    budgets_raw = round_millions(budgets_raw, 3550, rng_for("bud-round"))
    # re-anchor ends after rounding
    budgets_raw[0] = 200_000
    budgets_raw[-1] = 38_000_000_000
    revenues_raw = [(v // 100) * 100 for v in anchored_ints(4965, 61_800, 2_736_546_700, 43_388_886_600, 292_035_725_400)]
    popularity_raw = anchored_ints(N_MOVIES, 6466, 19940, 89106, 5_467_305)
    popularity_raw = diversify_sorted(popularity_raw, 6250, rng_for("pop-div"), step=1)
    popularity_raw[0] = 6466
    popularity_raw[-1] = 5_467_305
    runtimes_raw = anchored_ints(6893, 3, 101, 139, 400)
    vote_avg_raw = anchored_ints(6894, 1000, 6539, 7846, 10000)
    vote_cnt_raw = anchored_ints(6894, 1, 570, 7221, 32774)
    vote_cnt_raw = diversify_sorted(vote_cnt_raw, 2880, rng_for("vc-div"), step=1)
    vote_cnt_raw[0] = 1
    vote_cnt_raw[-1] = 32774
    user_vals_raw = anchored_ints(6894, 20, 65, 78, 100)

    b_movies = list(both | budget_only)
    r_movies = list(both | revenue_only)
    v_movies = [i for i in range(N_MOVIES) if i not in vote_null]
    rt_movies = [i for i in range(N_MOVIES) if i not in runtime_null]

    bud_map = assign_by_score(sorted(budgets_raw), b_movies, scores["bud"])
    rev_map = assign_by_score(sorted(revenues_raw), r_movies, scores["rev"])
    pop_map = assign_by_score(sorted(popularity_raw), list(range(N_MOVIES)), scores["pop"])
    rt_map = assign_by_score(sorted(runtimes_raw), rt_movies, scores["rt"])
    va_map = assign_by_score(sorted(vote_avg_raw), v_movies, scores["va"])
    vc_map = assign_by_score(sorted(vote_cnt_raw), v_movies, scores["vc"])
    # user_score: rank almost with vote_average (target Spearman 0.97), then hit 40% exact matches.
    us_score = [scores["va"][i] + 0.05 * scores["us"][i] for i in range(N_MOVIES)]
    us_map = assign_by_score(sorted(user_vals_raw), v_movies, us_score)

    for mi in range(N_MOVIES):
        movies[mi]["budget"] = bud_map.get(mi)
        movies[mi]["revenue"] = rev_map.get(mi)
        movies[mi]["popularity"] = pop_map[mi]
        movies[mi]["lang"] = lang_bag[mi]
        movies[mi]["rating"] = rating_bag[mi]
        movies[mi]["release"] = date_map[mi]
        movies[mi]["status"] = "Released"
        movies[mi]["runtime"] = rt_map.get(mi)
        if mi in va_map:
            movies[mi]["vote_average"] = va_map[mi]
            movies[mi]["vote_count"] = vc_map[mi]
            movies[mi]["user_score"] = us_map[mi]
        else:
            movies[mi]["vote_average"] = None
            movies[mi]["vote_count"] = None
            movies[mi]["user_score"] = None

    # Gentle match tuning: swap only when both sides stay near their rank neighbours.
    desired = {mi: round_tenths(movies[mi]["vote_average"]) for mi in v_movies}
    matches = [mi for mi in v_movies if movies[mi]["user_score"] == desired[mi]]
    target_matches = 2758
    rng_m = rng_for("score-matches")
    # Build index of movies by current user_score value
    by_val: dict[int, list[int]] = defaultdict(list)
    for mi in v_movies:
        by_val[movies[mi]["user_score"]].append(mi)
    guard = 0
    while len(matches) < target_matches and guard < 50000:
        guard += 1
        mi = rng_m.choice(v_movies)
        if movies[mi]["user_score"] == desired[mi]:
            continue
        want = desired[mi]
        donors = [d for d in by_val.get(want, []) if movies[d]["user_score"] == want and desired[d] != want]
        if not donors:
            continue
        d = donors[0]
        # swap
        by_val[movies[mi]["user_score"]].remove(mi)
        by_val[want].remove(d)
        movies[mi]["user_score"], movies[d]["user_score"] = movies[d]["user_score"], movies[mi]["user_score"]
        by_val[movies[mi]["user_score"]].append(mi)
        by_val[movies[d]["user_score"]].append(d)
        matches = [x for x in v_movies if movies[x]["user_score"] == desired[x]]
    while len(matches) > target_matches and guard < 100000:
        guard += 1
        mi = matches[-1]
        # swap with someone who would not become a match
        partner = None
        for j in v_movies:
            if j == mi:
                continue
            if movies[j]["user_score"] == desired[j]:
                continue
            if movies[j]["user_score"] != desired[mi] and movies[mi]["user_score"] != desired[j]:
                partner = j
                break
        if partner is None:
            break
        movies[mi]["user_score"], movies[partner]["user_score"] = movies[partner]["user_score"], movies[mi]["user_score"]
        matches = [x for x in v_movies if movies[x]["user_score"] == desired[x]]
    if abs(len(matches) - target_matches) > 5:
        # fall back to exact tuner (may soften Spearman a bit)
        current = [movies[mi]["user_score"] for mi in v_movies]
        tuned = tune_matches([desired[mi] for mi in v_movies], current, target_matches)
        for mi, value in zip(v_movies, tuned):
            movies[mi]["user_score"] = value

    log("relaciones")
    degree_specs = {
        "genre": (18604, 6, 3, 5, 9, 3.8, 1.8),
        "keyword": (53857, 307, 7, 18, 67, 2.8, 2.6),
        "cast": (178939, 16, 20, 64, 451, 4.8, 3.8),
        "company": (23971, 61, 3, 8, 27, 4.0, 2.8),
        "country": (10091, 21, 1, 3, 16, 0.4, 3.8),
        "spoken": (9855, 12, 1, 3, 10, 0.4, 3.8),
    }
    degrees = {}
    # genre/company/country/spoken: keep random shuffle (no correlation target)
    for name, (total, zeros, med, p95, mx, alpha, beta) in degree_specs.items():
        seq = build_degrees(N_MOVIES, total, zeros, med, p95, mx, alpha, beta)
        if name == "keyword":
            # assign high keyword counts to low movie_id via scores["kw"]
            order = sorted(range(N_MOVIES), key=lambda i: (scores["kw"][i], i))
            deg = [0] * N_MOVIES
            for rank, mi in enumerate(order):
                deg[mi] = seq[rank]
            degrees[name] = deg
        elif name == "cast":
            order = sorted(range(N_MOVIES), key=lambda i: (scores["cast"][i], i))
            deg = [0] * N_MOVIES
            for rank, mi in enumerate(order):
                deg[mi] = seq[rank]
            degrees[name] = deg
        else:
            degrees[name] = assign_degrees(seq, rng_for("deg-" + name))
    genre_of = realize(degrees["genre"], GENRE_FREQ)
    keyword_freq = build_freq(11762, 53857, 650, 0.45)
    keyword_of = realize(degrees["keyword"], keyword_freq)
    person_freq = build_freq(95050, 178939, 100, 0.60)
    person_of = realize(degrees["cast"], person_freq)
    company_freq = build_freq(8061, 23971, 300, 0.60)
    company_of = realize(degrees["company"], company_freq)
    country_of = realize(degrees["country"], [n for _, n in COUNTRIES])
    spoken_of = realize(degrees["spoken"], [n for _, n in SPOKEN])

    # Resolve keyword name clashes before texts/write (names needed).
    keyword_name_preview = _keyword_names()
    fix_keyword_name_clashes(keyword_of, keyword_name_preview)

    collection_of, obs_poster, obs_backdrop = _collections()

    log("enrichment")
    enrich = _enrichment(
        movies, vote_null, imdb_null, homepage_null, tagline_null, poster_null,
        overview_null, backdrop_null, genre_of, keyword_of, person_of,
        company_of, country_of, spoken_of, collection_of,
    )
    _apply_fx(movies, enrich)

    log("textos")
    _texts(
        movies, imdb_null, homepage_null, tagline_null, poster_null,
        overview_null, backdrop_null, scores,
    )

    log("escritura")
    _write_all(
        out_dir, movies, genre_of, keyword_of, person_of, company_of,
        country_of, spoken_of, collection_of, obs_poster, obs_backdrop, enrich,
        keyword_names=keyword_name_preview,
    )


def _dates(rng: random.Random) -> list[date]:
    def span(start: date, end: date, count: int, forced: date | None = None) -> list[date]:
        days = (end - start).days
        out = [start + timedelta(days=rng.randrange(days + 1)) for _ in range(count)]
        if forced is not None:
            out[0] = forced
        return out

    out = []
    out += span(date(1902, 4, 17), date(1999, 12, 31), 272, date(1902, 4, 17))
    out += span(date(2000, 1, 1), date(2009, 12, 31), 1926)
    out += span(date(2010, 1, 1), date(2019, 12, 31), 3176)
    out += span(date(2020, 1, 1), date(2023, 8, 2), 1525, date(2023, 8, 2))
    if len(out) != N_MOVIES:
        raise RuntimeError("dates")
    return out


def _collections() -> tuple[list[int | None], list[str | None], list[str | None]]:
    rng = rng_for("collections")
    order = list(range(N_MOVIES))
    rng.shuffle(order)
    chosen = order[:1934]
    sizes = [1] * 400 + [2] * 400 + [3] * 235 + [4] * 3 + [17]
    rng.shuffle(sizes)
    groups: list[list[int]] = []
    k = 0
    for size in sizes:
        groups.append(chosen[k:k + size])
        k += size
    ranked = sorted(range(len(groups)), key=lambda g: (-len(groups[g]), min(groups[g])))
    divergent = []
    for g in ranked:
        if len(groups[g]) >= 2:
            divergent.append(g)
        if len(divergent) == 4:
            break
    if len(divergent) != 4:
        raise RuntimeError("divergent collections")
    divergent_set = set(divergent)
    collection_of: list[int | None] = [None] * N_MOVIES
    obs_p: list[str | None] = [None] * N_MOVIES
    obs_b: list[str | None] = [None] * N_MOVIES
    counter = 50_000_000
    for gi, group in enumerate(groups):
        for mi in group:
            collection_of[mi] = gi
        if gi in divergent_set:
            for mi in group:
                obs_p[mi] = path_from(counter)
                counter += 1
                obs_b[mi] = path_from(counter)
                counter += 1
        else:
            poster = path_from(counter)
            counter += 1
            backdrop = path_from(counter)
            counter += 1
            for mi in group:
                obs_p[mi] = poster
                obs_b[mi] = backdrop
    return collection_of, obs_p, obs_b


def _heavy_extras() -> list[int]:
    # Two movies at 2 keep the percentile 4; one movie at 11 reaches the max.
    # A pile of 11s is not graphical against the enrichment quotas.
    parts = (
        (2, 2), (4, 142), (5, 131), (6, 40), (7, 16),
        (8, 8), (9, 4), (10, 2), (11, 1),
    )
    extra: list[int] = []
    for value, count in parts:
        extra.extend([value] * count)
    if len(extra) != 346 or sum(extra) != 1710 or extra[0] != 2 or extra[-1] != 11:
        raise RuntimeError("heavy extras")
    return extra


def _enrichment(
    movies, vote_null, imdb_null, homepage_null, tagline_null, poster_null,
    overview_null, backdrop_null, genre_of, keyword_of, person_of, company_of,
    country_of, spoken_of, collection_of,
):
    elig = {
        "overview": [i not in overview_null for i in range(N_MOVIES)],
        "genres": [bool(genre_of[i]) for i in range(N_MOVIES)],
        "poster_path": [i not in poster_null for i in range(N_MOVIES)],
        "cast": [bool(person_of[i]) for i in range(N_MOVIES)],
        "spoken_languages": [bool(spoken_of[i]) for i in range(N_MOVIES)],
        "imdb_id": [i not in imdb_null for i in range(N_MOVIES)],
        "backdrop_path": [i not in backdrop_null for i in range(N_MOVIES)],
        "runtime": [movies[i].get("runtime") is not None for i in range(N_MOVIES)],
        "vote_average": [movies[i].get("vote_average") is not None for i in range(N_MOVIES)],
        "vote_count": [movies[i].get("vote_count") is not None for i in range(N_MOVIES)],
        "production_countries": [bool(country_of[i]) for i in range(N_MOVIES)],
        "production_companies": [bool(company_of[i]) for i in range(N_MOVIES)],
        "belongs_to_collection": [collection_of[i] is not None for i in range(N_MOVIES)],
        "rating": [movies[i]["rating"] is not None for i in range(N_MOVIES)],
        "keywords": [bool(keyword_of[i]) for i in range(N_MOVIES)],
        "tagline": [i not in tagline_null for i in range(N_MOVIES)],
        "budget": [movies[i].get("budget") is not None for i in range(N_MOVIES)],
        "revenue": [movies[i].get("revenue") is not None for i in range(N_MOVIES)],
        "homepage": [i not in homepage_null for i in range(N_MOVIES)],
    }
    elig_count = [sum(1 for field, _ in EXTRA_FIELDS if elig[field][i]) for i in range(N_MOVIES)]
    ranked = [i for i in range(N_MOVIES) if i not in vote_null]
    ranked.sort(key=lambda i: (-elig_count[i], i))
    chosen = ranked[:3449]
    chosen_set = set(chosen)
    for field, count in EXTRA_FIELDS:
        have = sum(1 for i in chosen if elig[field][i])
        if have >= count:
            continue
        deficit = count - have
        incoming = [i for i in ranked if i not in chosen_set and elig[field][i]]
        outgoing = [i for i in reversed(chosen) if not elig[field][i]]
        if len(incoming) < deficit or len(outgoing) < deficit:
            raise RuntimeError(f"cannot cover {field}: have {have}, need {count}")
        for old, new in zip(outgoing[:deficit], incoming[:deficit]):
            chosen_set.remove(old)
            chosen_set.add(new)
        chosen = [i for i in ranked if i in chosen_set]
    heavy = sorted(_heavy_extras(), reverse=True)
    targets = [0] * N_MOVIES
    for mi, extra in zip(chosen, heavy):
        if elig_count[mi] < extra:
            raise RuntimeError(f"movie {mi} eligibility {elig_count[mi]} < {extra}")
        targets[mi] = extra
    for mi in chosen[346:]:
        if elig_count[mi] < 1:
            raise RuntimeError(f"movie {mi} has no extra field")
        targets[mi] = 1
    if sum(targets) != 4813 or len(chosen) != 3449:
        raise RuntimeError(f"extra targets {sum(targets)} movies {len(chosen)}")

    remaining = targets[:]
    enrich = [dict() for _ in range(N_MOVIES)]
    # Largest quotas first so a field is not left without capacity.
    for field, count in sorted(EXTRA_FIELDS, key=lambda item: (-item[1], item[0])):
        candidates = [i for i in range(N_MOVIES) if elig[field][i] and remaining[i] > 0]
        candidates.sort(key=lambda i: (-remaining[i], i))
        if len(candidates) < count:
            raise RuntimeError(
                f"{field} needs {count} movies with capacity, found {len(candidates)}"
            )
        for mi in candidates[:count]:
            enrich[mi][field] = ""
            remaining[mi] -= 1
    unfilled = [i for i in range(N_MOVIES) if remaining[i]]
    if unfilled:
        raise RuntimeError(f"{len(unfilled)} movies still need enrichment fields")

    plot_codes = spread([
        ("wikipedia_plot_2026-11-12", 3635),
        ("wikipedia_plot_2026-11-13", 1768),
        ("tmdb_overview", 1065),
        ("unverified", 429),
        ("tmdb_metadata_summary", 1),
        ("tmdb_overview_translated:zh-CN", 1),
    ], list(range(N_MOVIES)), rng_for("code-plot"))
    for mi, code in plot_codes.items():
        enrich[mi]["plot"] = code
    user_codes = spread([
        ("tmdb_api_2026-10-22", 6886),
        ("tmdb_api_fallback_doc_vote_average", 8),
    ], [i for i in range(N_MOVIES) if i not in vote_null], rng_for("code-user"))
    for mi, code in user_codes.items():
        enrich[mi]["user_score"] = code

    quotas = {
        "tagline": [("tmdb_api_2026-10-22", 433)],
        "keywords": [("tmdb_api_2026-10-22", 315)],
        "belongs_to_collection": [("tmdb_api_2026-10-22", 169)],
        "vote_average": [("tmdb_api_2026-10-22", 57)],
        "vote_count": [("tmdb_api_2026-10-22", 57)],
        "runtime": [("tmdb_api_2026-10-22", 29)],
        "backdrop_path": [("tmdb_api_2026-10-22", 27)],
        "imdb_id": [("tmdb_api_2026-10-22", 16)],
        "spoken_languages": [("tmdb_api_2026-10-22", 15)],
        "cast": [("tmdb_api_2026-10-22", 7)],
        "poster_path": [("tmdb_api_2026-10-22", 4)],
        "genres": [("tmdb_api_2026-10-22", 3)],
        "overview": [("tmdb_api_2026-10-22", 2)],
        "homepage": [("wikidata", 1293), ("tmdb_api_2026-10-22", 234)],
        "rating": [("tmdb_api_2026-10-22", 240), ("wikidata", 31)],
        "production_companies": [("tmdb_api_2026-10-22", 86), ("wikidata", 7)],
        "production_countries": [("tmdb_api_2026-10-22", 59), ("wikidata", 11)],
        "revenue": [
            ("tmdb_api_2026-10-22", 572), ("wikipedia_infobox", 346),
            ("wikidata", 64), ("FX", 22),
        ],
        "budget": [
            ("tmdb_api_2026-10-22", 372), ("wikipedia_infobox", 199),
            ("FX", 65), ("wikidata", 63), ("wikipedia_infobox_range_midpoint", 15),
        ],
    }
    for field, pairs in quotas.items():
        owners = [i for i in range(N_MOVIES) if field in enrich[i]]
        for mi, code in spread(pairs, owners, rng_for("code-" + field)).items():
            enrich[mi][field] = code
    counts = sorted(len(row) for row in enrich)
    if counts[0] != 1 or counts[3449] != 2 or percentile(counts, 95) != 4 or counts[-1] != 13:
        raise RuntimeError(
            f"enrichment shape min={counts[0]} p50={counts[3449]} "
            f"p95={percentile(counts, 95)} max={counts[-1]}"
        )
    if sum(counts) != 18606:
        raise RuntimeError(f"enrichment rows {sum(counts)}")
    return enrich


def _apply_fx(movies: list[dict], enrich: list[dict]) -> None:
    curs = FX_CURS[:]
    rng_for("fx-currency").shuffle(curs)
    pointer = 0
    budget_anchors = {200_000, 2_000_000_000, 15_000_000_000, 38_000_000_000}
    revenue_anchors = {61_800, 2_736_546_700, 43_388_886_600, 292_035_725_400}

    def place(field: str, count: int, amount_key: str, anchors: set[int], vmax: int) -> None:
        nonlocal pointer
        chosen = [i for i in range(N_MOVIES) if enrich[i].get(field) == "FX"]
        if len(chosen) != count:
            raise RuntimeError(f"{field} fx {len(chosen)}")
        bad = [i for i in chosen if not 1972 <= movies[i]["release"].year <= 2022]
        donors = [
            i for i in range(N_MOVIES)
            if field in enrich[i] and enrich[i][field] != "FX"
            and 1972 <= movies[i]["release"].year <= 2022
        ]
        rng_for("fx-swap-" + field).shuffle(donors)
        if len(donors) < len(bad):
            raise RuntimeError(f"not enough {field} fx donors")
        for bad_i, donor in zip(bad, donors):
            enrich[bad_i][field], enrich[donor][field] = enrich[donor][field], enrich[bad_i][field]
        final = [i for i in range(N_MOVIES) if enrich[i].get(field) == "FX"]
        if len(final) != count:
            raise RuntimeError(f"{field} fx drifted")
        for mi in final:
            year = movies[mi]["release"].year
            cur = curs[pointer]
            pointer += 1
            enrich[mi][field] = f"wikipedia_infobox_fx:{cur}:{year}"
            amount = movies[mi][amount_key]
            if amount in anchors:
                continue
            bumped = amount + (mi * 17 + 3) % 99 + 1
            if bumped <= vmax:
                movies[mi][amount_key] = bumped

    place("budget", 65, "budget", budget_anchors, 38_000_000_000)
    place("revenue", 22, "revenue", revenue_anchors, 292_035_725_400)
    if pointer != 87:
        raise RuntimeError(f"fx currencies used {pointer}")


def tagline_lengths(n: int = 5711) -> list[int]:
    """Tagline lengths: one 3-character tagline, none between 4 and 13, anchors kept."""
    vals = anchored_ints(n, 3, 32, 70, 248)
    for i in range(1, n):
        if vals[i] < 14:
            vals[i] = 14 + (i % 15)
    return sorted(vals)


HOME_WORDS: dict[int, list[str]] = {}
for _w_ in _w("""en us uk faq new now app top home film cast news info site watch press story about media photo
movies videos photos awards trailer tickets gallery credits release reviews contact official synopsis festival
schedule partners showtimes streaming downloads soundtrack screenplays productions"""):
    HOME_WORDS.setdefault(len(_w_), []).append(_w_)


def _hyphen_words(k: int, rng: random.Random) -> str:
    """Hyphen-joined real words of exactly k characters (k >= 2)."""
    parts: list[str] = []
    while k > 11:
        w = rng.choice([x for x in HOME_WORDS[rng.randrange(4, 9)] if x not in parts] or ["film"])
        parts.append(w)
        k -= len(w) + 1
    if k < 2:  # give back the last word and refill
        k += len(parts.pop()) + 1
        a = k // 2
        parts += [rng.choice(HOME_WORDS[a]), rng.choice(HOME_WORDS[k - a - 1])]
    else:
        parts.append(rng.choice(HOME_WORDS[k]))
    return "-".join(parts)


def make_home(length: int, https: bool, title: str, year: int, rng: random.Random) -> str:
    """Homepage on a reserved `.example` domain, exactly `length` characters long."""
    if length < 17:
        https = False
    prefix = "https://" if https else "http://"
    words = re.findall(r"[a-z0-9]+", title.lower().encode("ascii", "ignore").decode())
    core = [w for w in words if w not in ("the", "a", "an", "of", "and")] or words or ["film"]
    domains = {
        "".join(words), "".join(core), core[0] + "film", core[0] + "movie", "www." + "".join(core),
        "".join(core) + "movie", "watch" + "".join(core), "".join(w[0] for w in words) + "film",
        "".join(w[0] for w in words), core[0], core[-1] + str(year), "www." + core[0] + "film",
    }
    budget = length - len(prefix) - len(".example")
    fits = sorted(d for d in domains if 0 < len(d) <= budget)
    if not fits:
        fits = [("".join(w[0] for w in words) or "f")[:budget]]
    rng.shuffle(fits)
    fits.sort(key=lambda d: length - len(prefix) - len(d) - len(".example") == 2)
    url = prefix + fits[0] + ".example"
    slug = "-".join(core)
    segs = ["/en", "/us", "/films", "/movies", f"/{year}", "/" + slug, "/press-kit", "/official", "/watch", "/tickets", "/gallery"]
    rng.shuffle(segs)
    params = [("utm_source", ["newsletter", "social", "trailer", "poster", "festival", "press"]),
              ("utm_medium", ["email", "banner", "video", "print"]), ("utm_campaign", [slug + "-" + str(year)]),
              ("lang", ["en", "fr", "es", "de"]), ("region", ["us", "uk", "ca", "au"])]
    while length - len(url) > 30 and segs and rng.random() < 0.7:
        seg = segs.pop()
        if length - len(url) - len(seg) >= 20:
            url += seg
    for key, values in params:
        value = rng.choice(values)
        piece = ("&" if "?" in url else "?") + key + "=" + value
        if length - len(url) - len(piece) < 20:
            break
        url += piece
    k = length - len(url)
    if k == 1:
        url += "/"
    elif k == 2:
        url += "/" + str(year % 10)
    elif k == 3:
        url += "/" + rng.choice(HOME_WORDS[2])
    elif k >= 4:
        if "?" in url:
            head = "&utm_content="
            if k - len(head) >= 2:
                url += head + _hyphen_words(k - len(head), rng)
            else:
                url += "/" + _hyphen_words(k - 1, rng)
        else:
            url += "/" + _hyphen_words(k - 1, rng)
    if len(url) != length:
        raise RuntimeError(f"homepage {length} {url}")
    return url


def _texts(movies, imdb_null, homepage_null, tagline_null, poster_null, overview_null, backdrop_null, scores) -> None:
    title_len_map = assign_by_score(title_lengths(), list(range(N_MOVIES)), scores["tl"])
    plot_len = plot_lengths()
    if sum(1 for n in plot_len if n < 500) != 1180 or sum(1 for n in plot_len if n == 3000) != 416:
        raise RuntimeError("plot length shape")
    plot_len_map = assign_by_score(plot_len, list(range(N_MOVIES)), scores["plot"])
    tag_movies = [i for i in range(N_MOVIES) if i not in tagline_null]
    ov_movies = [i for i in range(N_MOVIES) if i not in overview_null]
    hp_movies = [i for i in range(N_MOVIES) if i not in homepage_null]
    tag_len_map = assign_by_score(tagline_lengths(len(tag_movies)), tag_movies, scores["tl"])
    ov_len_map = assign_by_score(anchored_ints(len(ov_movies), 39, 232, 529, 1445), ov_movies, scores["ov"])
    # homepage: minimum 16 (documented exception; .example domains cannot be shorter)
    hp_len_map = assign_by_score(homepage_lengths(len(hp_movies)), hp_movies, scores["tl"])

    non_en = [i for i in range(N_MOVIES) if movies[i]["lang"] != "en"]
    non_latin = [i for i in non_en if movies[i]["lang"] in NON_LATIN]
    lexicon_latin = [i for i in non_en if movies[i]["lang"] not in NON_LATIN and latin_language(movies[i]["lang"]) == movies[i]["lang"] or movies[i]["lang"] == "nb"]
    if len(non_en) != 1232 or len(non_latin) != 666 or len(lexicon_latin) < 425:
        raise RuntimeError(f"language split non-en={len(non_en)} non-latin={len(non_latin)}")
    # 666 native-script + 425 Latin other-language = 1091 (documented: ~770 native was impossible under frozen LANGS)
    differ = set(non_latin) | set(rng_for("latin-originals").sample(lexicon_latin, 425))

    # Cell-content quotas (section 4.5), chosen among texts long enough to hold them.
    rng_sets = rng_for("cell-content")
    long_plots = [i for i in range(N_MOVIES) if plot_len_map[i] >= 140]
    quote_plot = set(rng_sets.sample(long_plots, 3133))
    nl_pool = [i for i in range(N_MOVIES) if plot_len_map[i] >= 100 and i not in quote_plot]
    newline_set = set(rng_sets.sample(sorted(quote_plot), 3010)) | set(rng_sets.sample(nl_pool, 5480 - 3010))
    shortest = sorted(range(N_MOVIES), key=lambda i: (plot_len_map[i], i))
    no_comma_plot = set([i for i in shortest if i not in quote_plot][:600][::6][:93])
    comma_plot = set(range(N_MOVIES)) - no_comma_plot
    if len(comma_plot) != 6806:
        raise RuntimeError(f"comma plots {len(comma_plot)}")
    comma_ov = set(rng_sets.sample([i for i in ov_movies if ov_len_map[i] >= 60], 5695))
    quote_ov = set(rng_sets.sample([i for i in ov_movies if ov_len_map[i] >= 110], 316))
    comma_tag = set(rng_sets.sample([i for i in tag_movies if tag_len_map[i] >= 30], 666))
    quote_tag = set(rng_sets.sample([i for i in tag_movies if tag_len_map[i] >= 40 and i not in comma_tag], 12))
    comma_title = set(rng_sets.sample([i for i in range(N_MOVIES) if 14 <= title_len_map[i] <= 34], 87))
    quote_title = {rng_sets.choice([i for i in range(N_MOVIES) if 18 <= title_len_map[i] <= 26 and i not in comma_title])}
    https_set = set(rng_sets.sample(hp_movies, 2191))

    # IMDb ids: unique, ~15 % with 8 digits, scattered (few consecutive pairs).
    imdb_movies = [i for i in range(N_MOVIES) if i not in imdb_null]
    rng_imdb = rng_for("imdb-ids")
    eight_n = 1033
    seven_vals = rng_imdb.sample(range(417, 10_000_000), len(imdb_movies) - eight_n)
    eight_vals = rng_imdb.sample(range(10_000_000, 35_725_827), eight_n - 1) + [35_725_827]
    seven_vals[0] = 417
    all_nums = seven_vals + eight_vals
    rng_imdb.shuffle(all_nums)
    sorted_nums = sorted(all_nums)
    if len(set(all_nums)) != len(all_nums) or sum(1 for a, b in zip(sorted_nums, sorted_nums[1:]) if b - a == 1) >= 100:
        raise RuntimeError("imdb ids")
    imdb_assign = {mi: (f"tt{num:08d}" if num >= 10_000_000 else f"tt{num:07d}") for mi, num in zip(imdb_movies, all_nums)}

    titles = build_titles(title_len_map, comma_title, quote_title, rng_for("titles"))
    used_plots: set[str] = set()
    used_ovs: set[str] = set()
    used_tags: set[str] = set()
    used_homes: set[str] = set()
    for mi in range(N_MOVIES):
        movie = movies[mi]
        title = titles[mi]
        movie["title"] = title
        lang = movie["lang"]
        if mi in differ:
            rng_o = random.Random(SEED * 3 + mi)
            code = lang if lang in NON_LATIN else latin_language(lang)
            original = original_title(code, len(title), rng_o)
            while original == title:
                original = original_title(code, len(title), rng_o)
        else:
            original = title
        movie["original_title"] = original

        rng_p = random.Random(SEED + mi * 11003 + 4)
        plen = plot_len_map[mi]
        while True:
            plot = compose(plen, rng_p, mi in comma_plot, mi in quote_plot, mi in newline_set, plen == 3000)
            if plot not in used_plots:
                break
        used_plots.add(plot)
        movie["plot"] = plot

        if mi in overview_null:
            movie["overview"] = None
        else:
            rng_v = random.Random(SEED + mi * 13001 + 2)
            while True:
                ov = compose(ov_len_map[mi], rng_v, mi in comma_ov, mi in quote_ov, False, False)
                if ov not in used_ovs:
                    break
            used_ovs.add(ov)
            movie["overview"] = ov

        if mi in tagline_null:
            movie["tagline"] = None
        else:
            rng_g = random.Random(SEED + mi * 17007 + 6)
            for _ in range(80):
                tag = compose_tagline(tag_len_map[mi], rng_g, mi in comma_tag, mi in quote_tag)
                if tag not in used_tags:
                    break
            used_tags.add(tag)
            movie["tagline"] = tag

        if mi in homepage_null:
            movie["homepage"] = None
        else:
            rng_h = random.Random(SEED + mi * 7919 + 8)
            year = movie["release"].year
            for _ in range(200):
                home = make_home(hp_len_map[mi], mi in https_set, title, year, rng_h)
                if home not in used_homes:
                    break
            used_homes.add(home)
            movie["homepage"] = home

        movie["poster"] = None if mi in poster_null else path_from(mi + 1)
        movie["backdrop"] = None if mi in backdrop_null else path_from(1_000_000 + mi)
        movie["imdb"] = None if mi in imdb_null else imdb_assign[mi]



def _opt(value: object, fmt=str) -> str:
    return "" if value is None else fmt(value)


def _write_all(
    out_dir, movies, genre_of, keyword_of, person_of, company_of, country_of,
    spoken_of, collection_of, obs_poster, obs_backdrop, enrich,
    keyword_names=None,
) -> None:
    person_name = _person_names(95050)
    company_name = _company_names()
    keyword_name = keyword_names if keyword_names is not None else _keyword_names()
    collection_name = _collection_names()
    g_order, g_seen = appearance(genre_of)
    k_order, k_seen = appearance(keyword_of)
    p_order, p_seen = appearance(person_of)
    c_order, c_seen = appearance(company_of)
    y_order, y_seen = appearance(country_of)
    s_order, s_seen = appearance(spoken_of)
    col_seen: dict[int, int] = {}
    col_order: list[int] = []
    for mi in range(N_MOVIES):
        col = collection_of[mi]
        if col is not None and col not in col_seen:
            col_seen[col] = len(col_order)
            col_order.append(col)
    if [len(g_order), len(k_order), len(p_order), len(c_order), len(y_order), len(s_order), len(col_order)] != [
        19, 11762, 95050, 8061, 98, 68, 1039,
    ]:
        raise RuntimeError("appearance missed an entity")
    k_ids = spaced_ids(11762, 30, 382027)
    col_ids = spaced_ids(1039, 10, 1_800_171)
    field_pos = {name: i for i, name in enumerate(ENRICHMENT_FIELDS)}

    tables: dict[str, list[list[str]]] = {
        "movie_status": [["Released"]],
        "content_rating": [[code] for code in ("G", "PG", "PG-13", "R", "NC-17", "NR", "TV-PG")],
        "original_language": [[code, ""] for code, _ in LANGS],
        "enrichment_field": [[name] for name in ENRICHMENT_FIELDS],
        "genre": [[str(g_seen[e] + 1), GENRES[e]] for e in g_order],
        "keyword": [[str(k_ids[k_seen[e]]), keyword_name[e]] for e in k_order],
        "person": [[str(p_seen[e] + 1), person_name[e]] for e in p_order],
        "production_company": [[str(c_seen[e] + 1), company_name[e]] for e in c_order],
        "production_country": [[str(y_seen[e] + 1), COUNTRIES[e][0]] for e in y_order],
        "spoken_language": [[str(s_seen[e] + 1), SPOKEN[e][0]] for e in s_order],
        "collection": [[str(col_ids[col_seen[e]]), collection_name[e]] for e in col_order],
    }
    movie_rows = []
    for movie in movies:
        movie_rows.append([
            str(movie["movie_id"]),
            _opt(movie["imdb"]),
            movie["title"],
            movie["original_title"],
            movie["lang"],
            _opt(movie["overview"]),
            movie["plot"],
            _opt(movie["tagline"]),
            movie["status"],
            _opt(movie["rating"]),
            movie["release"].isoformat(),
            _opt(movie.get("runtime")),
            _opt(movie.get("budget"), fmt_cents),
            _opt(movie.get("revenue"), fmt_cents),
            fmt_thou(movie["popularity"]),
            _opt(movie.get("user_score"), fmt_tenth),
            _opt(movie.get("vote_average"), fmt_thou),
            _opt(movie.get("vote_count")),
            "false",
            "false",
            _opt(movie["homepage"]),
            _opt(movie["poster"]),
            _opt(movie["backdrop"]),
        ])
    tables["movie"] = movie_rows

    def bridge(lists, seen, spaced=None):
        rows = []
        for mi, bucket in enumerate(lists):
            mid = str(movies[mi]["movie_id"])
            for pos, ent in enumerate(bucket, start=1):
                ident = str(spaced[seen[ent]] if spaced is not None else seen[ent] + 1)
                rows.append([mid, ident, str(pos)])
        return rows

    tables["movie_genre"] = bridge(genre_of, g_seen)
    tables["movie_keyword"] = bridge(keyword_of, k_seen, k_ids)
    tables["movie_cast"] = bridge(person_of, p_seen)
    tables["movie_production_company"] = bridge(company_of, c_seen)
    tables["movie_production_country"] = bridge(country_of, y_seen)
    tables["movie_spoken_language"] = bridge(spoken_of, s_seen)
    collection_rows = []
    for mi, col in enumerate(collection_of):
        if col is None:
            continue
        collection_rows.append([
            str(movies[mi]["movie_id"]),
            str(col_ids[col_seen[col]]),
            obs_poster[mi],
            obs_backdrop[mi],
        ])
    tables["movie_collection"] = collection_rows
    enrichment_rows = []
    for mi, row in enumerate(enrich):
        for field, code in sorted(row.items(), key=lambda kv: field_pos[kv[0]]):
            if not code or code == "FX":
                raise RuntimeError(f"empty enrichment code {field} movie {mi}")
            enrichment_rows.append([str(movies[mi]["movie_id"]), field, code])
    tables["movie_enrichment"] = enrichment_rows
    for name in FILE_ORDER:
        write_csv(out_dir / f"{name}.csv", HEADERS[name], tables[name])


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load(directory: Path):
    loaded = {}
    problems = []
    for name in FILE_ORDER:
        path = directory / f"{name}.csv"
        if not path.is_file():
            problems.append(f"falta {name}.csv")
            continue
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
            problems.append(f"{name}.csv tiene BOM o CR")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{name}.csv no es UTF-8")
            continue
        rows = list(csv.reader(io.StringIO(text)))
        loaded[name] = (raw, rows)
    return loaded, problems


def _expect(bucket: list[str], cond: bool, msg: str) -> None:
    if not cond and len(bucket) < 15:
        bucket.append(msg)


def validate_dir(directory: Path):
    """Comprueba las validaciones 1 a 9 sobre los CSV ya escritos."""
    buckets = {i: [] for i in range(1, 10)}
    loaded, missing = _load(directory)
    for msg in missing:
        buckets[1].append(msg)
    stats = []
    if len(loaded) != 20:
        return _report(buckets, stats)

    for name in FILE_ORDER:
        raw, rows = loaded[name]
        stats.append({
            "file": f"{name}.csv",
            "rows": max(0, len(rows) - 1),
            "bytes": len(raw),
            "sha256": _sha256(raw),
        })
        if len(raw) >= 50 * 1024 * 1024:
            buckets[1].append(f"{name}.csv supera 50 MB")
        if not rows or rows[0] != HEADERS[name]:
            buckets[1].append(f"cabecera de {name}.csv: {rows[0] if rows else 'vacío'}")
        width = len(HEADERS[name])
        if any(len(row) != width for row in rows):
            buckets[2].append(f"{name}.csv tiene filas con distinto número de campos")
        rewritten = io.StringIO()
        csv.writer(rewritten, lineterminator="\n", quoting=csv.QUOTE_MINIMAL).writerows(rows)
        if rewritten.getvalue().encode("utf-8") != raw:
            buckets[2].append(f"{name}.csv no es CSV canónico (comillas o NULL)")

    if any(buckets[i] for i in (1, 2)):
        return _report(buckets, stats)

    data = {name: rows[1:] for name, (_, rows) in loaded.items()}
    movies = data["movie"]
    by_id = {row[0]: row for row in movies}
    _expect(buckets[3], len(by_id) == len(movies), "movie_id repetido")
    _expect(buckets[5], [int(row[0]) for row in movies] == sorted(int(row[0]) for row in movies), "movie.csv no está ordenado por movie_id")

    def pk(rows, cols):
        seen = set()
        for row in rows:
            key = tuple(row[c] for c in cols)
            if key in seen:
                return False
            seen.add(key)
        return True

    pk_cols = {
        "movie_status": (0,), "content_rating": (0,), "original_language": (0,),
        "enrichment_field": (0,), "genre": (0,), "keyword": (0,), "person": (0,),
        "production_company": (0,), "production_country": (0,), "spoken_language": (0,),
        "collection": (0,), "movie": (0,), "movie_collection": (0,),
        "movie_genre": (0, 1), "movie_keyword": (0, 1), "movie_cast": (0, 1),
        "movie_production_company": (0, 1), "movie_production_country": (0, 1),
        "movie_spoken_language": (0, 1), "movie_enrichment": (0, 1),
    }
    for name, cols in pk_cols.items():
        _expect(buckets[3], pk(data[name], cols), f"PK repetida en {name}")

    def ids(name, col=0):
        return {row[col] for row in data[name]}

    genre_ids, keyword_ids = ids("genre"), ids("keyword")
    person_ids, company_ids = ids("person"), ids("production_company")
    country_ids, spoken_ids = ids("production_country"), ids("spoken_language")
    collection_ids, movie_ids = ids("collection"), ids("movie")
    status_ids, rating_ids = ids("movie_status"), ids("content_rating")
    language_ids, field_ids = ids("original_language"), ids("enrichment_field")
    for row in movies:
        if row[4] not in language_ids:
            buckets[4].append("idioma original inexistente")
            break
        if row[8] not in status_ids:
            buckets[4].append("status inexistente")
            break
        if row[9] and row[9] not in rating_ids:
            buckets[4].append("rating inexistente")
            break
    bridges = [
        ("movie_genre", genre_ids, 1), ("movie_keyword", keyword_ids, 1),
        ("movie_cast", person_ids, 1), ("movie_production_company", company_ids, 1),
        ("movie_production_country", country_ids, 1), ("movie_spoken_language", spoken_ids, 1),
    ]
    for name, catalog, col in bridges:
        for row in data[name]:
            if row[0] not in movie_ids or row[col] not in catalog:
                buckets[4].append(f"FK rota en {name}")
                break
    for row in data["movie_collection"]:
        if row[0] not in movie_ids or row[1] not in collection_ids:
            buckets[4].append("FK rota en movie_collection")
            break
    for row in data["movie_enrichment"]:
        if row[0] not in movie_ids or row[1] not in field_ids:
            buckets[4].append("FK rota en movie_enrichment")
            break
    for name, catalog in (
        ("genre", genre_ids), ("keyword", keyword_ids), ("person", person_ids),
        ("production_company", company_ids), ("production_country", country_ids),
        ("spoken_language", spoken_ids), ("collection", collection_ids),
        ("enrichment_field", field_ids), ("movie_status", status_ids),
        ("content_rating", rating_ids), ("original_language", language_ids),
    ):
        used_col = 1 if name not in ("movie_status", "content_rating", "original_language", "enrichment_field") else 0
        if name in ("movie_status", "content_rating", "original_language", "enrichment_field"):
            if name == "movie_status":
                used = {row[8] for row in movies}
            elif name == "content_rating":
                used = {row[9] for row in movies if row[9]}
            elif name == "original_language":
                used = {row[4] for row in movies}
            else:
                used = {row[1] for row in data["movie_enrichment"]}
        else:
            bridge_name = {
                "genre": "movie_genre", "keyword": "movie_keyword", "person": "movie_cast",
                "production_company": "movie_production_company",
                "production_country": "movie_production_country",
                "spoken_language": "movie_spoken_language", "collection": "movie_collection",
            }[name]
            used = {row[1] for row in data[bridge_name]}
        _expect(buckets[4], used == catalog, f"huérfanos o sobrantes en {name}")

    names_unique = {
        "genre": 1, "person": 1, "production_company": 1,
        "production_country": 1, "spoken_language": 1,
    }
    for name, col in names_unique.items():
        values = [row[col] for row in data[name]]
        _expect(buckets[3], len(values) == len(set(values)) and all(values), f"UNIQUE(name) en {name}")
    imdb = [row[1] for row in movies if row[1]]
    _expect(buckets[3], len(imdb) == len(set(imdb)), "imdb_id repetido")
    posters = [row[21] for row in movies if row[21]]
    _expect(buckets[5], len(posters) == len(set(posters)), "poster_path repetido")

    def position_ok(rows, pos_col):
        grouped = defaultdict(list)
        for row in rows:
            grouped[row[0]].append(int(row[pos_col]))
        for mid, poss in grouped.items():
            if poss != list(range(1, len(poss) + 1)):
                return False
        return True

    for name, col in (
        ("movie_genre", 2), ("movie_keyword", 2), ("movie_cast", 2),
        ("movie_production_company", 2), ("movie_production_country", 2),
        ("movie_spoken_language", 2),
    ):
        _expect(buckets[3], pk(data[name], (0, col)), f"posición repetida en {name}")
        _expect(buckets[5], position_ok(data[name], col), f"posiciones no consecutivas en {name}")

    for row in movies:
        mid = int(row[0])
        _expect(buckets[5], mid > 0, "movie_id <= 0")
        if row[1]:
            _expect(buckets[5], bool(IMDB_RE.match(row[1])), f"imdb_id {row[1]}")
        if row[11]:
            _expect(buckets[5], int(row[11]) > 0, "runtime <= 0")
        if row[14]:
            _expect(buckets[5], float(row[14]) >= 0, "popularity < 0")
        for idx, label in ((15, "user_score"), (16, "vote_average")):
            if row[idx]:
                value = float(row[idx])
                _expect(buckets[5], 0 <= value <= 10, f"{label} fuera de rango")
        if row[17]:
            _expect(buckets[5], int(row[17]) >= 0, "vote_count < 0")
        if row[20]:
            _expect(buckets[5], row[20].startswith(("http://", "https://")), "homepage")
        for idx in (21, 22):
            if row[idx]:
                _expect(buckets[5], bool(PATH_RE.match(row[idx])), f"ruta {row[idx][:40]}")
        if len(buckets[5]) >= 15:
            break
    _expect(buckets[5], all(row[1] == "" for row in data["original_language"]), "description no es NULL")
    _expect(buckets[5], len(data["movie_collection"]) == len({row[0] for row in data["movie_collection"]}), "película en dos colecciones")

    def appearance_ok(entity_rows, bridge_rows):
        seen = []
        known = set()
        grouped = defaultdict(list)
        for row in bridge_rows:
            grouped[row[0]].append((int(row[2]), row[1]))
        for movie in movies:
            for _, ident in sorted(grouped[movie[0]]):
                if ident not in known:
                    known.add(ident)
                    seen.append(ident)
        return [row[0] for row in entity_rows] == seen

    for entity, bridge in (
        ("genre", "movie_genre"), ("keyword", "movie_keyword"), ("person", "movie_cast"),
        ("production_company", "movie_production_company"),
        ("production_country", "movie_production_country"),
        ("spoken_language", "movie_spoken_language"),
    ):
        _expect(buckets[5], appearance_ok(data[entity], data[bridge]), f"orden de {entity}")
    col_seen = []
    known = set()
    col_by_movie = {row[0]: row[1] for row in data["movie_collection"]}
    for movie in movies:
        ident = col_by_movie.get(movie[0])
        if ident and ident not in known:
            known.add(ident)
            col_seen.append(ident)
    _expect(buckets[5], [row[0] for row in data["collection"]] == col_seen, "orden de collection")
    for name in ("genre", "person", "production_company", "production_country", "spoken_language"):
        seq = [int(row[0]) for row in data[name]]
        _expect(buckets[5], seq == list(range(1, len(seq) + 1)), f"ids de {name}")

    required = {
        "movie": {0, 2, 3, 4, 6, 8, 10, 14, 18, 19},
    }
    for name, rows in data.items():
        cols = required.get(name, set(range(len(HEADERS[name]))))
        if name == "original_language":
            cols = {0}
        if name == "movie_collection":
            cols = {0, 1}
        for row in rows:
            if any(row[c] == "" for c in cols):
                buckets[6].append(f"NULL en columna obligatoria de {name}")
                break

    # Conteos y perfil.
    _expect(buckets[7], len(movies) == 6899, f"movie {len(movies)}")
    exact_rows = {
        "genre": 19, "production_country": 98, "spoken_language": 68,
        "original_language": 43, "movie_status": 1, "content_rating": 7,
        "enrichment_field": 21,
    }
    for name, count in exact_rows.items():
        _expect(buckets[7], len(data[name]) == count, f"{name} {len(data[name])}")
    tol_rows = {
        "collection": 1039, "movie_collection": 1934, "movie_genre": 18604,
        "keyword": 11762, "movie_keyword": 53857, "person": 95050,
        "movie_cast": 178939, "production_company": 8061,
        "movie_production_company": 23971, "movie_production_country": 10091,
        "movie_spoken_language": 9855, "movie_enrichment": 18606,
    }
    for name, count in tol_rows.items():
        _expect(buckets[7], near(len(data[name]), count), f"{name} {len(data[name])} vs {count}")

    rating_counts = Counter(row[9] if row[9] else None for row in movies)
    for code, count in RATINGS:
        _expect(buckets[7], rating_counts[code] == count, f"rating {code} {rating_counts[code]}")
    lang_counts = Counter(row[4] for row in movies)
    for code, count in LANGS:
        _expect(buckets[7], lang_counts[code] == count, f"lang {code}")
    genre_name = {row[0]: row[1] for row in data["genre"]}
    genre_freq = Counter(genre_name[row[1]] for row in data["movie_genre"])
    ordered = [genre_freq[name] for name in GENRES]
    _expect(buckets[7], all(ordered[i] > ordered[i + 1] for i in range(18)), f"géneros {ordered}")
    country_name = {row[0]: row[1] for row in data["production_country"]}
    country_freq = Counter(country_name[row[1]] for row in data["movie_production_country"])
    for name, count in COUNTRIES:
        _expect(buckets[7], country_freq[name] == count, f"país {name} {country_freq[name]}")
    spoken_name = {row[0]: row[1] for row in data["spoken_language"]}
    spoken_freq = Counter(spoken_name[row[1]] for row in data["movie_spoken_language"])
    for name, count in SPOKEN:
        _expect(buckets[7], spoken_freq[name] == count, f"idioma hablado {name} {spoken_freq[name]}")

    def degree_stats(bridge, pos_col):
        grouped = defaultdict(int)
        for row in data[bridge]:
            grouped[row[0]] += 1
        vals = [grouped.get(row[0], 0) for row in movies]
        vals.sort()
        return vals

    expectations = [
        ("géneros", "movie_genre", 2, 0, 3, 2.70, 5, 9, 6),
        ("keywords", "movie_keyword", 2, 0, 7, 7.81, 18, 67, 307),
        ("reparto", "movie_cast", 2, 0, 20, 25.94, 64, 451, 16),
        ("compañías", "movie_production_company", 2, 0, 3, 3.47, 8, 27, 61),
        ("países", "movie_production_country", 2, 0, 1, 1.46, 3, 16, 21),
        ("idiomas hablados", "movie_spoken_language", 2, 0, 1, 1.43, 3, 10, 12),
    ]
    for label, bridge, _pos, vmin, med, mean, p95, vmax, zeros in expectations:
        vals = degree_stats(bridge, 2)
        _expect(buckets[7], vals[0] == vmin and near(percentile(vals, 50), med) and near(sum(vals) / len(vals), mean) and near(percentile(vals, 95), p95) and near(vals[-1], vmax) and vals.count(0) == zeros,
                f"{label} min {vals[0]} p50 {percentile(vals, 50)} media {sum(vals)/len(vals):.3f} p95 {percentile(vals, 95)} max {vals[-1]} ceros {vals.count(0)}")

    enrich_counts = defaultdict(int)
    for row in data["movie_enrichment"]:
        enrich_counts[row[0]] += 1
    evals = sorted(enrich_counts.get(row[0], 0) for row in movies)
    _expect(buckets[7], evals[0] == 1 and near(percentile(evals, 50), 2) and near(sum(evals) / len(evals), 2.70) and near(percentile(evals, 95), 4) and near(evals[-1], 13) and evals.count(0) == 0,
            f"enrichment por película min {evals[0]} p50 {percentile(evals, 50)} max {evals[-1]}")

    def blanks(idx):
        return sum(1 for row in movies if row[idx] == "")

    null_targets = {1: 10, 5: 2, 7: 1188, 9: 715, 11: 6, 12: 2436, 13: 1934, 15: 5, 16: 5, 17: 5, 20: 1804, 21: 1, 22: 15}
    for idx, count in null_targets.items():
        _expect(buckets[7], blanks(idx) == count or near(blanks(idx), count), f"nulos col {idx}: {blanks(idx)} vs {count}")
    same_votes = [
        row[15] == "" and row[16] == "" and row[17] == "" or row[15] and row[16] and row[17]
        for row in movies
    ]
    _expect(buckets[7], all(same_votes), "nulos de voto no coinciden")
    both = budget_only = revenue_only = neither = 0
    for row in movies:
        b, r = bool(row[12]), bool(row[13])
        if b and r:
            both += 1
        elif b:
            budget_only += 1
        elif r:
            revenue_only += 1
        else:
            neither += 1
    _expect(buckets[7], (both, budget_only, revenue_only, neither) == (4067, 396, 898, 1538),
            f"presupuesto/ingresos {(both, budget_only, revenue_only, neither)}")

    def series(idx, scale):
        vals = []
        for row in movies:
            if row[idx]:
                whole, frac = row[idx].split(".")
                vals.append(int(whole) * scale + int(frac))
        return sorted(vals)

    numeric_targets = [
        (11, 1, 3, 101, 139, 400, "runtime"),
        (12, 100, 200_000, 2_000_000_000, 15_000_000_000, 38_000_000_000, "budget"),
        (13, 100, 61_800, 2_736_546_700, 43_388_886_600, 292_035_725_400, "revenue"),
        (14, 1000, 6466, 19940, 89106, 5_467_305, "popularity"),
        (16, 1000, 1000, 6539, 7846, 10000, "vote_average"),
        (17, 1, 1, 570, 7221, 32774, "vote_count"),
        (15, 10, 20, 65, 78, 100, "user_score"),
    ]
    for idx, scale, vmin, vmed, vp95, vmax, label in numeric_targets:
        if label == "runtime":
            vals = sorted(int(row[idx]) for row in movies if row[idx])
        elif label == "vote_count":
            vals = sorted(int(row[idx]) for row in movies if row[idx])
        else:
            vals = series(idx, scale)
        _expect(
            buckets[7],
            vals and vals[0] == vmin and percentile(vals, 50) == vmed and percentile(vals, 95) == vp95 and vals[-1] == vmax,
            f"{label} {vals[0] if vals else None} {percentile(vals, 50) if vals else None} {percentile(vals, 95) if vals else None} {vals[-1] if vals else None}",
        )
    matched = 0
    scored = 0
    for row in movies:
        if row[15] and row[16]:
            scored += 1
            whole, frac = row[16].split(".")
            tenths = (int(whole) * 1000 + int(frac) + 50) // 100
            if f"{tenths // 10}.{tenths % 10}" == row[15]:
                matched += 1
    _expect(buckets[7], scored and near(matched / scored, 0.40), f"correlación de scores {matched}/{scored}")
    _expect(buckets[7], all(row[18] == "false" and row[19] == "false" for row in movies), "adult/video")

    dates = [date.fromisoformat(row[10]) for row in movies]
    _expect(buckets[7], min(dates) == date(1902, 4, 17) and max(dates) == date(2023, 8, 2), "rango de estreno")
    buckets_n = [
        sum(1 for d in dates if d < date(2000, 1, 1)),
        sum(1 for d in dates if date(2000, 1, 1) <= d <= date(2009, 12, 31)),
        sum(1 for d in dates if date(2010, 1, 1) <= d <= date(2019, 12, 31)),
        sum(1 for d in dates if d >= date(2020, 1, 1)),
    ]
    _expect(buckets[7], buckets_n == [272, 1926, 3176, 1525], f"décadas {buckets_n}")

    def lengths(idx):
        return sorted(len(row[idx]) for row in movies if row[idx])

    for idx, vmin, vmed, vp95, vmax, label in (
        (2, 1, 14, 37, 86, "title"),
        (3, 1, 14, 37, 86, "original_title"),
        (7, 3, 32, 70, 248, "tagline"),
        (5, 39, 232, 529, 1445, "overview"),
        (6, 44, 2883, 2991, 3000, "plot"),
        (20, 16, 38, 66, 267, "homepage"),
    ):
        vals = lengths(idx)
        p95 = percentile(vals, 95)
        ok = near(vals[0], vmin) and near(percentile(vals, 50), vmed) and near(p95, vp95) and near(vals[-1], vmax)
        _expect(buckets[7], ok, f"longitud {label} {vals[0]} {percentile(vals, 50)} {p95} {vals[-1]}")
    plots = [row[6] for row in movies]
    _expect(buckets[7], near(sum(1 for p in plots if len(p) == 3000), 416), "tramas en el tope")
    _expect(buckets[7], near(sum(1 for p in plots if len(p) < 500), 1180), "tramas cortas")
    _expect(buckets[7], near(sum(1 for p in plots if "\n" in p) / len(plots), 0.79), "saltos de línea")
    overs = [row[5] for row in movies if row[5]]
    _expect(buckets[7], near(sum(1 for p in overs if '"' in p), 316), "comillas en overview")
    diffs = sum(1 for row in movies if row[2] != row[3])
    _expect(buckets[7], near(diffs, 1091), f"títulos distintos {diffs}")
    non_en_diffs = sum(1 for row in movies if row[2] != row[3] and row[4] != "en")
    _expect(buckets[7], non_en_diffs == diffs, "un título en inglés difiere de su original")
    imdb_rows = [row[1] for row in movies if row[1]]
    eight = sum(1 for value in imdb_rows if len(value) == 10)
    _expect(buckets[7], near(eight / len(imdb_rows), 0.15), f"imdb de 8 dígitos {eight}")
    homes = [row[20] for row in movies if row[20]]
    https = sum(1 for value in homes if value.startswith("https://"))
    _expect(buckets[7], near(https / len(homes), 0.43), f"https {https}/{len(homes)}")
    mids = sorted(int(row[0]) for row in movies)
    _expect(buckets[7], mids[0] == 11 and mids[-1] == 1_059_999 and near(percentile(mids, 10), 8055) and near(percentile(mids, 50), 239566) and near(percentile(mids, 90), 757860),
            f"movie_id {mids[0]} {percentile(mids, 10)} {percentile(mids, 50)} {percentile(mids, 90)} {mids[-1]}")
    kids = sorted(int(row[0]) for row in data["keyword"])
    cids = sorted(int(row[0]) for row in data["collection"])
    _expect(buckets[7], kids[0] == 30 and kids[-1] == 382027 and any(kids[i + 1] - kids[i] > 1 for i in range(len(kids) - 1)), "keyword_id")
    _expect(buckets[7], cids[0] == 10 and cids[-1] == 1_800_171 and any(cids[i + 1] - cids[i] > 1 for i in range(len(cids) - 1)), "collection_id")
    sizes = sorted(Counter(row[1] for row in data["movie_collection"]).values())
    _expect(buckets[7], sizes and sizes[0] >= 1 and near(sizes[-1], 17) and near(percentile(sizes, 50), 2), f"tamaños de colección {sizes[0]} {percentile(sizes, 50) if sizes else None} {sizes[-1] if sizes else None}")

    kw_names = Counter(row[1] for row in data["keyword"])
    _expect(buckets[8], sum(1 for n in kw_names.values() if n == 2) == 18 and not any(n > 2 for n in kw_names.values()), "keywords homónimas")
    _expect(buckets[8], len({row[0] for row in data["keyword"]}) == len(data["keyword"]), "keyword_id con dos nombres")
    col_names = Counter(row[1] for row in data["collection"])
    _expect(buckets[8], sum(1 for n in col_names.values() if n == 2) == 1 and not any(n > 2 for n in col_names.values()), "colecciones homónimas")
    by_col = defaultdict(list)
    for row in data["movie_collection"]:
        by_col[row[1]].append(row)
    divergent = 0
    for rows in by_col.values():
        if len({row[2] for row in rows}) > 1 or len({row[3] for row in rows}) > 1:
            divergent += 1
        elif len(rows) > 1 and (len({row[2] for row in rows}) != 1 or len({row[3] for row in rows}) != 1):
            buckets[8].append("rutas de colección incoherentes")
    _expect(buckets[8], divergent == 4, f"colecciones con rutas distintas: {divergent}")
    _expect(buckets[8], "Guadaloupe" in country_name.values() and lang_counts["cn"] == 27, "Guadaloupe o cn")
    company_names = {row[1] for row in data["production_company"]}
    variants = 0
    for name in company_names:
        if name.endswith(" Pictures") and name[:-9] in company_names:
            variants += 1
        if name.endswith(" Ltd.") and name[:-5] in company_names:
            variants += 1
    _expect(buckets[8], 20 <= variants <= 60, f"variantes de compañía: {variants}")

    movie_fields = defaultdict(dict)
    for row in data["movie_enrichment"]:
        movie_fields[row[0]][row[1]] = row[2]
    code_counts = Counter((row[1], row[2] if not row[2].startswith("wikipedia_infobox_fx:") else "FX") for row in data["movie_enrichment"])
    expected_codes = {
        ("plot", "wikipedia_plot_2026-11-12"): 3635,
        ("plot", "wikipedia_plot_2026-11-13"): 1768,
        ("plot", "tmdb_overview"): 1065,
        ("plot", "unverified"): 429,
        ("plot", "tmdb_metadata_summary"): 1,
        ("plot", "tmdb_overview_translated:zh-CN"): 1,
        ("user_score", "tmdb_api_2026-10-22"): 6886,
        ("user_score", "tmdb_api_fallback_doc_vote_average"): 8,
        ("homepage", "wikidata"): 1293,
        ("homepage", "tmdb_api_2026-10-22"): 234,
        ("revenue", "tmdb_api_2026-10-22"): 572,
        ("revenue", "wikipedia_infobox"): 346,
        ("revenue", "wikidata"): 64,
        ("revenue", "FX"): 22,
        ("budget", "tmdb_api_2026-10-22"): 372,
        ("budget", "wikipedia_infobox"): 199,
        ("budget", "FX"): 65,
        ("budget", "wikidata"): 63,
        ("budget", "wikipedia_infobox_range_midpoint"): 15,
        ("rating", "tmdb_api_2026-10-22"): 240,
        ("rating", "wikidata"): 31,
        ("production_companies", "tmdb_api_2026-10-22"): 86,
        ("production_companies", "wikidata"): 7,
        ("production_countries", "tmdb_api_2026-10-22"): 59,
        ("production_countries", "wikidata"): 11,
    }
    for field, count in (
        ("tagline", 433), ("keywords", 315), ("belongs_to_collection", 169),
        ("vote_average", 57), ("vote_count", 57), ("runtime", 29),
        ("backdrop_path", 27), ("imdb_id", 16), ("spoken_languages", 15),
        ("cast", 7), ("poster_path", 4), ("genres", 3), ("overview", 2),
    ):
        expected_codes[(field, "tmdb_api_2026-10-22")] = count
    for key, count in expected_codes.items():
        _expect(buckets[7], code_counts[key] == count, f"código {key} {code_counts[key]} vs {count}")
    fx_currencies = Counter()
    rel = {
        "budget": lambda row: row[12] != "",
        "revenue": lambda row: row[13] != "",
        "homepage": lambda row: row[20] != "",
        "tagline": lambda row: row[7] != "",
        "rating": lambda row: row[9] != "",
        "vote_average": lambda row: row[16] != "",
        "vote_count": lambda row: row[17] != "",
        "runtime": lambda row: row[11] != "",
        "backdrop_path": lambda row: row[22] != "",
        "imdb_id": lambda row: row[1] != "",
        "poster_path": lambda row: row[21] != "",
        "overview": lambda row: row[5] != "",
        "user_score": lambda row: row[15] != "",
        "plot": lambda row: row[6] != "",
    }
    bridge_nonempty = {
        "keywords": "movie_keyword", "genres": "movie_genre", "cast": "movie_cast",
        "production_companies": "movie_production_company",
        "production_countries": "movie_production_country",
        "spoken_languages": "movie_spoken_language",
        "belongs_to_collection": "movie_collection",
    }
    present = {name: {row[0] for row in rows} for name, rows in (
        ("movie_keyword", data["movie_keyword"]), ("movie_genre", data["movie_genre"]),
        ("movie_cast", data["movie_cast"]), ("movie_production_company", data["movie_production_company"]),
        ("movie_production_country", data["movie_production_country"]),
        ("movie_spoken_language", data["movie_spoken_language"]),
        ("movie_collection", data["movie_collection"]),
    )}
    for mid, fields in movie_fields.items():
        row = by_id[mid]
        for field in fields:
            if field in rel and not rel[field](row):
                buckets[9].append(f"{field} enriquecido sin dato")
                break
            if field in bridge_nonempty and mid not in present[bridge_nonempty[field]]:
                buckets[9].append(f"{field} enriquecido sin relación")
                break
            code = fields[field]
            match = FX_RE.match(code)
            if match:
                cur, year = match.group(1), int(match.group(2))
                fx_currencies[cur] += 1
                release = date.fromisoformat(row[10]).year
                if cur not in set(FX_CURS) or year != release or not 1972 <= year <= 2022:
                    buckets[9].append(f"fx incoherente {code} estreno {release}")
                    break
        if len(buckets[9]) >= 15:
            break
    _expect(buckets[9], fx_currencies["EUR"] > fx_currencies["GBP"] > 0 and fx_currencies["GBP"] == max(n for c, n in fx_currencies.items() if c != "EUR"),
            f"monedas fx {fx_currencies.most_common(4)}")
    cents_bad = 0
    for row in movies:
        fields = movie_fields[row[0]]
        if row[12] and not row[12].endswith(".00") and not fields.get("budget", "").startswith("wikipedia_infobox_fx:"):
            cents_bad += 1
        if row[13] and not row[13].endswith(".00") and not fields.get("revenue", "").startswith("wikipedia_infobox_fx:"):
            cents_bad += 1
    money_n = sum(1 for row in movies if row[12]) + sum(1 for row in movies if row[13])
    money_int = sum(1 for row in movies if row[12].endswith(".00")) + sum(1 for row in movies if row[13].endswith(".00"))
    _expect(buckets[7], cents_bad == 0 and money_int > money_n / 2, f"céntimos fuera de fx o no mayoritarios ({money_int}/{money_n})")

    # --- New checks 11-16 (task §5) ---
    buckets.update({i: [] for i in range(11, 17)})

    # 11. No movie holds two keywords of the same name.
    kw_id_to_name = {row[0]: row[1] for row in data["keyword"]}
    kw_by_movie = defaultdict(list)
    for row in data["movie_keyword"]:
        kw_by_movie[row[0]].append(kw_id_to_name[row[1]])
    clash = 0
    for mid, names in kw_by_movie.items():
        if len(names) != len(set(names)):
            clash += 1
            if len(buckets[11]) < 5:
                buckets[11].append(f"película {mid} tiene keywords homónimas")
    _expect(buckets[11], clash == 0, f"{clash} películas con keywords del mismo nombre")

    # 12. Spearman correlations within ±0.15.
    def col_series(key):
        out = []
        for row in movies:
            mid = int(row[0])
            if key == "id":
                out.append(float(mid)); continue
            if key == "rel":
                out.append(date.fromisoformat(row[10]).toordinal()); continue
            if key == "vc":
                out.append(float(row[17]) if row[17] else None); continue
            if key == "rev":
                if not row[13]: out.append(None); continue
                w, f = row[13].split("."); out.append(float(int(w) * 100 + int(f))); continue
            if key == "bud":
                if not row[12]: out.append(None); continue
                w, f = row[12].split("."); out.append(float(int(w) * 100 + int(f))); continue
            if key == "plot":
                out.append(float(len(row[6]))); continue
            if key == "ov":
                out.append(float(len(row[5])) if row[5] else None); continue
            if key == "rt":
                out.append(float(row[11]) if row[11] else None); continue
            if key == "pop":
                w, f = row[14].split("."); out.append(float(int(w) * 1000 + int(f))); continue
            if key == "us":
                out.append(float(row[15]) if row[15] else None); continue
            if key == "va":
                out.append(float(row[16]) if row[16] else None); continue
            if key == "tl":
                out.append(float(len(row[2]))); continue
            if key == "kw":
                out.append(float(sum(1 for r in data["movie_keyword"] if r[0] == row[0]))); continue
            if key == "cast":
                out.append(float(sum(1 for r in data["movie_cast"] if r[0] == row[0]))); continue
            raise KeyError(key)
        return out

    # Precompute cast/kw degrees more efficiently
    kw_deg = defaultdict(int)
    for row in data["movie_keyword"]:
        kw_deg[row[0]] += 1
    cast_deg = defaultdict(int)
    for row in data["movie_cast"]:
        cast_deg[row[0]] += 1

    series = {}
    for key in list(SPEARMAN_ID) + ["id"]:
        if key == "kw":
            series[key] = [float(kw_deg.get(row[0], 0)) for row in movies]
        elif key == "cast":
            series[key] = [float(cast_deg.get(row[0], 0)) for row in movies]
        else:
            series[key] = col_series(key)

    def paired(a, b):
        xs, ys = [], []
        for x, y in zip(series[a], series[b]):
            if x is None or y is None:
                continue
            xs.append(x); ys.append(y)
        return xs, ys

    corr_rows = []
    for key, target in SPEARMAN_ID.items():
        xs, ys = paired("id", key)
        got = spearman(xs, ys)
        corr_rows.append(("id", key, target, got))
        if abs(got - target) > 0.15:
            buckets[12].append(f"id~{key}: {got:.3f} vs {target} (±0.15)")
    for (a, b), target in SPEARMAN_PAIRS.items():
        xs, ys = paired(a, b)
        got = spearman(xs, ys)
        corr_rows.append((a, b, target, got))
        if abs(got - target) > 0.15:
            buckets[12].append(f"{a}~{b}: {got:.3f} vs {target} (±0.15)")
        if abs(got) > 0.999:
            buckets[12].append(f"{a}~{b}: correlación degenerada {got:.3f}")
    # stash for README
    stats.append({"_correlations": corr_rows})

    # 13. Variety of texts
    titles = [row[2] for row in movies]
    taglines = [row[7] for row in movies if row[7]]
    overs = [row[5] for row in movies if row[5]]
    plots = [row[6] for row in movies]
    homes = [row[20] for row in movies if row[20]]
    _expect(buckets[13], len(set(titles)) >= 6700, f"títulos distintos {len(set(titles))}")
    _expect(buckets[13], max(Counter(titles).values()) <= 4, f"título más repetido {max(Counter(titles).values())}")
    _expect(buckets[13], len(set(plots)) == len(plots), f"plots distintos {len(set(plots))}/{len(plots)}")
    _expect(buckets[13], len(set(overs)) >= len(overs) - 2, f"overviews distintos {len(set(overs))}/{len(overs)}")
    _expect(buckets[13], len(set(taglines)) / max(1, len(taglines)) >= 0.99, f"taglines distintas {len(set(taglines))}/{len(taglines)}")
    _expect(buckets[13], len(set(homes)) / max(1, len(homes)) >= 0.98, f"homepages distintas {len(set(homes))}/{len(homes)}")

    # 14. Cell contents (commas, quotes, newlines) ±5%
    def count_chars(rows, idx, pred):
        return sum(1 for row in rows if row[idx] and pred(row[idx]))
    # title
    t_comma = sum(1 for row in movies if "," in row[2])
    t_quote = sum(1 for row in movies if '"' in row[2])
    t_nl = sum(1 for row in movies if "\n" in row[2])
    _expect(buckets[14], near(t_comma, 87, 0.05), f"title coma {t_comma}")
    _expect(buckets[14], near(t_quote, 1, 0.05) or t_quote == 1, f"title comilla {t_quote}")
    _expect(buckets[14], t_nl == 0, f"title newline {t_nl}")
    # tagline
    tg = [row[7] for row in movies if row[7]]
    _expect(buckets[14], near(sum(1 for t in tg if "," in t), 666, 0.05), "tagline coma")
    _expect(buckets[14], near(sum(1 for t in tg if '"' in t), 12, 0.05), "tagline comilla")
    _expect(buckets[14], sum(1 for t in tg if "\n" in t) == 0, "tagline newline")
    # overview
    ov = [row[5] for row in movies if row[5]]
    _expect(buckets[14], near(sum(1 for t in ov if "," in t), 5695, 0.05), "overview coma")
    _expect(buckets[14], near(sum(1 for t in ov if '"' in t), 316, 0.05), "overview comilla")
    _expect(buckets[14], sum(1 for t in ov if "\n" in t) == 0, "overview newline")
    # plot
    pl = [row[6] for row in movies]
    _expect(buckets[14], near(sum(1 for t in pl if "," in t), 6806, 0.05), "plot coma")
    _expect(buckets[14], near(sum(1 for t in pl if '"' in t), 3133, 0.05), "plot comilla")
    _expect(buckets[14], near(sum(1 for t in pl if "\n" in t), 5480, 0.05), "plot newline")
    _expect(buckets[14], near(sum(1 for t in pl if '"' in t and "\n" in t), 3010, 0.05), "plot comilla+newline")
    kw_comma = sum(1 for row in data["keyword"] if "," in row[1])
    co_comma = sum(1 for row in data["production_company"] if "," in row[1])
    _expect(buckets[14], near(kw_comma, 157, 0.05), f"keyword coma {kw_comma}")
    _expect(buckets[14], near(co_comma, 26, 0.05), f"company coma {co_comma}")

    # 15. Person names Latin script only (diacritics allowed, ~5 % of names)
    non_latin_people = 0
    with_marks = 0
    for row in data["person"]:
        letters = [ch for ch in row[1] if ch not in " '-."]
        if any(not unicodedata.name(ch, "").startswith("LATIN") for ch in letters):
            non_latin_people += 1
        if not row[1].isascii():
            with_marks += 1
    _expect(buckets[15], near(with_marks / max(1, len(data["person"])), 0.05), f"personas con diacríticos {with_marks}")
    _expect(buckets[15], non_latin_people == 0, f"personas no latinas {non_latin_people}")

    # 16. imdb non-sequential; homepage .example only
    imdb_nums = []
    for row in movies:
        if row[1]:
            imdb_nums.append(int(row[1][2:]))
    imdb_nums.sort()
    consec = sum(1 for i in range(len(imdb_nums) - 1) if imdb_nums[i + 1] - imdb_nums[i] == 1)
    _expect(buckets[16], consec < 100, f"imdb consecutivos {consec}")
    _expect(buckets[16], imdb_nums and imdb_nums[0] >= 417 and imdb_nums[-1] <= 35_725_827, f"imdb rango {imdb_nums[0]}..{imdb_nums[-1]}")
    bad_home = [row[20] for row in movies if row[20] and ".example" not in row[20]]
    _expect(buckets[16], not bad_home, f"homepage sin .example: {bad_home[:3]}")

    # 17. Every title token (digits aside) is a word of the generator's title list.
    buckets.update({17: [], 18: []})
    bad_tokens = Counter(tok for row in movies for tok in title_tokens(row[2]) if tok not in TITLE_WORDS)
    _expect(buckets[17], not bad_tokens, f"palabras de título fuera de la lista: {bad_tokens.most_common(5)}")
    ot_bad = Counter(tok for row in movies if row[3] == row[2] for tok in title_tokens(row[3]) if tok not in TITLE_WORDS)
    _expect(buckets[17], not ot_bad, f"original_title fuera de la lista: {ot_bad.most_common(5)}")

    # 18. Prose: no quote or line break glued to letters on both sides; quotes paired.
    for idx, label in ((7, "tagline"), (5, "overview"), (6, "plot")):
        cells = [row[idx] for row in movies if row[idx]]
        glued = [c for c in cells if PROSE_BAD.search(c)]
        _expect(buckets[18], not glued, f"{label}: {len(glued)} celdas con comilla o salto pegado a letras")
        odd = [c for c in cells if c.count('"') % 2]
        _expect(buckets[18], not odd, f"{label}: {len(odd)} celdas con comillas sin pareja")

    return _report(buckets, stats)


def _report(buckets, stats):
    lines = []
    summaries = {
        1: "Existen los 20 archivos, con la cabecera de la sección 8.2 y menos de 50 MB.",
        2: "UTF-8 sin BOM, sin CR, y todas las filas tienen los mismos campos al leerlas como RFC 4180 (sección 8.3).",
        3: "Claves primarias y restricciones UNIQUE sin duplicados.",
        4: "Claves foráneas íntegras y ninguna entidad huérfana.",
        5: "Restricciones de la sección 12, posiciones consecutivas desde 1 y orden de la sección 8.4.",
        6: "Columnas obligatorias sin nulos y ningún texto vacío: el campo vacío y sin comillas es NULL (sección 8.3).",
        7: "Catálogos y frecuencias exactos; el resto del perfil, dentro de ±3 %.",
        8: "Están los defectos de la sección 8.6 y no hay repeticiones dentro de una película ni un keyword_id con dos nombres.",
        9: "Cada fila de movie_enrichment corresponde a un dato presente, y los códigos fx cuadran con el estreno.",
        11: "Ninguna película tiene dos keywords del mismo nombre.",
        12: "Correlaciones de Spearman (tarea §4.1 y §4.2) dentro de ±0.15; ningún par en ±1.00.",
        13: "Variedad de títulos, tagline, overview, plot y homepage (tarea §4.3, §4.4, §4.8).",
        14: "Contenido de celdas (comas, comillas, saltos) según la tarea §4.5 (±5 %).",
        15: "Todos los nombres de persona están en alfabeto latino; un 5 % lleva diacríticos.",
        16: "imdb_id no secuenciales (rango tt0000417..tt35725827) y homepage solo con dominios .example.",
        17: "Cada palabra de los títulos (salvo números) está en la lista de palabras del generador.",
        18: "Prosa sin comillas ni saltos de línea pegados a letras por ambos lados, y comillas emparejadas.",
    }
    ok = True
    for number in list(range(1, 10)) + list(range(11, 19)):
        passed = not buckets.get(number)
        ok = ok and passed
        lines.append(f"{number}. {'PASS' if passed else 'FAIL'}. {summaries[number]}")
        for detail in buckets.get(number, []):
            lines.append(f"   - {detail}")
    return ok, lines, stats




def write_readme(directory: Path, lines: list[str], stats: list[dict]) -> None:
    corr = None
    file_stats = []
    for item in stats:
        if isinstance(item, dict) and "_correlations" in item:
            corr = item["_correlations"]
        else:
            file_stats.append(item)
    body = [
        "# Datos sintéticos de entrada de ElastiFlix",
        "",
        "Estos archivos son **sintéticos**. No proceden del catálogo original, no usan",
        "títulos de películas reales, nombres de personas reales ni nombres de compañías",
        "reales, y las sinopsis están generadas. Los catálogos cerrados (estado, rating,",
        "idiomas, países, géneros, idiomas hablados y campos de enrichment) sí usan los",
        "valores exactos del contrato (secciones 8.2 y 8.5 del diseño).",
        "",
        "## Semilla",
        "",
        "```python",
        f"SEED = {SEED}",
        "```",
        "",
        "El generador solo usa la biblioteca estándar de Python 3.12. Cada subsistema",
        "toma su propia secuencia a partir de esa semilla; no interviene la fecha, la",
        "hora, el orden de un `set` ni la red.",
        "",
        "## Regenerar",
        "",
        "Desde la raíz del repositorio:",
        "",
        "```bash",
        "python3 raw_data/generate_raw_data.py",
        "python3 raw_data/generate_raw_data.py --out /tmp/raw_data_check",
        "python3 raw_data/generate_raw_data.py --validate",
        "```",
        "",
        "Sin `--out`, reescribe los 20 CSV en este directorio. Con `--out <dir>`, escribe",
        "ahí. `--validate` genera dos veces, comprueba el contrato (secciones 8.2, 8.3,",
        "8.4 y 8.6 del diseño, más las correlaciones y la variedad de la tarea de",
        "regeneración) y vuelve a escribir este README. `created_at` y `updated_at` no",
        "están en los archivos: los asigna PostgreSQL.",
        "",
        "## Excepciones documentadas",
        "",
        "- **Longitud mínima de `homepage`:** 16 caracteres (no 15). Las URL con dominio",
        "  reservado `.example` no pueden ser más cortas que `http://a.example`.",
        "- **`original_title` en alfabeto no latino:** 666 películas (todas las de idiomas",
        "  con script propio bajo las frecuencias congeladas de `LANGS`). El objetivo",
        "  informal de ~770 era incompatible con esas frecuencias; el total de títulos",
        "  que difieren del `title` se mantiene en 1,091 (666 no latinos + 425 latinos",
        "  en otro idioma). Los 425 latinos se eligen entre idiomas con léxico propio",
        "  en el generador (fr, es, it, de, pt, sv, da, no, nb, nl, pl); en el resto de",
        "  idiomas latinos `original_title` coincide con `title`.",
        "- **Longitudes de `tagline`:** se conservan mínimo (3), mediana (32), P95 (70) y",
        "  máximo (248), pero la cola baja se ha desplazado: ninguna tagline mide entre 4",
        "  y 13 caracteres, porque con frases reales no caben ~900 taglines distintas tan",
        "  cortas (la tarea exige al menos un 99 % distintas).",
        "",
        "## Cómo se generan los textos",
        "",
        "- **Títulos:** palabras inglesas reales de listas curadas en el generador",
        "  (`TITLE_WORDS`), combinadas con una gramática de plantillas (adjetivo + nombre,",
        "  «The … of the …», «Nombre: subtítulo», números, etc.). La longitud se alcanza",
        "  eligiendo palabras y estructuras, nunca recortando ni rellenando. Una lista de",
        "  bloqueo (`TITLE_BLOCK`) descarta títulos de películas reales conocidas.",
        "- **`original_title`:** palabras reales del idioma (japonés, coreano, chino,",
        "  ruso, hindi, árabe, tailandés…, y francés, español, italiano, alemán… para los",
        "  latinos), con longitud cercana a la del título.",
        "- **Prosa (`tagline`, `overview`, `plot`):** frases completas generadas con",
        "  plantillas y huecos tipados (personajes con pronombres coherentes, oficios,",
        "  lugares, objetos, sucesos, objetivos, ciudades). Las comillas solo rodean una",
        "  línea de diálogo completa y los saltos de línea solo separan frases. Las 416",
        "  tramas cortadas en 3,000 caracteres terminan en un límite de palabra.",
        "- **Personas:** nombres y apellidos reales de muchas culturas combinados al azar",
        "  (`PERSON_BLOCK` evita combinaciones que coinciden con personas famosas); un 5 %",
        "  usa nombres o apellidos con diacríticos.",
        "- **Compañías, keywords y colecciones:** raíces y sufijos curados, apellidos,",
        "  sustantivos ingleses comunes en minúsculas y ciudades reales; lista de bloqueo",
        "  de compañías reales (`REAL_COMPANY_BLOCK`).",
        "",
        "## Archivos",
        "",
        "| Archivo | Filas | Bytes | SHA-256 |",
        "|---|---:|---:|---|",
    ]
    for item in file_stats:
        body.append(f"| `{item['file']}` | {item['rows']} | {item['bytes']} | `{item['sha256']}` |")
    body.extend([
        "",
        "Las filas no incluyen la cabecera. Columnas y claves: sección 8.2. Formato:",
        "sección 8.3. Orden e identificadores: sección 8.4. Defectos intencionales:",
        "sección 8.6. Orden de carga sin violar claves foráneas:",
        "`movie_status`, `content_rating`, `original_language`, `enrichment_field`,",
        "`genre`, `keyword`, `person`, `production_company`, `production_country`,",
        "`spoken_language`, `collection`, `movie`, `movie_collection`, `movie_genre`,",
        "`movie_keyword`, `movie_cast`, `movie_production_company`,",
        "`movie_production_country`, `movie_spoken_language`, `movie_enrichment`.",
        "",
        "## Validaciones",
        "",
        "Resultado de `python3 raw_data/generate_raw_data.py --validate`:",
        "",
        "```text",
        *lines,
        "```",
        "",
    ])
    if corr:
        body.extend([
            "## Correlaciones de Spearman observadas",
            "",
            "| Par | Objetivo | Observado |",
            "|---|---:|---:|",
        ])
        for a, b, target, got in corr:
            body.append(f"| `{a}` ~ `{b}` | {target:+.2f} | {got:+.3f} |")
        body.append("")
    text = "\n".join(body) + "\n"
    path = directory / "README.md"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\r", "\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera los CSV sintéticos de ElastiFlix")
    parser.add_argument("--validate", action="store_true", help="genera dos veces y comprueba el contrato")
    parser.add_argument("--out", type=Path, default=None, help="directorio de salida (por defecto: raw_data/)")
    args = parser.parse_args(argv)
    out = args.out.resolve() if args.out else Path(__file__).resolve().parent
    if not args.validate:
        generate(out)
        return 0
    log("primera ejecución")
    generate(out)
    with tempfile.TemporaryDirectory() as tmp:
        log("segunda ejecución")
        generate(Path(tmp))
        second = {
            name: _sha256((Path(tmp) / f"{name}.csv").read_bytes())
            for name in FILE_ORDER
        }
    ok, lines, stats = validate_dir(out)
    first = {item["file"].removesuffix(".csv"): item["sha256"] for item in stats if "file" in item}
    det_ok = first == second and len(first) == 20
    lines.append(
        "10. " + ("PASS" if det_ok else "FAIL")
        + ". SHA-256 idéntico en dos ejecuciones."
    )
    if not det_ok:
        lines.append("   - los CSV de las dos ejecuciones no coinciden")
    if ok and det_ok:
        write_readme(out, lines, stats)
    print("\n".join(lines))
    return 0 if ok and det_ok else 1


if __name__ == "__main__":
    sys.exit(main())
