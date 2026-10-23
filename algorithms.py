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
    arr = list(values)
    n = len(arr)
    settled = ()
    for i in range(n - 1):
        swapped = False
        for j in range(n - i - 1):
            yield frame(arr, f"Compare {arr[j]} and {arr[j + 1]}.", active=(j, j + 1),
                        settled=settled, comparisons=1, line=1)
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
                swapped = True
                yield frame(arr, "Swap the neighboring values using temp.", active=(j, j + 1),
                            settled=settled, writes=2, line=2, swap=(j, j + 1))
        settled = tuple(range(n - i - 1, n))
        yield frame(arr, f"Position {n - i - 1} is now settled.", settled=settled, line=3)
        if not swapped:
            break
    yield finished(arr)


def selection_sort(values, target=None):
    arr = list(values)
    n = len(arr)
    for i in range(n - 1):
        min_index = i
        for j in range(i + 1, n):
            yield frame(arr, f"Is {arr[j]} smaller than {arr[min_index]}?",
                        active=(j,), pivot=(min_index,), settled=tuple(range(i)),
                        comparisons=1, line=1)
            if arr[j] < arr[min_index]:
                min_index = j
                yield frame(arr, f"New minimum: {arr[min_index]}.", pivot=(min_index,),
                            settled=tuple(range(i)), line=2)
        temp = arr[i]
        arr[i] = arr[min_index]
        arr[min_index] = temp
        yield frame(arr, f"Place the minimum {arr[i]} at position {i}.",
                    settled=tuple(range(i + 1)), writes=2, line=3,
                    swap=(i, min_index) if i != min_index else ())
    yield finished(arr)


def insertion_sort(values, target=None):
    arr = list(values)
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        yield frame(arr, f"Hold {key} as key.", pivot=(i,), line=0)
        while j >= 0 and arr[j] > key:
            yield frame(arr, f"Compare {arr[j]} with key {key}.",
                        active=(j,), comparisons=1, line=1)
            arr[j + 1] = arr[j]
            yield frame(arr, f"Shift {arr[j]} one place to the right.",
                        active=(j, j + 1), writes=1, line=2)
            j -= 1
        if j >= 0:
            yield frame(arr, f"{arr[j]} is not greater than key {key}; stop shifting.",
                        active=(j,), comparisons=1, line=1)
        arr[j + 1] = key
        yield frame(arr, f"Insert key {key} at position {j + 1}.",
                    active=(j + 1,), writes=1, line=3)
    yield finished(arr)


def merge_sort(values, target=None):
    arr = list(values)

    def merge(left, mid, right):
        n1 = mid - left + 1
        n2 = right - mid
        left_arr = [0] * n1
        right_arr = [0] * n2
        for i in range(n1):
            left_arr[i] = arr[left + i]
        for j in range(n2):
            right_arr[j] = arr[mid + 1 + j]
        i = 0
        j = 0
        k = left
        yield frame(arr, f"Merge [{left}–{mid}] and [{mid + 1}–{right}] using two temporary arrays.",
                    active=tuple(range(left, right + 1)), line=1)
        while i < n1 and j < n2:
            yield frame(arr, f"Compare left value {left_arr[i]} with right value {right_arr[j]}.",
                        active=(k,), comparisons=1, line=2)
            if left_arr[i] <= right_arr[j]:
                arr[k] = left_arr[i]
                i += 1
            else:
                arr[k] = right_arr[j]
                j += 1
            yield frame(arr, f"Write {arr[k]} into position {k}.", active=(k,), writes=1, line=3)
            k += 1
        while i < n1:
            arr[k] = left_arr[i]
            yield frame(arr, f"Copy remaining left value {arr[k]} to position {k}.",
                        active=(k,), writes=1, line=4)
            i += 1
            k += 1
        while j < n2:
            arr[k] = right_arr[j]
            yield frame(arr, f"Copy remaining right value {arr[k]} to position {k}.",
                        active=(k,), writes=1, line=4)
            j += 1
            k += 1

    def sort(left, right):
        if left < right:
            mid = left + (right - left) // 2
            yield frame(arr, f"Split [{left}–{right}] at midpoint {mid}; sort both halves.",
                        pivot=(mid,), line=0)
            yield from sort(left, mid)
            yield from sort(mid + 1, right)
            yield from merge(left, mid, right)

    yield from sort(0, len(arr) - 1)
    yield finished(arr)


