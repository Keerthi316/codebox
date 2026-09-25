"""Built-in problem set. Problems use stdin/stdout I/O so they work in every language.

Expected outputs are computed by the reference solvers below, so hidden test data
is correct by construction. Seeding is idempotent (upsert by slug).
"""

import random
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Problem, TestCase
from .extra_problems import EXTRA_PROBLEMS, EXTRA_STARTER_CODE, build_extra_tests

# --------------------------------------------------------------------------- solvers


def _two_sum(inp: str) -> str:
    data = list(map(int, inp.split()))
    n, nums, target = data[0], data[1:1 + data[0]], data[1 + data[0]]
    seen = {}
    for i, value in enumerate(nums):
        if target - value in seen:
            return f"{seen[target - value]} {i}"
        seen[value] = i
    raise ValueError("no solution")


def _reverse(inp: str) -> str:
    return inp.rstrip("\n")[::-1]


def _valid_parens(inp: str) -> str:
    pairs, stack = {")": "(", "]": "[", "}": "{"}, []
    for ch in inp.strip():
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return "false"
        else:
            stack.append(ch)
    return "true" if not stack else "false"


def _max_subarray(inp: str) -> str:
    nums = list(map(int, inp.split()))[1:]
    best = current = nums[0]
    for value in nums[1:]:
        current = max(value, current + value)
        best = max(best, current)
    return str(best)


def _binary_search(inp: str) -> str:
    data = list(map(int, inp.split()))
    n, nums, target = data[0], data[1:1 + data[0]], data[1 + data[0]]
    return str(nums.index(target)) if target in nums else "-1"


# ------------------------------------------------------------------- input builders


def _arr(nums, *extra) -> str:
    lines = [str(len(nums)), " ".join(map(str, nums))] + [str(e) for e in extra]
    return "\n".join(lines) + "\n"


def _two_sum_large(rng: random.Random) -> str:
    while True:
        nums = rng.sample(range(-10**9, 10**9), 10_000)
        i, j = sorted(rng.sample(range(len(nums)), 2))
        target = nums[i] + nums[j]
        values = set(nums)
        pairs = sum(1 for v in nums if target - v in values and target - v != v) // 2
        if pairs == 1:
            return _arr(nums, target)


def _binary_search_large(rng: random.Random, present: bool) -> str:
    nums = sorted(rng.sample(range(-10**9, 10**9), 100_000))
    target = rng.choice(nums) if present else nums[0] - 1
    return _arr(nums, target)


def _build_tests():
    rng = random.Random(20240601)
    return {
        "two-sum": [
            _arr([2, 7, 11, 15], 9),
            _arr([3, 2, 4], 6),
            _arr([3, 3], 6),
            _arr([-1, -2, -3, -4, -5], -8),
            _arr([0, 4, 3, 0], 0),
            _two_sum_large(rng),
        ],
        "reverse-string": [
            "hello\n",
            "Hannah\n",
            "a\n",
            "A man, a plan\n",
            "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(100_000)) + "\n",
        ],
        "valid-parentheses": [
            "()[]{}\n", "()\n", "(]\n", "([)]\n", "{[]}\n", "(((\n",
            "([{}])" * 10_000 + "\n",
            "(" * 50_000 + ")" * 49_999 + "\n",
        ],
        "maximum-subarray": [
            _arr([-2, 1, -3, 4, -1, 2, 1, -5, 4]),
            _arr([1]),
            _arr([5, 4, -1, 7, 8]),
            _arr([-3, -2, -5, -1]),
            _arr([rng.randint(-10_000, 10_000) for _ in range(100_000)]),
        ],
        "binary-search": [
            _arr([-1, 0, 3, 5, 9, 12], 9),
            _arr([-1, 0, 3, 5, 9, 12], 2),
            _arr([5], 5),
            _arr([1, 3], 3),
            _binary_search_large(rng, True),
            _binary_search_large(rng, False),
        ],
    }


# ------------------------------------------------------------------- starter code

