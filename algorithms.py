"""Pure, incremental algorithms. Each yielded frame is an immutable snapshot."""

from dataclasses import dataclass
from typing import Callable, Iterator, Optional


@dataclass(frozen=True)
class Step:
    values: tuple
    message: str
    active: tuple = ()
    pivot: tuple = ()
    settled: tuple = ()
    discarded: tuple = ()
    found: tuple = ()
    comparisons: int = 0
    writes: int = 0
    line: int = 0
    done: bool = False
    result: Optional[int] = None
    swap: tuple = ()


def frame(values, message, **kwargs):
    return Step(tuple(values), message, **kwargs)


def finished(values):
    return frame(values, "Sorted! Every value is in its place.",
                 settled=tuple(range(len(values))), done=True, line=5)


def bubble_sort(values, target=None):
    a = list(values)
    settled = ()
    for end in range(len(a) - 1, 0, -1):
        swapped = False
        for j in range(end):
            yield frame(a, f"Compare {a[j]} and {a[j + 1]}.", active=(j, j + 1),
                        settled=settled, comparisons=1, line=1)
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
                yield frame(a, "Swap the neighboring values.", active=(j, j + 1),
                            settled=settled, writes=2, line=2, swap=(j, j + 1))
        settled = tuple(range(end, len(a)))
        yield frame(a, f"Position {end} is now settled.", settled=settled, line=3)
        if not swapped:
            break
    yield finished(a)


def selection_sort(values, target=None):
    a = list(values)
    for i in range(len(a)):
        minimum = i
        for j in range(i + 1, len(a)):
            yield frame(a, f"Is {a[j]} smaller than {a[minimum]}?",
                        active=(j,), pivot=(minimum,), settled=tuple(range(i)),
                        comparisons=1, line=1)
            if a[j] < a[minimum]:
                minimum = j
                yield frame(a, f"New minimum: {a[minimum]}.", pivot=(minimum,),
                            settled=tuple(range(i)), line=2)
        writes = 0
        if minimum != i:
            a[i], a[minimum] = a[minimum], a[i]
            writes = 2
        yield frame(a, f"Place {a[i]} at position {i}.",
                    settled=tuple(range(i + 1)), writes=writes, line=3,
                    swap=(i, minimum) if writes else ())
    yield finished(a)


def insertion_sort(values, target=None):
    a = list(values)
    for i in range(1, len(a)):
        key, j = a[i], i - 1
        yield frame(a, f"Take {key}; find its place in the sorted prefix.", pivot=(i,), line=0)
        while j >= 0:
            yield frame(a, f"Compare {a[j]} with the held value {key}.",
                        active=(j,), comparisons=1, line=1)
            if a[j] <= key:
                break
            a[j + 1] = a[j]
            yield frame(a, f"Shift {a[j]} one place to the right.",
                        active=(j, j + 1), writes=1, line=2)
            j -= 1
        a[j + 1] = key
        yield frame(a, f"Insert {key} at position {j + 1}.",
                    active=(j + 1,), writes=1, line=3)
    yield finished(a)


def merge_sort(values, target=None):
    a = list(values)
    width = 1
    while width < len(a):
        for low in range(0, len(a), 2 * width):
            mid, high = min(low + width, len(a)), min(low + 2 * width, len(a))
            if mid == high:
                continue
            left, right = a[low:mid], a[mid:high]
            i = j = 0
            yield frame(a, f"Merge runs [{low}–{mid - 1}] and [{mid}–{high - 1}].",
                        active=tuple(range(low, high)), line=0)
            for k in range(low, high):
                if i < len(left) and j < len(right):
                    yield frame(a, f"Compare {left[i]} and {right[j]} from the two runs.",
                                active=(low + i, mid + j), comparisons=1, line=1)
                if j == len(right) or (i < len(left) and left[i] <= right[j]):
                    a[k] = left[i]
                    i += 1
                else:
                    a[k] = right[j]
                    j += 1
                yield frame(a, f"Write {a[k]} into position {k}.", active=(k,), writes=1, line=2)
        width *= 2
    yield finished(a)


def shell_sort(values, target=None):
    """Gapped insertion sort using Shell's original halving sequence."""
    a = list(values)
    gap = len(a) // 2
    while gap:
        yield frame(a, f"Gap {gap}: insertion-sort values this far apart.", line=0)
        for i in range(gap, len(a)):
            key, j = a[i], i
            yield frame(a, f"Hold {key} while exploring its gap-{gap} group.",
                        pivot=(i,), line=1)
            while j >= gap:
                yield frame(a, f"Compare {a[j - gap]} with held value {key}.",
                            active=(j - gap,), pivot=(j,), comparisons=1, line=2)
                if a[j - gap] <= key:
                    break
                a[j] = a[j - gap]
                yield frame(a, f"Shift {a[j]} forward by {gap} positions.",
                            active=(j - gap, j), writes=1, line=3)
                j -= gap
            a[j] = key
            yield frame(a, f"Insert {key} at index {j}.", active=(j,), writes=1, line=4)
        gap //= 2
    yield finished(a)


