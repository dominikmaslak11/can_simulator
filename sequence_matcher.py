def frames_equal(candidate1, candidate2, tolerance_bytes=None):
    """
    Porównuje dwie ramki (cid, data, is_extended).
    Zwraca True, jeśli są identyczne lub różnią się tylko na dozwolonych pozycjach.
    """
    cid1, data1, ext1 = candidate1
    cid2, data2, ext2 = candidate2

    if cid1 != cid2 or ext1 != ext2:
        return False
    if len(data1) != len(data2):
        return False

    if tolerance_bytes is None:
        return data1 == data2

    for i, (b1, b2) in enumerate(zip(data1, data2)):
        if i in tolerance_bytes:
            continue
        if b1 != b2:
            return False
    return True


def longest_common_subsequence(seq1, seq2, tolerance_bytes=None):
    """
    Znajduje najdłuższy wspólny podciąg dwóch sekwencji ramek.
    Zwraca listę indeksów w seq1, które tworzą LCS.
    """
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if frames_equal(seq1[i - 1], seq2[j - 1], tolerance_bytes):
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Odtworzenie LCS
    lcs_indices = []
    i, j = m, n
    while i > 0 and j > 0:
        if frames_equal(seq1[i - 1], seq2[j - 1], tolerance_bytes):
            lcs_indices.append(i - 1)
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return list(reversed(lcs_indices))


def find_common_pattern(sequences, min_length=2, tolerance_bytes=None):
    """
    Znajduje najdłuższy wzorzec występujący we wszystkich podanych sekwencjach.
    """
    if not sequences:
        return []
    pattern = sequences[0]
    for seq in sequences[1:]:
        indices = longest_common_subsequence(pattern, seq, tolerance_bytes)
        pattern = [pattern[i] for i in indices]
    return pattern
