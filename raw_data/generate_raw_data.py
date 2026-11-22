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
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

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
WORDS = (
    "brimdal", "quorven", "lixan", "mordel", "tavrin", "zelqua", "ompira",
    "fandrel", "yosket", "crivane", "pelnor", "daxium", "sovrel", "quimble",
    "ortavo", "nemblis", "harvok", "jintrel", "wexlan", "ulvora", "kalmex",
    "brontis", "fenquar", "gildove", "hexmar", "ivorel", "jorven", "kestil",
    "lomari", "mivren", "naxoli", "ostven", "prindel", "quelmar", "rovantis",
    "sulvek", "tremqa", "vornel", "xalder", "yentris", "zorvane", "astelq",
)
ALPH62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
LATIN = "bcdfghjklmnpqrstvwxyz"
ACCENTS = "áéíóúäöüàèìòùñ"
HANGUL = "".join(chr(0xAC00 + i * 53) for i in range(36))
CYR = "абвгдежзийклмнопрстуфхцчшщыэюя"
GREEK = "αβγδεζηθικλμνξοπρστυφχψω"
ARABIC = "بتثجحخدذرزسشصضطظعغفقكلمنهوي"
HIRA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほ"
CJK = "".join(chr(c) for c in range(0x4E16, 0x4E3A))
DEVAN = "कखगघचछजझटठडढतथदधनपफबभमयरलवशषस"
THAI = "กขคงจฉชซดตถทนบปผฝพฟมยรลวสห"
SCRIPTS = {
    "ja": HIRA, "ko": HANGUL, "zh": CJK, "cn": CJK, "ru": CYR, "uk": CYR,
    "hi": DEVAN, "th": THAI, "ar": ARABIC, "fa": ARABIC, "el": GREEK,
    "te": "కఖగఘచఛజఝటఠడఢణతథదధనపఫబభమయరలవశషస",
    "kn": "ಕಖಗಘಚಛಜಝಟಠಡಢಣತಥದಧನಪಫಬಭಮಯರಲವಶಷಸ",
    "km": "កខគឃងចឆជឈញដឋឌឍណតថទធនបផពភមយរលវសហ",
    "ka": "აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ",
    "kk": CYR, "gu": "કખગઘચછજઝટઠડઢણતથદધનપફબભમયરલવશષસ",
    "mk": CYR, "ta": "கஙசஞடணதநபமயரலவழளறன",
}

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


def fit_words(length: int, salt: int) -> str:
    if length < 1:
        raise ValueError(length)
    pieces: list[str] = []
    total = 0
    k = 0
    while total < length:
        w = WORDS[(salt + k) % len(WORDS)]
        k += 1
        if not pieces:
            if len(w) >= length:
                return w[:length]
            pieces.append(w)
            total = len(w)
            continue
        if total + 1 >= length:
            pieces.append("x" * (length - total))
            break
        room = length - total - 1
        if len(w) <= room:
            pieces.append(" " + w)
            total += 1 + len(w)
        else:
            pieces.append(" " + w[:room])
            break
    text = "".join(pieces)
    if len(text) < length:
        text += "x" * (length - len(text))
    return text[:length]


def fit_script(length: int, salt: int, alphabet: str) -> str:
    return "".join(alphabet[(salt + i * 7) % len(alphabet)] for i in range(length))


def fit_accented(length: int, salt: int) -> str:
    alpha = "aeiou" + ACCENTS
    chars = [alpha[(salt + i * 5) % len(alpha)] for i in range(length)]
    if not any(c in ACCENTS for c in chars):
        chars[-1] = ACCENTS[salt % len(ACCENTS)]
    return "".join(chars)