def comb_sort(values, target=None):
    """Shrink the comparison gap by 1.3, finishing with swap-free gap-1 passes."""
    a = list(values)
    gap, swapped = len(a), True
    while gap > 1 or swapped:
        gap = max(1, gap * 10 // 13)
        swapped = False
        yield frame(a, f"Comb the array with a gap of {gap}.", line=0)
        for i in range(len(a) - gap):
            j = i + gap
            yield frame(a, f"Compare {a[i]} and {a[j]}, {gap} positions apart.",
                        active=(i, j), comparisons=1, line=1)
            if a[i] > a[j]:
                a[i], a[j] = a[j], a[i]
                swapped = True
                yield frame(a, "Swap this out-of-order pair.", active=(i, j),
                            writes=2, swap=(i, j), line=2)
        yield frame(a, "Repeat gap 1 until no swaps remain." if gap == 1 else
                    "Shrink the gap and comb again.", line=3)
    yield finished(a)


def quick_sort(values, target=None):
    a = list(values)
    stack = [(0, len(a) - 1)]
    settled = set()
    while stack:
        low, high = stack.pop()
        if low > high:
            continue
        if low == high:
            settled.add(low)
            continue
        pivot, i = a[high], low
        yield frame(a, f"Partition [{low}–{high}] around pivot {pivot}.",
                    pivot=(high,), settled=tuple(sorted(settled)), line=0)
        for j in range(low, high):
            yield frame(a, f"Compare {a[j]} with pivot {pivot}.",
                        active=(j,), pivot=(high,), settled=tuple(sorted(settled)),
                        comparisons=1, line=1)
            if a[j] <= pivot:
                if i != j:
                    a[i], a[j] = a[j], a[i]
                    yield frame(a, "Move this value to the smaller partition.",
                                active=(i, j), pivot=(high,),
                                settled=tuple(sorted(settled)), writes=2, line=2, swap=(i, j))
                i += 1
        writes = 0
        if i != high:
            a[i], a[high] = a[high], a[i]
            writes = 2
        settled.add(i)
        yield frame(a, f"Pivot {pivot} is settled at position {i}.",
                    settled=tuple(sorted(settled)), writes=writes, line=3,
                    swap=(i, high) if writes else ())
        stack.extend(((i + 1, high), (low, i - 1)))
    yield finished(a)


def heap_sort(values, target=None):
    a = list(values)
    settled = ()

    def sift(size, root):
        while 2 * root + 1 < size:
            child = 2 * root + 1
            if child + 1 < size:
                yield frame(a, "Choose the larger child.", active=(child, child + 1),
                            settled=settled, comparisons=1, line=1)
                if a[child] < a[child + 1]:
                    child += 1
            yield frame(a, "Compare the parent with its largest child.",
                        active=(root, child), settled=settled, comparisons=1, line=2)
            if a[root] >= a[child]:
                return
            a[root], a[child] = a[child], a[root]
            yield frame(a, "Swap to restore the max-heap property.",
                        active=(root, child), settled=settled, writes=2, line=3,
                        swap=(root, child))
            root = child

    for root in range(len(a) // 2 - 1, -1, -1):
        yield from sift(len(a), root)
    for end in range(len(a) - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        settled = tuple(range(end, len(a)))
        yield frame(a, f"Move the maximum {a[end]} to position {end}.",
                    settled=settled, writes=2, line=4, swap=(0, end))
        yield from sift(end, 0)
    yield finished(a)


def counting_sort(values, target=None):
    a = list(values)
    if not a:
        yield finished(a)
        return
    low = high = a[0]
    for i in range(1, len(a)):
        low, high = min(low, a[i]), max(high, a[i])
        yield frame(a, f"Find the value range: {low} to {high}.",
                    active=(i,), comparisons=2, line=0)
    counts = [0] * (high - low + 1)
    for i, value in enumerate(a):
        counts[value - low] += 1
        yield frame(a, f"Count {value}: {counts[value - low]} occurrence(s).", active=(i,), line=1)
    position = 0
    for offset, count in enumerate(counts):
        for _ in range(count):
            a[position] = offset + low
            yield frame(a, f"Place {a[position]} from its frequency bucket.",
                        settled=tuple(range(position + 1)), writes=1, line=3)
            position += 1
    yield finished(a)


def radix_sort(values, target=None):
    a = list(values)
    if not a:
        yield finished(a)
        return
    low = high = a[0]
    for i in range(1, len(a)):
        low, high = min(low, a[i]), max(high, a[i])
        yield frame(a, "Find the range for signed digit keys.", active=(i,), comparisons=2, line=0)
    offset = -min(0, low)
    place = 1
    while (high + offset) // place > 0:
        buckets = [[] for _ in range(10)]
        for i, value in enumerate(a):
            digit = ((value + offset) // place) % 10
            buckets[digit].append(value)
            yield frame(a, f"Digit place {place}: put {value} in bucket {digit}.", active=(i,), line=1)
        position = 0
        for digit, bucket in enumerate(buckets):
            for value in bucket:
                a[position] = value
                yield frame(a, f"Collect {value} from bucket {digit}, preserving order.",
                            active=(position,), writes=1, line=2)
                position += 1
        place *= 10
    yield finished(a)


def linear_search(values, target):
    a = list(values)
    for i, value in enumerate(a):
        yield frame(a, f"Does {value} equal {target}?", active=(i,),
                    discarded=tuple(range(i)), comparisons=1, line=1)
        if value == target:
            yield frame(a, f"Found {target} at index {i} (position {i + 1}).",
                        found=(i,), done=True, result=i, line=2)
            return
    yield frame(a, f"{target} was not found in this array.",
                discarded=tuple(range(len(a))), done=True, line=4)


def binary_search(values, target):
    """Search ascending input, returning the leftmost match for duplicates."""
    a = list(values)
    low, high, result = 0, len(a) - 1, None
    while low <= high:
        mid = (low + high) // 2
        discarded = tuple(i for i in range(len(a)) if i < low or i > high)
        yield frame(a, f"Check midpoint {mid}: compare {a[mid]} with {target}.",
                    active=(mid,), pivot=(low, high), discarded=discarded,
                    comparisons=1, line=1)
        if a[mid] == target:
            result = mid
            high = mid - 1
            yield frame(a, "Match found; check the left half for an earlier match.", found=(mid,), line=2)
        else:
            yield frame(a, f"Choose which half can contain {target}.", active=(mid,),
                        comparisons=1, discarded=discarded, line=3)
            if a[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
    if result is None:
        yield frame(a, f"{target} was not found in this array.",
                    discarded=tuple(range(len(a))), done=True, line=4)
    else:
        yield frame(a, f"Found {target} at index {result} in the sorted array.",
                    found=(result,), result=result, done=True, line=4)


def interpolation_search(values, target):
    """Search ascending integers by estimated position; return the first match."""
    a = list(values)
    low, high = 0, len(a) - 1
    while low <= high:
        discarded = tuple(i for i in range(len(a)) if i < low or i > high)
        yield frame(a, f"Check whether {target} is below the lower bound {a[low]}.",
                    pivot=(low, high), discarded=discarded, comparisons=1, line=0)
        if target < a[low]:
            break
        yield frame(a, f"Check whether {target} is above the upper bound {a[high]}.",
                    pivot=(low, high), discarded=discarded, comparisons=1, line=0)
        if target > a[high]:
            break
        yield frame(a, "Check for an equal-valued range before estimating a position.",
                    pivot=(low, high), discarded=discarded, comparisons=1, line=1)
        # If the endpoints match, the entire sorted range matches the target.
        position = low if a[low] == a[high] else (
            low + (target - a[low]) * (high - low) // (a[high] - a[low]))
        yield frame(a, f"Estimate index {position}; compare {a[position]} with {target}.",
                    active=(position,), pivot=(low, high), discarded=discarded,
                    comparisons=1, line=2)
        if a[position] == target:
            while position > 0:
                yield frame(a, "Check the preceding value for the first occurrence.",
                            active=(position - 1,), found=(position,), comparisons=1, line=3)
                if a[position - 1] != target:
                    break
                position -= 1
            yield frame(a, f"Found {target} at index {position} in the sorted array.",
                        found=(position,), result=position, done=True, line=5)
            return
        yield frame(a, "Narrow the interval around the estimated position.",
                    active=(position,), discarded=discarded, comparisons=1, line=4)
        if a[position] < target:
            low = position + 1
        else:
            high = position - 1
    yield frame(a, f"{target} was not found in this array.",
                discarded=tuple(range(len(a))), done=True, line=5)


@dataclass(frozen=True)
class Algorithm:
    name: str
    category: str
    function: Callable[..., Iterator[Step]]
    summary: str
    average: str
    worst: str
    space: str
    code: tuple


ALGORITHMS = {
    item.name: item for item in (
        Algorithm("Bubble Sort", "Sort", bubble_sort,
                  "Compare neighbors. Swap them when they are out of order. The largest value bubbles to the end.",
                  "O(n²)", "O(n²)", "O(1)",
                  ("repeat for each unsorted end", "  compare adjacent values", "  swap if left > right",
                   "  settle the largest value", "  stop if no swaps occurred", "return sorted array")),
        Algorithm("Selection Sort", "Sort", selection_sort,
                  "Find the smallest remaining value, then place it at the front of the unsorted region.",
                  "O(n²)", "O(n²)", "O(1)",
                  ("for each position i", "  scan for the smallest value", "  remember the new minimum",
                   "  place minimum at i", "  advance the sorted boundary", "return sorted array")),
        Algorithm("Insertion Sort", "Sort", insertion_sort,
                  "Build an ordered prefix one value at a time, just like arranging cards in your hand.",
                  "O(n²)", "O(n²)", "O(1)",
                  ("take the next value as key", "compare key with left neighbor", "shift larger values right",
                   "insert key into the gap", "repeat for each remaining value", "return sorted array")),
        Algorithm("Shell Sort", "Sort", shell_sort,
                  "Insertion-sort distant neighbors, then halve the gap. Uses Shell's original halving sequence; costs depend on gaps.",
                  "Gap-dependent", "O(n²)", "O(1)",
                  ("start with gap = n // 2", "hold the next value as key", "compare gap-spaced neighbors",
                   "shift larger values by the gap", "insert key; halve gap and repeat", "return sorted array")),
        Algorithm("Comb Sort", "Sort", comb_sort,
                  "Swap distant out-of-order pairs. Shrink the gap by 1.3, then repeat gap 1 until a pass makes no swaps.",
                  "Gap-dependent", "O(n²)", "O(1)",
                  ("shrink gap by 1.3; minimum 1", "compare values a gap apart", "swap if they are out of order",
                   "repeat until gap 1 has no swaps", "all neighboring pairs are ordered", "return sorted array")),
        Algorithm("Merge Sort", "Sort", merge_sort,
                  "Merge small ordered runs into larger ones. Double the run size until the whole array is sorted.",
                  "O(n log n)", "O(n log n)", "O(n)",
                  ("pair adjacent sorted runs", "compare heads of both runs", "write the smaller head",
                   "drain any remaining values", "double run width and repeat", "return sorted array")),
        Algorithm("Quick Sort", "Sort", quick_sort,
                  "Choose a pivot. Partition values around it, then repeat on both sides. Uses an explicit stack.",
                  "O(n log n)", "O(n²)", "O(n)",
                  ("choose the last value as pivot", "compare each value with pivot", "move smaller values left",
                   "place pivot in final position", "repeat on both partitions", "return sorted array")),
        Algorithm("Heap Sort", "Sort", heap_sort,
                  "Build a max heap. Repeatedly move the largest value to the end and repair the remaining heap.",
                  "O(n log n)", "O(n log n)", "O(1)",
                  ("build a max heap", "choose the larger child", "compare parent and child",
                   "swap and continue sifting", "extract maximum; repair heap", "return sorted array")),
        Algorithm("Counting Sort", "Sort", counting_sort,
                  "Count each integer, then rebuild the array from its frequencies. k is the integer value range.",
                  "O(n + k)", "O(n + k)", "O(k)",
                  ("find minimum and maximum", "count each value in its bucket", "visit buckets in order",
                   "write each value by frequency", "continue until all values placed", "return sorted array")),
        Algorithm("Radix Sort", "Sort", radix_sort,
                  "Group by digits, from units upward. Shift signed keys so negative integers work too. d is digit count.",
                  "O(d · n)", "O(d · n)", "O(n)",
                  ("find range; offset negative keys", "distribute by current digit", "collect buckets in order",
                   "move to the next digit", "repeat until all digits processed", "return sorted array")),
        Algorithm("Linear Search", "Search", linear_search,
                  "Check values from left to right. Return the first match; no ordering is required.",
                  "O(n)", "O(n)", "O(1)",
                  ("start at the first value", "compare current value to target", "if equal: return its index",
                   "otherwise move to next value", "if exhausted: target not found", "search complete")),
        Algorithm("Binary Search", "Search", binary_search,
                  "Halve an ordered search interval. Input is sorted before searching; preparation is excluded from metrics.",
                  "O(log n)", "O(log n)", "O(1)",
                  ("start with the full sorted range", "compare midpoint to target", "on match: keep searching left",
                   "discard the impossible half", "return first match, or not found", "indices refer to sorted input")),
        Algorithm("Interpolation Search", "Search", interpolation_search,
                  "Estimate a position from endpoint values. Average O(log log n) assumes uniform distinct keys; duplicates may need a linear scan. Input is sorted first.",
                  "O(log log n)*", "O(n)", "O(1)",
                  ("check target within endpoint range", "handle equal endpoints safely",
                   "estimate index; compare to target", "on match: find first duplicate",
                   "otherwise narrow the interval", "return first match, or not found")),
    )
}