def shell_sort(values, target=None):
    arr = list(values)
    n = len(arr)
    gap = n // 2
    while gap > 0:
        yield frame(arr, f"Gap {gap}: insertion-sort values this far apart.", line=0)
        for i in range(gap, n):
            temp = arr[i]
            j = i
            yield frame(arr, f"Hold {temp} in temp for this gap-{gap} group.", pivot=(i,), line=1)
            while j >= gap and arr[j - gap] > temp:
                yield frame(arr, f"Compare {arr[j - gap]} with temp {temp}.",
                            active=(j - gap,), pivot=(j,), comparisons=1, line=2)
                arr[j] = arr[j - gap]
                yield frame(arr, f"Shift {arr[j]} forward by {gap} positions.",
                            active=(j - gap, j), writes=1, line=3)
                j -= gap
            if j >= gap:
                yield frame(arr, f"{arr[j - gap]} is not greater than temp {temp}; stop shifting.",
                            active=(j - gap,), pivot=(j,), comparisons=1, line=2)
            arr[j] = temp
            yield frame(arr, f"Insert temp {temp} at index {j}.", active=(j,), writes=1, line=4)
        gap //= 2
    yield finished(arr)


def comb_sort(values, target=None):
    arr = list(values)
    n = len(arr)
    gap = n
    swapped = True
    while gap > 1 or swapped:
        gap = int(gap / 1.3)
        if gap < 1:
            gap = 1
        swapped = False
        yield frame(arr, f"Comb the array with a gap of {gap}.", line=0)
        for i in range(gap, n):
            yield frame(arr, f"Compare {arr[i - gap]} and {arr[i]}, {gap} positions apart.",
                        active=(i - gap, i), comparisons=1, line=1)
            if arr[i - gap] > arr[i]:
                temp = arr[i]
                arr[i] = arr[i - gap]
                arr[i - gap] = temp
                swapped = True
                yield frame(arr, "Swap this out-of-order pair using temp.", active=(i - gap, i),
                            writes=2, swap=(i - gap, i), line=2)
        yield frame(arr, "Repeat gap 1 until no swaps remain." if gap == 1 else
                    "Shrink the gap and comb again.", line=3)
    yield finished(arr)


