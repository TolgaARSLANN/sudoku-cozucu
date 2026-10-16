"""Bitmask + MRV (en az seçenekli hücre önce) backtracking sudoku çözücü."""


def _search(board, max_solutions, max_steps):
    """En fazla max_solutions çözüm bulup listeler. Çelişkili tahtada ya da adım sınırı aşılırsa []."""
    b = list(board)
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
    for i, v in enumerate(b):
        if v:
            r, c = divmod(i, 9)
            k, bit = r // 3 * 3 + c // 3, 1 << v
            if (rows[r] | cols[c] | boxes[k]) & bit:
                return []  # verilen rakamlar çelişiyor (büyük ihtimalle yanlış okuma)
            rows[r] |= bit
            cols[c] |= bit
            boxes[k] |= bit
    empties = [i for i in range(81) if not b[i]]
    solutions = []
    steps = 0

    def rec():
        """True dönerse arama durur (yeterince çözüm bulundu ya da adım sınırı aşıldı)."""
        nonlocal steps
        steps += 1
        if steps > max_steps:
            return True
        best, best_opts, best_n = None, 0, 10
        for i in empties:
            if b[i]:
                continue
            r, c = divmod(i, 9)
            opts = ~(rows[r] | cols[c] | boxes[r // 3 * 3 + c // 3]) & 0x3FE
            n = opts.bit_count()
            if n == 0:
                return False
            if n < best_n:
                best, best_opts, best_n = i, opts, n
        if best is None:
            solutions.append(list(b))
            return len(solutions) >= max_solutions
        r, c = divmod(best, 9)
        k = r // 3 * 3 + c // 3
        for v in range(1, 10):
            bit = 1 << v
            if best_opts & bit:
                b[best] = v
                rows[r] |= bit
                cols[c] |= bit
                boxes[k] |= bit
                stop = rec()
                rows[r] ^= bit
                cols[c] ^= bit
                boxes[k] ^= bit
                if stop:
                    b[best] = 0
                    return True
        b[best] = 0
        return False

    rec()
    return [] if steps > max_steps else solutions


def solve(board, max_steps=20000):
    """board: 81 elemanlı liste, boş hücre 0. Bir çözüm listesi ya da None döner."""
    solutions = _search(board, 1, max_steps)
    return solutions[0] if solutions else None


def solve_unique(board, max_steps=20000):
    """Tek çözümü varsa onu döner; çözümsüz ya da birden fazla çözümlüyse None.

    Gerçek bir sudokunun tek çözümü vardır. Birden fazla çözüm çıkması genelde
    bir rakamın okunamadığı anlamına gelir; yanlış çözüm göstermektense reddederiz.
    """
    solutions = _search(board, 2, max_steps)
    return solutions[0] if len(solutions) == 1 else None