def add_newline(text: str) -> str:
    target = max(1, len(text) // 3)
    best = -1
    start = 0
    while True:
        j = text.find(" ", start)
        if j < 0 or j >= len(text) - 1:
            break
        if best < 0 or abs(j - target) < abs(best - target):
            best = j
        start = j + 1
    if best < 0:
        mid = len(text) // 2
        return text[:mid] + "\n" + text[mid + 1:]
    return text[:best] + "\n" + text[best + 1:]


def add_quote(text: str) -> str:
    for i in range(len(text) // 2, len(text)):
        if text[i].isalpha():
            return text[:i] + '"' + text[i + 1:]
    return text[:-1] + '"'


def make_url(length: int, https: bool, salt: int) -> str:
    prefix = "https://" if https else "http://"
    rest = length - len(prefix)
    alpha = "abcdefghijklmnopqrstuvwxyz0123456789"
    chars = [alpha[(salt + i * 13) % len(alpha)] for i in range(rest)]
    if rest >= 4:
        chars[rest // 2] = "."
    return prefix + "".join(chars)


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
        if len(SCRIPTS.get(code, "")) < 2:
            raise RuntimeError(f"script {code}")


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

    dates = _dates(rng_for("dates"))
    rng_for("dates-assign").shuffle(dates)

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

    budgets = [(v // 100) * 100 for v in anchored_ints(4463, 200_000, 2_000_000_000, 15_000_000_000, 38_000_000_000)]
    revenues = [(v // 100) * 100 for v in anchored_ints(4965, 61_800, 2_736_546_700, 43_388_886_600, 292_035_725_400)]
    popularity = anchored_ints(N_MOVIES, 6466, 19940, 89106, 5_467_305)
    runtimes = anchored_ints(6893, 3, 101, 139, 400)
    vote_avg = anchored_ints(6894, 1000, 6539, 7846, 10000)
    vote_cnt = anchored_ints(6894, 1, 570, 7221, 32774)
    user_vals = anchored_ints(6894, 20, 65, 78, 100)

    b_movies = sorted(both | budget_only)
    r_movies = sorted(both | revenue_only)
    v_movies = [i for i in range(N_MOVIES) if i not in vote_null]
    rt_movies = [i for i in range(N_MOVIES) if i not in runtime_null]
    for mi, value in zip(b_movies, budgets):
        movies[mi]["budget"] = value
    for mi, value in zip(r_movies, revenues):
        movies[mi]["revenue"] = value
    for mi in range(N_MOVIES):
        movies[mi]["budget"] = movies[mi].get("budget")
        movies[mi]["revenue"] = movies[mi].get("revenue")
        movies[mi]["popularity"] = popularity[mi]
        movies[mi]["lang"] = lang_bag[mi]
        movies[mi]["rating"] = rating_bag[mi]
        movies[mi]["release"] = dates[mi]
        movies[mi]["status"] = "Released"
    for mi, value in zip(rt_movies, runtimes):
        movies[mi]["runtime"] = value
    for mi, va, vc, us in zip(v_movies, vote_avg, vote_cnt, user_vals):
        movies[mi]["vote_average"] = va
        movies[mi]["vote_count"] = vc
        movies[mi]["user_score"] = us
    desired = [round_tenths(movies[mi]["vote_average"]) for mi in v_movies]
    current = [movies[mi]["user_score"] for mi in v_movies]
    tuned = tune_matches(desired, current, 2758)
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
    for name, (total, zeros, med, p95, mx, alpha, beta) in degree_specs.items():
        seq = build_degrees(N_MOVIES, total, zeros, med, p95, mx, alpha, beta)
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
        overview_null, backdrop_null,
    )

    log("escritura")
    _write_all(
        out_dir, movies, genre_of, keyword_of, person_of, company_of,
        country_of, spoken_of, collection_of, obs_poster, obs_backdrop, enrich,
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


def _person_names(n: int) -> list[str]:
    scripts = [HANGUL, CYR, GREEK, ARABIC, HIRA, CJK]
    names = []
    for i in range(n):
        bucket = i % 10
        if bucket == 0:
            names.append(encode(i, LATIN) + " " + encode(i, ACCENTS))
        elif bucket <= 6:
            alpha = scripts[bucket - 1]
            names.append(encode(i, alpha) + " " + encode(i + 17, alpha))
        else:
            names.append(encode(i, LATIN) + " " + encode(i + 91, LATIN))
    if len(set(names)) != n:
        raise RuntimeError("person names collide")
    return names


def _company_names(n: int = 8061) -> list[str]:
    names: list[str] = [""] * n
    for i in range(36):
        stem = "C" + encode(i, LATIN)
        names[i] = stem
        names[36 + i] = stem + (" Pictures" if i < 18 else " Ltd.")
    scripts = [HANGUL, CYR, ARABIC, HIRA, CJK]
    for i in range(72, n):
        bucket = i % 8
        if bucket == 0:
            names[i] = encode(i, LATIN) + encode(i, ACCENTS)
        elif bucket <= 5:
            names[i] = encode(i, scripts[bucket - 1])
        else:
            names[i] = "C" + encode(i, LATIN)
    if len(set(names)) != n:
        raise RuntimeError("company names collide")
    return names


def _keyword_names(n: int = 11762) -> list[str]:
    names = ["K" + encode(i, LATIN) for i in range(n)]
    for i in range(18):
        names[1000 + i] = names[i]
    counts = Counter(names)
    if sum(1 for value in counts.values() if value == 2) != 18 or any(value > 2 for value in counts.values()):
        raise RuntimeError("keyword name defects")
    return names


def _collection_names(n: int = 1039) -> list[str]:
    names = ["Cycle " + encode(i, LATIN) for i in range(n)]
    names[1] = names[0]
    counts = Counter(names)
    if sum(1 for value in counts.values() if value == 2) != 1 or any(value > 2 for value in counts.values()):
        raise RuntimeError("collection name defect")
    return names


def _texts(movies, imdb_null, homepage_null, tagline_null, poster_null, overview_null, backdrop_null) -> None:
    title_len = anchored_ints(N_MOVIES, 1, 14, 37, 86)
    plot_len = plot_lengths()
    if sum(1 for n in plot_len if n < 500) != 1180 or sum(1 for n in plot_len if n == 3000) != 416:
        raise RuntimeError("plot length shape")
    tag_len = anchored_ints(5711, 3, 32, 70, 248)
    ov_len = anchored_ints(6897, 39, 232, 529, 1445)
    hp_len = anchored_ints(5095, 15, 38, 66, 267)
    non_en = [i for i in range(N_MOVIES) if movies[i]["lang"] != "en"]
    non_latin = [i for i in non_en if movies[i]["lang"] in NON_LATIN]
    latin_non_en = [i for i in non_en if movies[i]["lang"] not in NON_LATIN]
    if len(non_en) != 1232 or len(non_latin) != 666:
        raise RuntimeError(f"language split non-en={len(non_en)} non-latin={len(non_latin)}")
    differ = set(non_latin) | set(latin_non_en[:425])
    if len(differ) != 1091:
        raise RuntimeError(f"title diffs {len(differ)}")
    newline_set = set(rng_for("newlines").sample(range(N_MOVIES), 5450))
    quote_set = set(rng_for("quotes").sample([i for i in range(N_MOVIES) if i not in overview_null], 316))
    https_set = set(rng_for("https").sample([i for i in range(N_MOVIES) if i not in homepage_null], 2191))
    eight = set(rng_for("imdb8").sample([i for i in range(N_MOVIES) if i not in imdb_null], 1033))
    tag_movies = [i for i in range(N_MOVIES) if i not in tagline_null]
    ov_movies = [i for i in range(N_MOVIES) if i not in overview_null]
    hp_movies = [i for i in range(N_MOVIES) if i not in homepage_null]
    for n, mi in enumerate(tag_movies):
        movies[mi]["tag_len"] = tag_len[n]
    for n, mi in enumerate(ov_movies):
        movies[mi]["ov_len"] = ov_len[n]
    for n, mi in enumerate(hp_movies):
        movies[mi]["hp_len"] = hp_len[n]
    seq7 = 1_000_000
    seq8 = 10_000_000
    for mi in range(N_MOVIES):
        movie = movies[mi]
        length = title_len[mi]
        title = fit_words(length, mi * 3 + 1)
        if mi in differ:
            if movie["lang"] in NON_LATIN:
                original = fit_script(length, mi * 5 + 9, SCRIPTS[movie["lang"]])
            else:
                original = fit_accented(length, mi * 5 + 9)
            if original == title:
                original = ("é" if title != "é" else "á") if length == 1 else original[:-1] + ("q" if title[-1] != "q" else "z")
        else:
            original = title
        if len(title) != length or len(original) != length or (mi in differ and original == title):
            raise RuntimeError(f"title {mi}")
        movie["title"] = title
        movie["original_title"] = original
        plot = fit_words(plot_len[mi], mi * 11 + 4)
        if plot_len[mi] == 3000 and plot[-1] in " .!?\n":
            plot = plot[:-1] + "m"
        if mi in newline_set:
            plot = add_newline(plot)
        if len(plot) != plot_len[mi] or ("\n" in plot) != (mi in newline_set):
            raise RuntimeError(f"plot {mi}")
        movie["plot"] = plot
        if mi in overview_null:
            movie["overview"] = None
        else:
            text = fit_words(movie["ov_len"], mi * 13 + 2)
            if mi in quote_set:
                text = add_quote(text)
            if len(text) != movie["ov_len"] or ('"' in text) != (mi in quote_set):
                raise RuntimeError(f"overview {mi}")
            movie["overview"] = text
        movie["tagline"] = None if mi in tagline_null else fit_words(movie["tag_len"], mi * 17 + 6)
        if mi in homepage_null:
            movie["homepage"] = None
        else:
            movie["homepage"] = make_url(movie["hp_len"], mi in https_set, mi * 19 + 8)
            if len(movie["homepage"]) != movie["hp_len"]:
                raise RuntimeError(f"homepage {mi}")
        movie["poster"] = None if mi in poster_null else path_from(mi + 1)
        movie["backdrop"] = None if mi in backdrop_null else path_from(1_000_000 + mi)
        if mi in imdb_null:
            movie["imdb"] = None
        elif mi in eight:
            movie["imdb"] = f"tt{seq8:08d}"
            seq8 += 1
        else:
            movie["imdb"] = f"tt{seq7:07d}"
            seq7 += 1


def _opt(value: object, fmt=str) -> str:
    return "" if value is None else fmt(value)


def _write_all(
    out_dir, movies, genre_of, keyword_of, person_of, company_of, country_of,
    spoken_of, collection_of, obs_poster, obs_backdrop, enrich,
) -> None:
    person_name = _person_names(95050)
    company_name = _company_names()
    keyword_name = _keyword_names()
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
        (20, 15, 38, 66, 267, "homepage"),
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
    return _report(buckets, stats)


def _report(buckets, stats):
    lines = []
    summaries = {
        1: "Existen los 20 archivos, con la cabecera de la sección 6 y menos de 50 MB.",
        2: "UTF-8 sin BOM, sin CR, y todas las filas tienen los mismos campos al leerlas como RFC 4180.",
        3: "Claves primarias y restricciones UNIQUE sin duplicados.",
        4: "Claves foráneas íntegras y ninguna entidad huérfana.",
        5: "Restricciones de la sección 6, posiciones consecutivas desde 1 y orden de la sección 7.",
        6: "Columnas obligatorias sin nulos y ningún texto vacío: el campo vacío y sin comillas es NULL.",
        7: "Catálogos y frecuencias de la sección 8 exactos; el resto del perfil, dentro de ±3 %.",
        8: "Están los defectos de la sección 10 y no hay repeticiones dentro de una película ni un keyword_id con dos nombres.",
        9: "Cada fila de movie_enrichment corresponde a un dato presente, y los códigos fx cuadran con el estreno.",
    }
    ok = True
    for number in range(1, 10):
        passed = not buckets[number]
        ok = ok and passed
        lines.append(f"{number}. {'PASS' if passed else 'FAIL'}. {summaries[number]}")
        for detail in buckets[number]:
            lines.append(f"   - {detail}")
    return ok, lines, stats


def write_readme(directory: Path, lines: list[str], stats: list[dict]) -> None:
    body = [
        "# Datos sintéticos de entrada de ElastiFlix",
        "",
        "Estos archivos son **sintéticos**. No proceden del catálogo original, no usan",
        "títulos de películas reales, nombres de personas reales ni nombres de compañías",
        "reales, y las sinopsis están generadas. Los catálogos cerrados (estado, rating,",
        "idiomas, países, géneros, idiomas hablados y campos de enrichment) sí usan los",
        "valores exactos del contrato.",
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
        "python3 raw_data/generate_raw_data.py --validate",
        "```",
        "",
        "El primer comando reescribe los 20 CSV en este directorio. `--validate` los",
        "genera dos veces, comprueba el contrato y vuelve a escribir este README.",
        "`created_at` y `updated_at` no están en los archivos: los asigna PostgreSQL.",
        "",
        "## Archivos",
        "",
        "| Archivo | Filas | Bytes | SHA-256 |",
        "|---|---:|---:|---|",
    ]
    for item in stats:
        body.append(f"| `{item['file']}` | {item['rows']} | {item['bytes']} | `{item['sha256']}` |")
    body.extend([
        "",
        "Las filas no incluyen la cabecera. Orden de carga sin violar claves foráneas:",
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
    (directory / "README.md").write_text("\n".join(body), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera los CSV sintéticos de ElastiFlix")
    parser.add_argument("--validate", action="store_true", help="genera dos veces y comprueba el contrato")
    args = parser.parse_args(argv)
    out = Path(__file__).resolve().parent
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
    first = {item["file"].removesuffix(".csv"): item["sha256"] for item in stats}
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