_ARRAY_TARGET_READERS = {
    "python": "    data = sys.stdin.read().split()\n    n = int(data[0])\n    nums = list(map(int, data[1:1 + n]))\n    target = int(data[1 + n])\n",
    "javascript": "const data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\nconst n = data[0];\nconst nums = data.slice(1, 1 + n);\nconst target = data[1 + n];\n",
    "java": "        StreamTokenizer in = new StreamTokenizer(new BufferedReader(new InputStreamReader(System.in)));\n        in.nextToken(); int n = (int) in.nval;\n        int[] nums = new int[n];\n        for (int i = 0; i < n; i++) { in.nextToken(); nums[i] = (int) in.nval; }\n        in.nextToken(); int target = (int) in.nval;\n",
    "cpp": "    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    int n;\n    cin >> n;\n    vector<int> nums(n);\n    for (auto& x : nums) cin >> x;\n    int target;\n    cin >> target;\n",
}

STARTER_CODE = {
    "two-sum": {
        "python": "import sys\n\n\ndef two_sum(nums: list[int], target: int) -> tuple[int, int]:\n    # Return the indices (i < j) of the two numbers that add up to target.\n    return -1, -1\n\n\ndef main() -> None:\n" + _ARRAY_TARGET_READERS["python"] + "    i, j = two_sum(nums, target)\n    print(i, j)\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "javascript": "function twoSum(nums, target) {\n  // Return the indices [i, j] (i < j) of the two numbers that add up to target.\n  return [-1, -1];\n}\n\n" + _ARRAY_TARGET_READERS["javascript"] + "console.log(twoSum(nums, target).join(' '));\n",
        "java": "import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    static int[] twoSum(int[] nums, int target) {\n        // Return the indices {i, j} (i < j) of the two numbers that add up to target.\n        return new int[]{-1, -1};\n    }\n\n    public static void main(String[] args) throws IOException {\n" + _ARRAY_TARGET_READERS["java"] + "        int[] ans = twoSum(nums, target);\n        System.out.println(ans[0] + \" \" + ans[1]);\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\npair<int, int> twoSum(const vector<int>& nums, int target) {\n    // Return the indices (i < j) of the two numbers that add up to target.\n    return {-1, -1};\n}\n\nint main() {\n" + _ARRAY_TARGET_READERS["cpp"] + "    auto [i, j] = twoSum(nums, target);\n    cout << i << ' ' << j << '\\n';\n}\n",
    },
    "reverse-string": {
        "python": "import sys\n\n\ndef reverse_string(s: str) -> str:\n    # Return s reversed.\n    return s\n\n\ndef main() -> None:\n    s = sys.stdin.readline().rstrip(\"\\r\\n\")\n    print(reverse_string(s))\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "javascript": "function reverseString(s) {\n  // Return s reversed.\n  return s;\n}\n\nconst s = require('fs').readFileSync(0, 'utf8').split('\\n')[0].replace(/\\r$/, '');\nconsole.log(reverseString(s));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static String reverseString(String s) {\n        // Return s reversed.\n        return s;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        String s = in.readLine();\n        System.out.println(reverseString(s == null ? \"\" : s));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nstring reverseString(string s) {\n    // Return s reversed.\n    return s;\n}\n\nint main() {\n    string s;\n    getline(cin, s);\n    if (!s.empty() && s.back() == '\\r') s.pop_back();\n    cout << reverseString(s) << '\\n';\n}\n",
    },
    "valid-parentheses": {
        "python": "import sys\n\n\ndef is_valid(s: str) -> bool:\n    # Return True if the brackets in s are balanced and properly nested.\n    return False\n\n\ndef main() -> None:\n    s = sys.stdin.readline().strip()\n    print(\"true\" if is_valid(s) else \"false\")\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "javascript": "function isValid(s) {\n  // Return true if the brackets in s are balanced and properly nested.\n  return false;\n}\n\nconst s = require('fs').readFileSync(0, 'utf8').trim();\nconsole.log(isValid(s) ? 'true' : 'false');\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static boolean isValid(String s) {\n        // Return true if the brackets in s are balanced and properly nested.\n        return false;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        String s = in.readLine();\n        System.out.println(isValid(s == null ? \"\" : s.trim()) ? \"true\" : \"false\");\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nbool isValid(const string& s) {\n    // Return true if the brackets in s are balanced and properly nested.\n    return false;\n}\n\nint main() {\n    string s;\n    cin >> s;\n    cout << (isValid(s) ? \"true\" : \"false\") << '\\n';\n}\n",
    },
    "maximum-subarray": {
        "python": "import sys\n\n\ndef max_subarray(nums: list[int]) -> int:\n    # Return the largest sum of a non-empty contiguous subarray.\n    return 0\n\n\ndef main() -> None:\n    data = sys.stdin.read().split()\n    n = int(data[0])\n    nums = list(map(int, data[1:1 + n]))\n    print(max_subarray(nums))\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "javascript": "function maxSubArray(nums) {\n  // Return the largest sum of a non-empty contiguous subarray.\n  return 0;\n}\n\nconst data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\nconst nums = data.slice(1, 1 + data[0]);\nconsole.log(maxSubArray(nums));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static long maxSubArray(int[] nums) {\n        // Return the largest sum of a non-empty contiguous subarray.\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n        StreamTokenizer in = new StreamTokenizer(new BufferedReader(new InputStreamReader(System.in)));\n        in.nextToken(); int n = (int) in.nval;\n        int[] nums = new int[n];\n        for (int i = 0; i < n; i++) { in.nextToken(); nums[i] = (int) in.nval; }\n        System.out.println(maxSubArray(nums));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nlong long maxSubArray(const vector<int>& nums) {\n    // Return the largest sum of a non-empty contiguous subarray.\n    return 0;\n}\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    int n;\n    cin >> n;\n    vector<int> nums(n);\n    for (auto& x : nums) cin >> x;\n    cout << maxSubArray(nums) << '\\n';\n}\n",
    },
    "binary-search": {
        "python": "import sys\n\n\ndef search(nums: list[int], target: int) -> int:\n    # nums is sorted ascending with distinct values. Return target's index or -1.\n    return -1\n\n\ndef main() -> None:\n" + _ARRAY_TARGET_READERS["python"] + "    print(search(nums, target))\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "javascript": "function search(nums, target) {\n  // nums is sorted ascending with distinct values. Return target's index or -1.\n  return -1;\n}\n\n" + _ARRAY_TARGET_READERS["javascript"] + "console.log(search(nums, target));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static int search(int[] nums, int target) {\n        // nums is sorted ascending with distinct values. Return target's index or -1.\n        return -1;\n    }\n\n    public static void main(String[] args) throws IOException {\n" + _ARRAY_TARGET_READERS["java"] + "        System.out.println(search(nums, target));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint search(const vector<int>& nums, int target) {\n    // nums is sorted ascending with distinct values. Return target's index or -1.\n    return -1;\n}\n\nint main() {\n" + _ARRAY_TARGET_READERS["cpp"] + "    cout << search(nums, target) << '\\n';\n}\n",
    },
}

# -------------------------------------------------------------------- problems

PROBLEMS = [
    {
        "slug": "two-sum",
        "tags": ["Array", "Hash Table"],
        "title": "Two Sum",
        "difficulty": "Easy",
        "solver": _two_sum,
        "description": (
            "Given an array of integers `nums` and an integer `target`, return the indices of "
            "the two numbers such that they add up to `target`.\n\n"
            "Each input has **exactly one** solution, and you may not use the same element twice. "
            "Print the two indices `i j` with `i < j`.\n\n"
            "### Input format\n"
            "- Line 1: `n`, the length of the array\n"
            "- Line 2: `n` space-separated integers\n"
            "- Line 3: `target`\n\n"
            "### Output format\n"
            "Two 0-based indices separated by a space."
        ),
        "constraints": "- 2 ≤ n ≤ 10^4\n- -10^9 ≤ nums[i] ≤ 10^9\n- -10^9 ≤ target ≤ 10^9\n- Exactly one valid answer exists",
        "examples": [
            {"input": "4\n2 7 11 15\n9", "output": "0 1",
             "explanation": "nums[0] + nums[1] = 2 + 7 = 9"},
            {"input": "3\n3 2 4\n6", "output": "1 2", "explanation": None},
        ],
    },
    {
        "slug": "reverse-string",
        "tags": ["String", "Two Pointers"],
        "title": "Reverse String",
        "difficulty": "Easy",
        "solver": _reverse,
        "description": (
            "Given a single line of text `s`, print it reversed.\n\n"
            "Every character counts, including spaces and punctuation.\n\n"
            "### Input format\nA single line containing `s`.\n\n"
            "### Output format\nThe reversed string."
        ),
        "constraints": "- 1 ≤ |s| ≤ 10^5\n- s consists of printable ASCII characters",
        "examples": [
            {"input": "hello", "output": "olleh", "explanation": None},
            {"input": "Hannah", "output": "hannaH", "explanation": None},
        ],
    },
    {
        "slug": "valid-parentheses",
        "tags": ["String", "Stack"],
        "title": "Valid Parentheses",
        "difficulty": "Easy",
        "solver": _valid_parens,
        "description": (
            "Given a string `s` containing only the characters `(`, `)`, `{`, `}`, `[` and `]`, "
            "determine whether it is valid.\n\n"
            "A string is valid if:\n"
            "1. Open brackets are closed by the same type of bracket.\n"
            "2. Open brackets are closed in the correct order.\n"
            "3. Every close bracket has a corresponding open bracket.\n\n"
            "### Input format\nA single line containing `s`.\n\n"
            "### Output format\n`true` or `false`."
        ),
        "constraints": "- 1 ≤ |s| ≤ 10^5\n- s consists of `()[]{}` only",
        "examples": [
            {"input": "()[]{}", "output": "true", "explanation": None},
            {"input": "(]", "output": "false", "explanation": "The ( is closed by the wrong bracket type."},
        ],
    },
    {
        "slug": "maximum-subarray",
        "tags": ["Array", "Dynamic Programming"],
        "title": "Maximum Subarray",
        "difficulty": "Medium",
        "solver": _max_subarray,
        "description": (
            "Given an integer array `nums`, find the contiguous subarray (containing at least one "
            "number) with the largest sum and print that sum.\n\n"
            "An O(n) solution exists. Can you find it?\n\n"
            "### Input format\n"
            "- Line 1: `n`\n- Line 2: `n` space-separated integers\n\n"
            "### Output format\nThe maximum subarray sum."
        ),
        "constraints": "- 1 ≤ n ≤ 10^5\n- -10^4 ≤ nums[i] ≤ 10^4",
        "examples": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "output": "6",
             "explanation": "The subarray [4, -1, 2, 1] has the largest sum, 6."},
            {"input": "5\n5 4 -1 7 8", "output": "23", "explanation": None},
        ],
    },
    {
        "slug": "binary-search",
        "tags": ["Array", "Binary Search"],
        "title": "Binary Search",
        "difficulty": "Easy",
        "solver": _binary_search,
        "description": (
            "Given a sorted (ascending) array of **distinct** integers `nums` and an integer "
            "`target`, print the index of `target` in `nums`, or `-1` if it is not present.\n\n"
            "Your algorithm must run in O(log n) time.\n\n"
            "### Input format\n"
            "- Line 1: `n`\n- Line 2: `n` sorted integers\n- Line 3: `target`\n\n"
            "### Output format\nThe 0-based index of target, or `-1`."
        ),
        "constraints": "- 1 ≤ n ≤ 10^5\n- -10^9 < nums[i], target < 10^9\n- All values in nums are distinct",
        "examples": [
            {"input": "6\n-1 0 3 5 9 12\n9", "output": "4", "explanation": "9 exists in nums at index 4."},
            {"input": "6\n-1 0 3 5 9 12\n2", "output": "-1", "explanation": "2 does not exist in nums."},
        ],
    },
]


PROBLEMS += EXTRA_PROBLEMS
STARTER_CODE.update(EXTRA_STARTER_CODE)


@lru_cache(maxsize=1)
def all_tests() -> dict:
    """Test inputs are generated from fixed seeds, so build them once per process."""
    return {**_build_tests(), **build_extra_tests()}


def seed_problems(db: Session) -> None:
    tests_by_slug = all_tests()
    for spec in PROBLEMS:
        slug = spec["slug"]
        problem = db.scalar(select(Problem).where(Problem.slug == slug))
        if problem is None:
            problem = Problem(slug=slug)
            db.add(problem)
        problem.title = spec["title"]
        problem.difficulty = spec["difficulty"]
        problem.tags = spec["tags"]
        problem.description = spec["description"]
        problem.constraints = spec["constraints"]
        problem.examples = spec["examples"]
        problem.starter_code = STARTER_CODE[slug]
        problem.test_cases.clear()
        db.flush()
        for position, test_input in enumerate(tests_by_slug[slug]):
            problem.test_cases.append(TestCase(
                position=position,
                input=test_input,
                expected_output=spec["solver"](test_input) + "\n",
                is_sample=position == 0,  # first case mirrors example 1
            ))
    db.commit()
