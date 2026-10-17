"""İnsan gibi çözen sudoku çözücü: ipuçları ve zorluk derecesi.

Teknikler kolaydan zora sırayla denenir; her adımda en basit işe yarayan teknik kullanılır.
Bulmacanın zorluğu, çözüm için gereken en zor tekniğe göre belirlenir. Teknikler yetmezse
kalan hücreler deneme yanılmayla bulunan çözümden doldurulur ve bulmaca "Şeytani" sayılır.
"""
from itertools import combinations

from solver import solve_unique

ROWS = [[r * 9 + c for c in range(9)] for r in range(9)]
COLS = [[r * 9 + c for r in range(9)] for c in range(9)]
BOXES = [[(b // 3 * 3 + i // 3) * 9 + b % 3 * 3 + i % 3 for i in range(9)] for b in range(9)]
UNITS = [("satır", u) for u in ROWS] + [("sütun", u) for u in COLS] + [("kutu", u) for u in BOXES]
PEERS = [set().union(*(u for _, u in UNITS if i in u)) - {i} for i in range(81)]
BOX_NAMES = ["sol üst", "üst orta", "sağ üst", "sol orta", "orta", "sağ orta", "sol alt", "alt orta", "sağ alt"]
LEVELS = ["Kolay", "Orta", "Zor", "Şeytani"]


def cell_name(i):
    return f"{i // 9 + 1}. satır {i % 9 + 1}. sütun"


def unit_name(kind, cells):
    if kind == "satır":
        return f"{cells[0] // 9 + 1}. satır"
    if kind == "sütun":
        return f"{cells[0] % 9 + 1}. sütun"
    return f"{BOX_NAMES[(cells[0] // 27) * 3 + cells[0] % 9 // 3]} kutu"


def digits(ds):
    return ", ".join(str(d) for d in sorted(ds))


# ---------- Yerleştirme teknikleri: (hücre, rakam, açıklama, vurgulanacak hücreler) ----------

def naked_single(board, cands):
    for i in range(81):
        if not board[i] and len(cands[i]) == 1:
            d = next(iter(cands[i]))
            return i, d, (f"Bu hücreye sadece {d} sığıyor: satırında, sütununda ve kutusunda diğer bütün "
                          "rakamlar zaten var."), sorted(PEERS[i])


def hidden_single(board, cands):
    for kind, unit in UNITS:  # önce satır ve sütunlar, sonra kutular
        for d in range(1, 10):
            spots = [i for i in unit if not board[i] and d in cands[i]]
            if len(spots) == 1:
                i = spots[0]
                return i, d, f"{unit_name(kind, unit)} içinde {d} rakamı sadece bu hücreye sığıyor.", unit


# ---------- Eleme teknikleri: (silinecek [(hücre, rakam)], açıklama, vurgulanacak hücreler) ----------

def naked_subset(board, cands, size):
    for kind, unit in UNITS:
        empty = [i for i in unit if not board[i] and 2 <= len(cands[i]) <= size]
        for group in combinations(empty, size):
            union = set().union(*(cands[i] for i in group))
            if len(union) != size:
                continue
            removals = [(i, d) for i in unit if i not in group and not board[i] for d in union & cands[i]]
            if removals:
                cells = " ve ".join(cell_name(i) for i in group)
                return removals, (f"{cells} hücrelerine sadece {digits(union)} sığıyor. Bu rakamlar "
                                  f"bu hücrelere ait olduğundan {unit_name(kind, unit)} içindeki diğer "
                                  "hücrelerden elenir."), list(group)


def hidden_pair(board, cands):
    for kind, unit in UNITS:
        spots = {d: [i for i in unit if not board[i] and d in cands[i]] for d in range(1, 10)}
        for a, b in combinations(range(1, 10), 2):
            if len(spots[a]) == 2 and spots[a] == spots[b]:
                removals = [(i, d) for i in spots[a] for d in cands[i] - {a, b}]
                if removals:
                    cells = " ve ".join(cell_name(i) for i in spots[a])
                    return removals, (f"{unit_name(kind, unit)} içinde {a} ve {b} sadece {cells} "
                                      "hücrelerine sığıyor. Bu iki hücre onlara ayrıldığından diğer adaylar "
                                      "elenir."), spots[a]


def box_line(board, cands):
    """Kutu içinde bir rakamın yerleri tek satır/sütundaysa o satır/sütunun geri kalanından elenir (ve tersi)."""
    for box_index, box in enumerate(BOXES):
        for kind, lines in (("satır", ROWS), ("sütun", COLS)):
            for line in lines:
                inside = set(box) & set(line)
                for d in range(1, 10):
                    in_box = {i for i in box if not board[i] and d in cands[i]}
                    in_line = {i for i in line if not board[i] and d in cands[i]}
                    if in_box and in_box <= inside:  # kutudaki yerleri bu satır/sütunda
                        removals = [(i, d) for i in in_line - inside]
                        if removals:
                            return removals, (f"{BOX_NAMES[box_index]} kutuda {d} sadece {unit_name(kind, line)} "
                                              f"üzerinde olabilir. Bu yüzden {unit_name(kind, line)} içindeki "
                                              f"diğer kutulardan {d} elenir."), sorted(in_box)
                    if in_line and in_line <= inside:  # satır/sütundaki yerleri bu kutuda
                        removals = [(i, d) for i in in_box - inside]
                        if removals:
                            return removals, (f"{unit_name(kind, line)} içinde {d} sadece {BOX_NAMES[box_index]} "
                                              f"kutuda olabilir. Bu yüzden o kutunun geri kalanından {d} "
                                              "elenir."), sorted(in_line)


def x_wing(board, cands):
    for kind, lines, cross in (("satır", ROWS, lambda i: i % 9), ("sütun", COLS, lambda i: i // 9)):
        for d in range(1, 10):
            spots = [[i for i in line if not board[i] and d in cands[i]] for line in lines]
            for a, b in combinations(range(9), 2):
                if len(spots[a]) == 2 and len(spots[b]) == 2 and \
                        [cross(i) for i in spots[a]] == [cross(i) for i in spots[b]]:
                    crossing = [COLS, ROWS][kind == "sütun"]
                    corners = spots[a] + spots[b]
                    removals = [(i, d) for k in (cross(i) for i in spots[a]) for i in crossing[k]
                                if i not in corners and not board[i] and d in cands[i]]
                    if removals:
                        other = "sütun" if kind == "satır" else "satır"
                        return removals, (f"{d} rakamı {a + 1}. ve {b + 1}. {kind} içinde sadece aynı iki "
                                          f"{other}da olabilir. {d} bu dört köşeden ikisine karşılıklı yerleşeceği "
                                          f"için o iki {other}un geri kalanından elenir."), corners


# (teknik adı, fonksiyon, zorluk seviyesi: 0 Kolay, 1 Orta, 2 Zor)
PLACEMENTS = [("Tek aday", naked_single, 0), ("Gizli tek", hidden_single, 0)]
ELIMINATIONS = [
    ("Açık çift", lambda b, c: naked_subset(b, c, 2), 1),
    ("Kutu-satır kesişimi", box_line, 1),
    ("Gizli çift", hidden_pair, 2),
    ("Açık üçlü", lambda b, c: naked_subset(b, c, 3), 2),
    ("X-Wing", x_wing, 2),
]


def candidates(board):
    return [set() if board[i] else set(range(1, 10)) - {board[p] for p in PEERS[i]} for i in range(81)]


def sentence(text):
    return text[0].upper() + text[1:]


def explain(board):
    """Bulmacanın insan gibi çözümü. Tek çözümü yoksa None.

    Döner: {"zorluk": "Orta", "ipuclari": [{hucre, rakam, teknik, aciklama, on_adimlar, vurgu}, ...]}
    Her ipucu bir hücreye rakam yerleştirir. Gereken elemeler, ilgili oldukları ilk ipucunun
    on_adimlar listesine eklenir (hücreyi ya da onun satır/sütun/kutusunu etkileyen elemeler).
    "teknik", ipucunun kullandığı en zor tekniktir.
    """
    solution = solve_unique(board)
    if solution is None:
        return None
    board = list(board)
    cands = candidates(board)
    hints, pending, level = [], [], 0  # pending: henüz bir ipucuna bağlanmamış elemeler
    while not all(board):
        for name, technique, technique_level in PLACEMENTS:
            found = technique(board, cands)
            if found:
                i, d, text, highlight = found
                break
        else:
            for name, technique, technique_level in ELIMINATIONS:
                found = technique(board, cands)
                if found:
                    removals, text, highlight = found
                    for i, d in removals:
                        cands[i].discard(d)
                    pending.append({"teknik": name, "aciklama": sentence(text), "seviye": technique_level,
                                    "hucreler": {i for i, _ in removals}})
                    level = max(level, technique_level)
                    break
            else:  # mantık teknikleri tükendi: deneme yanılma gerekiyor
                i = min((i for i in range(81) if not board[i]), key=lambda i: len(cands[i]))
                d, name, technique_level, highlight = solution[i], "Deneme yanılma", 3, [i]
                text = (f"Bilinen mantık teknikleri burada yetmiyor. Bu hücre için adaylar "
                        f"{digits(cands[i])}; bunlar tek tek denendiğinde sadece {d} çelişkisiz bir çözüme ulaşıyor.")
            if technique_level < 3:
                continue
        level = max(level, technique_level)
        nearby = PEERS[i] | {i}
        before = [p for p in pending if p["hucreler"] & nearby]
        pending = [p for p in pending if not p["hucreler"] & nearby]
        hardest = max(before, key=lambda p: p["seviye"], default=None)
        if hardest and hardest["seviye"] >= technique_level:
            name = hardest["teknik"]
        hints.append({"hucre": i, "rakam": d, "teknik": name, "aciklama": sentence(text),
                      "on_adimlar": [{"teknik": p["teknik"], "aciklama": p["aciklama"]} for p in before],
                      "vurgu": highlight})
        board[i] = d
        cands[i] = set()
        for p in PEERS[i]:
            cands[p].discard(d)
    return {"zorluk": LEVELS[level], "ipuclari": hints}