def quick_sort(values, target=None):
    arr = list(values)
    settled = []

    def partition(low, high):
        pivot = arr[high]
        left = low
        right = high - 1
        yield frame(arr, f"Partition [{low}–{high}] around last value {pivot}.",
                    pivot=(high,), settled=tuple(settled), line=0)
        while left <= right:
            while left <= right:
                yield frame(arr, f"Scan from the left: compare {arr[left]} with pivot {pivot}.",
                            active=(left,), pivot=(high,), settled=tuple(settled),
                            comparisons=1, line=1)
                if arr[left] >= pivot:
                    break
                left += 1
            while left <= right:
                yield frame(arr, f"Scan from the right: compare {arr[right]} with pivot {pivot}.",
                            active=(right,), pivot=(high,), settled=tuple(settled),
                            comparisons=1, line=2)
                if arr[right] <= pivot:
                    break
                right -= 1
            if left >= right:
                break
            temp = arr[left]
            arr[left] = arr[right]
            arr[right] = temp
            yield frame(arr, "Swap the out-of-place left and right values.",
                        active=(left, right), pivot=(high,), settled=tuple(settled),
                        writes=2, swap=(left, right), line=3)
            left += 1
            right -= 1
        temp = arr[left]
        arr[left] = arr[high]
        arr[high] = temp
        settled.append(left)
        yield frame(arr, f"Place pivot {pivot} at index {left}; recursively sort both sides.",
                    settled=tuple(settled), writes=2, line=4,
                    swap=(left, high) if left != high else ())
        return left

    def sort(low, high):
        if low < high:
            pivot_index = yield from partition(low, high)
            yield from sort(low, pivot_index - 1)
            yield from sort(pivot_index + 1, high)
        elif low == high:
            settled.append(low)

    yield from sort(0, len(arr) - 1)
    yield finished(arr)


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
    arr = list(values)
    n = len(arr)
    if n == 0:
        yield finished(arr)
        return
    minimum = arr[0]
    maximum = arr[0]
    for i in range(1, n):
        if arr[i] < minimum:
            minimum = arr[i]
        if arr[i] > maximum:
            maximum = arr[i]
        yield frame(arr, f"Find the range: {minimum} to {maximum}.",
                    active=(i,), comparisons=2, line=0)
    offset = 0
    if minimum < 0:
        offset = -minimum

    def count_sort(exp):
        output = [0] * n
        count = [0] * 10
        for i in range(n):
            digit = ((arr[i] + offset) // exp) % 10
            count[digit] += 1
            yield frame(arr, f"Digit place {exp}: count digit {digit} for {arr[i]}.",
                        active=(i,), line=1)
        for i in range(1, 10):
            count[i] += count[i - 1]
            yield frame(arr, f"Cumulative count through digit {i}: {count[i]} values.", line=2)
        for i in range(n - 1, -1, -1):
            digit = ((arr[i] + offset) // exp) % 10
            position = count[digit] - 1
            output[position] = arr[i]
            count[digit] -= 1
            yield frame(arr, f"Place {arr[i]} at output index {position}, scanning right to left.",
                        active=(i,), line=3)
        for i in range(n):
            arr[i] = output[i]
            yield frame(arr, f"Copy {arr[i]} back to index {i} for digit place {exp}.",
                        active=(i,), writes=1, line=4)

    exp = 1
    while (maximum + offset) // exp > 0:
        yield from count_sort(exp)
        exp *= 10
    yield finished(arr)


def linear_search(values, target):
    arr = list(values)
    n = len(arr)
    for i in range(n):
        yield frame(arr, f"Does {arr[i]} equal {target}?", active=(i,),
                    discarded=tuple(range(i)), comparisons=1, line=1)
        if arr[i] == target:
            yield frame(arr, f"Found {target} at index {i} (position {i + 1}).",
                        found=(i,), done=True, result=i, line=2)
            return
    yield frame(arr, f"{target} was not found in this array.",
                discarded=tuple(range(n)), done=True, line=4)


def binary_search(values, target):
    arr = list(values)
    n = len(arr)
    left = 0
    right = n - 1
    while left <= right:
        mid = left + (right - left) // 2
        discarded = tuple(range(left)) + tuple(range(right + 1, n))
        yield frame(arr, f"Check midpoint {mid}: compare {arr[mid]} with {target}.",
                    active=(mid,), pivot=(left, right), discarded=discarded,
                    comparisons=1, line=1)
        if arr[mid] == target:
            yield frame(arr, f"Found {target} at index {mid} in the sorted array.",
                        found=(mid,), result=mid, done=True, line=2)
            return
        yield frame(arr, f"Choose which half can contain {target}.", active=(mid,),
                    discarded=discarded, comparisons=1, line=3)
        if arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    yield frame(arr, f"{target} was not found in this array.",
                discarded=tuple(range(n)), done=True, line=4)


def interpolation_search(values, target):
    arr = list(values)
    n = len(arr)
    low = 0
    high = n - 1
    while low <= high:
        discarded = tuple(range(low)) + tuple(range(high + 1, n))
        yield frame(arr, f"Check whether {target} is below the lower bound {arr[low]}.",
                    pivot=(low, high), discarded=discarded, comparisons=1, line=0)
        if target < arr[low]:
            break
        yield frame(arr, f"Check whether {target} is above the upper bound {arr[high]}.",
                    pivot=(low, high), discarded=discarded, comparisons=1, line=0)
        if target > arr[high]:
            break
        yield frame(arr, "Check for equal endpoints before dividing.",
                    pivot=(low, high), discarded=discarded, comparisons=1, line=1)
        if arr[low] == arr[high]:
            yield frame(arr, f"Equal endpoints: found {target} at index {low}.",
                        found=(low,), result=low, done=True, line=1)
            return
        pos = low + ((target - arr[low]) * (high - low) // (arr[high] - arr[low]))
        yield frame(arr, f"Estimate index {pos}; compare {arr[pos]} with {target}.",
                    active=(pos,), pivot=(low, high), discarded=discarded,
                    comparisons=1, line=2)
        if arr[pos] == target:
            yield frame(arr, f"Found {target} at index {pos} in the sorted array.",
                        found=(pos,), result=pos, done=True, line=3)
            return
        yield frame(arr, "Narrow the interval around the estimated position.",
                    active=(pos,), discarded=discarded, comparisons=1, line=4)
        if arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
    yield frame(arr, f"{target} was not found in this array.",
                discarded=tuple(range(n)), done=True, line=5)


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
                  ("for i from 0 to n - 2", "  compare neighbors up to n - i - 1", "  swap using temp if left > right",
                   "  settle the largest value", "  stop if no swaps occurred", "return sorted array")),
        Algorithm("Selection Sort", "Sort", selection_sort,
                  "Find the smallest remaining value, then place it at the front of the unsorted region.",
                  "O(n²)", "O(n²)", "O(1)",
                  ("for i from 0 to n - 2", "  scan for the smallest value", "  update min_index",
                   "  swap arr[i] and arr[min_index]", "  advance the sorted boundary", "return sorted array")),
        Algorithm("Insertion Sort", "Sort", insertion_sort,
                  "Build an ordered prefix one value at a time, just like arranging cards in your hand.",
                  "O(n²)", "O(n²)", "O(1)",
                  ("take the next value as key", "compare key with left neighbor", "shift larger values right",
                   "insert key into the gap", "repeat for each remaining value", "return sorted array")),
        Algorithm("Shell Sort", "Sort", shell_sort,
                  "Insertion-sort distant neighbors, then halve the gap. Uses Shell's original halving sequence; costs depend on gaps.",
                  "Gap-dependent", "O(n²)", "O(1)",
                  ("start with gap = n // 2", "hold the next value in temp", "compare gap-spaced neighbors",
                   "shift larger values by the gap", "insert temp; halve gap and repeat", "return sorted array")),
        Algorithm("Comb Sort", "Sort", comb_sort,
                  "Swap distant out-of-order pairs. Shrink the gap by 1.3, then repeat gap 1 until a pass makes no swaps.",
                  "Gap-dependent", "O(n²)", "O(1)",
                  ("shrink gap by 1.3; minimum 1", "compare values a gap apart", "swap if they are out of order",
                   "repeat until gap 1 has no swaps", "all neighboring pairs are ordered", "return sorted array")),
        Algorithm("Merge Sort", "Sort", merge_sort,
                  "Recursively split the array into halves. Merge them using two temporary arrays and copy any leftovers.",
                  "O(n log n)", "O(n log n)", "O(n)",
                  ("split at mid; recursively sort halves", "copy halves into left/right arrays", "compare the two front values",
                   "write the smaller value; advance", "copy the remaining values", "return sorted array")),
        Algorithm("Quick Sort", "Sort", quick_sort,
                  "Use the last value as pivot. Scan inward from both sides, swap misplaced values, then recursively sort both partitions.",
                  "O(n log n)", "O(n²)", "O(n)",
                  ("pivot = last value; set left/right", "scan left while value < pivot", "scan right while value > pivot",
                   "swap misplaced values; move inward", "place pivot; recursively sort sides", "return sorted array")),
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
                  "Counting-sort each digit: count, accumulate, fill output from right to left, then copy back. Offset negative keys. d is digit count.",
                  "O(d · n)", "O(d · n)", "O(n)",
                  ("find range; offset negative keys", "count the digit at exp = 1, 10, ...", "accumulate the ten digit counts",
                   "fill output from right to left", "copy output back; exp *= 10", "return sorted array")),
        Algorithm("Linear Search", "Search", linear_search,
                  "Check values from left to right. Return the first match; no ordering is required.",
                  "O(n)", "O(n)", "O(1)",
                  ("start at the first value", "compare current value to target", "if equal: return its index",
                   "otherwise move to next value", "if exhausted: target not found", "search complete")),
        Algorithm("Binary Search", "Search", binary_search,
                  "Check the middle of the sorted range and stop at a match. With duplicates, the match need not be the first occurrence.",
                  "O(log n)", "O(log n)", "O(1)",
                  ("left = 0; right = n - 1", "mid = left + (right - left) // 2", "on match: return mid immediately",
                   "move left or right past mid", "if range is empty: not found", "indices refer to sorted input")),
        Algorithm("Interpolation Search", "Search", interpolation_search,
                  "Estimate a position from endpoint values and stop at a match, which need not be the first duplicate. Average O(log log n) assumes uniform distinct keys.",
                  "O(log log n)*", "O(n)", "O(1)",
                  ("check target within endpoint range", "handle equal endpoints safely",
                   "estimate index; compare to target", "on match: return pos immediately",
                   "otherwise narrow the interval", "outside the range: not found")),
    )
}
