from solver import solve, solve_unique

PUZZLE = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
SOLUTION = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"


def to_board(s):
    return [int(ch) for ch in s]


def test_solves_known_puzzle():
    assert solve(to_board(PUZZLE)) == to_board(SOLUTION)


def test_keeps_givens_and_does_not_mutate_input():
    board = to_board(PUZZLE)
    solve(board)
    assert board == to_board(PUZZLE)


def test_conflicting_givens_return_none():
    board = to_board(PUZZLE)
    board[2] = 5  # ilk satırda ikinci 5
    assert solve(board) is None


def test_unsolvable_but_consistent_returns_none():
    # Çelişki yok ama (0,2) hücresine hiçbir rakam sığmıyor
    board = [0] * 81
    board[0:2] = [1, 2]
    board[3:9] = [3, 4, 5, 6, 7, 8]
    board[9 * 1 + 2] = 9
    assert solve(board) is None


def test_unique_accepts_proper_puzzle():
    assert solve_unique(to_board(PUZZLE)) == to_board(SOLUTION)


def test_unique_rejects_puzzle_with_missing_digits():
    # İpuçlarının bir kısmı "okunamamış" gibi silinirse birden fazla çözüm çıkar
    board = to_board(PUZZLE)
    for i in (0, 1, 4, 9, 12, 13):
        board[i] = 0
    assert solve(board) is not None
    assert solve_unique(board) is None


def test_hard_puzzle_within_step_limit():
    # "Dünyanın en zor sudokusu" (Arto Inkala)
    hard = "800000000003600000070090200050007000000045700000100030001000068008500010090000400"
    result = solve_unique(to_board(hard))  # tek çözümlü olduğu da doğrulansın
    assert result is not None and all(result)
