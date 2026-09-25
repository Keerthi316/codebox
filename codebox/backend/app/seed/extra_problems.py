"""Problems 6-15. Same conventions as problems.py: stdin/stdout I/O, expected outputs
computed by the reference solvers, first test case mirrors example 1."""

import random
from collections import deque

# --------------------------------------------------------------------------- solvers


def _fizz_buzz(inp: str) -> str:
    n = int(inp)
    return "\n".join(("Fizz" if i % 3 == 0 else "") + ("Buzz" if i % 5 == 0 else "") or str(i)
                     for i in range(1, n + 1))


def _valid_palindrome(inp: str) -> str:
    cleaned = [c.lower() for c in inp.rstrip("\r\n") if c.isascii() and c.isalnum()]
    return "true" if cleaned == cleaned[::-1] else "false"


def _climbing_stairs(inp: str) -> str:
    a, b = 1, 1
    for _ in range(int(inp)):
        a, b = b, a + b
    return str(a)


def _max_profit(inp: str) -> str:
    prices = list(map(int, inp.split()))[1:]
    best, low = 0, prices[0]
    for p in prices:
        low = min(low, p)
        best = max(best, p - low)
    return str(best)


def _contains_duplicate(inp: str) -> str:
    nums = inp.split()[1:]
    return "true" if len(set(nums)) != len(nums) else "false"


def _longest_substring(inp: str) -> str:
    s = inp.rstrip("\r\n")
    last, start, best = {}, 0, 0
    for i, c in enumerate(s):
        if last.get(c, -1) >= start:
            start = last[c] + 1
        last[c] = i
        best = max(best, i - start + 1)
    return str(best)


def _num_islands(inp: str) -> str:
    data = inp.split()
    m, n = int(data[0]), int(data[1])
    grid = [list(row) for row in data[2:2 + m]]
    count = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] != "1":
                continue
            count += 1
            grid[r][c] = "0"
            queue = deque([(r, c)])
            while queue:
                y, x = queue.popleft()
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < m and 0 <= nx < n and grid[ny][nx] == "1":
                        grid[ny][nx] = "0"
                        queue.append((ny, nx))
    return str(count)


def _coin_change(inp: str) -> str:
    data = list(map(int, inp.split()))
    k = data[0]
    coins, amount = data[1:1 + k], data[1 + k]
    inf = amount + 1
    dp = [0] + [inf] * amount
    for a in range(1, amount + 1):
        for coin in coins:
            if coin <= a and dp[a - coin] + 1 < dp[a]:
                dp[a] = dp[a - coin] + 1
    return str(dp[amount] if dp[amount] <= amount else -1)


def _trap(inp: str) -> str:
    h = list(map(int, inp.split()))[1:]
    left, right, left_max, right_max, water = 0, len(h) - 1, 0, 0, 0
    while left < right:
        if h[left] < h[right]:
            left_max = max(left_max, h[left])
            water += left_max - h[left]
            left += 1
        else:
            right_max = max(right_max, h[right])
            water += right_max - h[right]
            right -= 1
    return str(water)


def _edit_distance(inp: str) -> str:
    lines = inp.split("\n")
    a, b = lines[0].rstrip("\r"), (lines[1] if len(lines) > 1 else "").rstrip("\r")
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = prev[j - 1] if ca == cb else 1 + min(prev[j - 1], prev[j], cur[j - 1])
        prev = cur
    return str(prev[-1])


# ------------------------------------------------------------------- input builders


def _arr(nums, *extra) -> str:
    return "\n".join([str(len(nums)), " ".join(map(str, nums))] + [str(e) for e in extra]) + "\n"


def _grid(rows) -> str:
    return f"{len(rows)} {len(rows[0])}\n" + "\n".join(rows) + "\n"


def _noisy_palindrome(rng: random.Random, n: int, palindrome: bool) -> str:
    half = [rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n // 2)]
    core = half + half[::-1]
    if not palindrome:  # change one character so it no longer matches its mirror
        i = len(core) // 3
        core[i] = "a" if core[i] != "a" else "b"
    out = []
    for ch in core:
        out.append(ch.upper() if rng.random() < 0.3 else ch)
        if rng.random() < 0.15:
            out.append(rng.choice(" ,.:;!?-'"))
    return "".join(out) + "\n"


def build_extra_tests():
    rng = random.Random(20260926)
    letters = "abcdefghijklmnopqrstuvwxyz"
    return {
        "fizz-buzz": ["5\n", "1\n", "3\n", "15\n", "100\n", "10000\n"],
        "valid-palindrome": [
            "A man, a plan, a canal: Panama\n", "race a car\n", " \n", "0P\n", "ab_a\n",
            _noisy_palindrome(rng, 100_000, True), _noisy_palindrome(rng, 100_000, False),
        ],
        "climbing-stairs": ["2\n", "3\n", "1\n", "5\n", "10\n", "45\n"],
        "best-time-to-buy-and-sell-stock": [
            _arr([7, 1, 5, 3, 6, 4]), _arr([7, 6, 4, 3, 1]), _arr([5]), _arr([1, 2]),
            _arr([rng.randint(0, 10_000) for _ in range(100_000)]),
            _arr(list(range(100_000, 0, -1))),
        ],
        "contains-duplicate": [
            _arr([1, 2, 3, 1]), _arr([1, 2, 3, 4]), _arr([1, 1, 1, 3, 3, 4, 3, 2, 4, 2]), _arr([5]),
            _arr(rng.sample(range(-10**9, 10**9), 100_000)),
            _arr((lambda v: v + [v[rng.randrange(len(v))]])(rng.sample(range(-10**9, 10**9), 99_999))),
        ],
        "longest-substring-without-repeating-characters": [
            "abcabcbb\n", "bbbbb\n", "pwwkew\n", "dvdf\n", "a\n", "abba\n",
            "".join(rng.choice(letters) for _ in range(50_000)) + "\n",
            "".join(chr(33 + i % 94) for i in range(50_000)) + "\n",
        ],
        "number-of-islands": [
            _grid(["11110", "11010", "11000", "00000"]),
            _grid(["11000", "11000", "00100", "00011"]),
            _grid(["0"]), _grid(["1"]),
            _grid(["".join("1" if (r + c) % 2 == 0 else "0" for c in range(50)) for r in range(50)]),
            _grid(["".join("1" if rng.random() < 0.45 else "0" for _ in range(300)) for _ in range(300)]),
            _grid(["1" * 300] * 300),
        ],
        "coin-change": [
            _arr([1, 2, 5], 11), _arr([2], 3), _arr([1], 0), _arr([186, 419, 83, 408], 6249),
            _arr(sorted(rng.sample(range(1, 500), 12)), 10_000),
            _arr([7, 13], 10_000),
        ],
        "trapping-rain-water": [
            _arr([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]), _arr([4, 2, 0, 3, 2, 5]),
            _arr([5]), _arr([1, 2, 3]),
            _arr([rng.randint(0, 10_000) for _ in range(100_000)]),
            _arr(list(range(10_000, 0, -1)) + list(range(10_000))),
        ],
        "edit-distance": [
            "horse\nros\n", "intention\nexecution\n", "\nabc\n", "same\nsame\n",
            "".join(rng.choice("abcd") for _ in range(500)) + "\n"
            + "".join(rng.choice("abcd") for _ in range(500)) + "\n",
            "".join(rng.choice(letters) for _ in range(400)) + "\n"
            + "".join(rng.choice(letters) for _ in range(300)) + "\n",
        ],
    }


# ------------------------------------------------------------------- starter code

_READ_ARRAY = {
    "python": "    data = sys.stdin.read().split()\n    n = int(data[0])\n    nums = list(map(int, data[1:1 + n]))\n",
    "javascript": "const data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\nconst nums = data.slice(1, 1 + data[0]);\n",
    "java": "        StreamTokenizer in = new StreamTokenizer(new BufferedReader(new InputStreamReader(System.in)));\n        in.nextToken(); int n = (int) in.nval;\n        int[] nums = new int[n];\n        for (int i = 0; i < n; i++) { in.nextToken(); nums[i] = (int) in.nval; }\n",
    "cpp": "    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    int n;\n    cin >> n;\n    vector<int> nums(n);\n    for (auto& x : nums) cin >> x;\n",
}


def _py(signature: str, doc: str, stub: str, body: str) -> str:
    return f"import sys\n\n\n{signature}\n    # {doc}\n{stub}\n\ndef main() -> None:\n{body}\n\nif __name__ == \"__main__\":\n    main()\n"


EXTRA_STARTER_CODE = {
    "fizz-buzz": {
        "python": _py("def fizz_buzz(n: int) -> list[str]:", "Return the FizzBuzz sequence for 1..n.", "    return []\n",
                      "    n = int(sys.stdin.readline())\n    print(\"\\n\".join(fizz_buzz(n)))\n"),
        "javascript": "function fizzBuzz(n) {\n  // Return the FizzBuzz sequence for 1..n as an array of strings.\n  return [];\n}\n\nconst n = Number(require('fs').readFileSync(0, 'utf8').trim());\nconsole.log(fizzBuzz(n).join('\\n'));\n",
        "java": "import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    static List<String> fizzBuzz(int n) {\n        // Return the FizzBuzz sequence for 1..n.\n        return new ArrayList<>();\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        int n = Integer.parseInt(in.readLine().trim());\n        System.out.println(String.join(\"\\n\", fizzBuzz(n)));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nvector<string> fizzBuzz(int n) {\n    // Return the FizzBuzz sequence for 1..n.\n    return {};\n}\n\nint main() {\n    int n;\n    cin >> n;\n    string out;\n    for (const string& s : fizzBuzz(n)) out += s + '\\n';\n    cout << out;\n}\n",
    },
    "valid-palindrome": {
        "python": _py("def is_palindrome(s: str) -> bool:", "Compare only letters and digits, ignoring case.", "    return False\n",
                      "    s = sys.stdin.readline().rstrip(\"\\r\\n\")\n    print(\"true\" if is_palindrome(s) else \"false\")\n"),
        "javascript": "function isPalindrome(s) {\n  // Compare only letters and digits, ignoring case.\n  return false;\n}\n\nconst s = require('fs').readFileSync(0, 'utf8').split('\\n')[0].replace(/\\r$/, '');\nconsole.log(isPalindrome(s) ? 'true' : 'false');\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static boolean isPalindrome(String s) {\n        // Compare only letters and digits, ignoring case.\n        return false;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        String s = in.readLine();\n        System.out.println(isPalindrome(s == null ? \"\" : s) ? \"true\" : \"false\");\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nbool isPalindrome(const string& s) {\n    // Compare only letters and digits, ignoring case.\n    return false;\n}\n\nint main() {\n    string s;\n    getline(cin, s);\n    if (!s.empty() && s.back() == '\\r') s.pop_back();\n    cout << (isPalindrome(s) ? \"true\" : \"false\") << '\\n';\n}\n",
    },
    "climbing-stairs": {
        "python": _py("def climb_stairs(n: int) -> int:", "Number of distinct ways to climb n steps taking 1 or 2 at a time.", "    return 0\n",
                      "    print(climb_stairs(int(sys.stdin.readline())))\n"),
        "javascript": "function climbStairs(n) {\n  // Number of distinct ways to climb n steps taking 1 or 2 at a time.\n  return 0;\n}\n\nconsole.log(climbStairs(Number(require('fs').readFileSync(0, 'utf8').trim())));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static long climbStairs(int n) {\n        // Number of distinct ways to climb n steps taking 1 or 2 at a time.\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        System.out.println(climbStairs(Integer.parseInt(in.readLine().trim())));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nlong long climbStairs(int n) {\n    // Number of distinct ways to climb n steps taking 1 or 2 at a time.\n    return 0;\n}\n\nint main() {\n    int n;\n    cin >> n;\n    cout << climbStairs(n) << '\\n';\n}\n",
    },
    "best-time-to-buy-and-sell-stock": {
        "python": _py("def max_profit(prices: list[int]) -> int:", "Best profit from one buy followed by one sell (0 if none).", "    return 0\n",
                      _READ_ARRAY["python"] + "    print(max_profit(nums))\n"),
        "javascript": "function maxProfit(prices) {\n  // Best profit from one buy followed by one sell (0 if none).\n  return 0;\n}\n\n" + _READ_ARRAY["javascript"] + "console.log(maxProfit(nums));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static int maxProfit(int[] prices) {\n        // Best profit from one buy followed by one sell (0 if none).\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n" + _READ_ARRAY["java"] + "        System.out.println(maxProfit(nums));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint maxProfit(const vector<int>& prices) {\n    // Best profit from one buy followed by one sell (0 if none).\n    return 0;\n}\n\nint main() {\n" + _READ_ARRAY["cpp"] + "    cout << maxProfit(nums) << '\\n';\n}\n",
    },
    "contains-duplicate": {
        "python": _py("def contains_duplicate(nums: list[int]) -> bool:", "True if any value appears at least twice.", "    return False\n",
                      _READ_ARRAY["python"] + "    print(\"true\" if contains_duplicate(nums) else \"false\")\n"),
        "javascript": "function containsDuplicate(nums) {\n  // True if any value appears at least twice.\n  return false;\n}\n\n" + _READ_ARRAY["javascript"] + "console.log(containsDuplicate(nums) ? 'true' : 'false');\n",
        "java": "import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    static boolean containsDuplicate(int[] nums) {\n        // True if any value appears at least twice.\n        return false;\n    }\n\n    public static void main(String[] args) throws IOException {\n" + _READ_ARRAY["java"] + "        System.out.println(containsDuplicate(nums) ? \"true\" : \"false\");\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nbool containsDuplicate(const vector<int>& nums) {\n    // True if any value appears at least twice.\n    return false;\n}\n\nint main() {\n" + _READ_ARRAY["cpp"] + "    cout << (containsDuplicate(nums) ? \"true\" : \"false\") << '\\n';\n}\n",
    },
    "longest-substring-without-repeating-characters": {
        "python": _py("def length_of_longest_substring(s: str) -> int:", "Length of the longest substring with no repeated character.", "    return 0\n",
                      "    s = sys.stdin.readline().rstrip(\"\\r\\n\")\n    print(length_of_longest_substring(s))\n"),
        "javascript": "function lengthOfLongestSubstring(s) {\n  // Length of the longest substring with no repeated character.\n  return 0;\n}\n\nconst s = require('fs').readFileSync(0, 'utf8').split('\\n')[0].replace(/\\r$/, '');\nconsole.log(lengthOfLongestSubstring(s));\n",
        "java": "import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    static int lengthOfLongestSubstring(String s) {\n        // Length of the longest substring with no repeated character.\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        String s = in.readLine();\n        System.out.println(lengthOfLongestSubstring(s == null ? \"\" : s));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint lengthOfLongestSubstring(const string& s) {\n    // Length of the longest substring with no repeated character.\n    return 0;\n}\n\nint main() {\n    string s;\n    getline(cin, s);\n    if (!s.empty() && s.back() == '\\r') s.pop_back();\n    cout << lengthOfLongestSubstring(s) << '\\n';\n}\n",
    },
    "number-of-islands": {
        "python": _py("def num_islands(grid: list[list[str]]) -> int:", "Count groups of '1' cells connected up/down/left/right.", "    return 0\n",
                      "    data = sys.stdin.read().split()\n    m = int(data[0])\n    grid = [list(row) for row in data[2:2 + m]]\n    print(num_islands(grid))\n"),
        "javascript": "function numIslands(grid) {\n  // Count groups of '1' cells connected up/down/left/right.\n  return 0;\n}\n\nconst data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/);\nconst m = Number(data[0]);\nconst grid = data.slice(2, 2 + m).map((row) => row.split(''));\nconsole.log(numIslands(grid));\n",
        "java": "import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    static int numIslands(char[][] grid) {\n        // Count groups of '1' cells connected up/down/left/right.\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        StringTokenizer st = new StringTokenizer(in.readLine());\n        int m = Integer.parseInt(st.nextToken());\n        char[][] grid = new char[m][];\n        for (int i = 0; i < m; i++) grid[i] = in.readLine().trim().toCharArray();\n        System.out.println(numIslands(grid));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint numIslands(vector<string>& grid) {\n    // Count groups of '1' cells connected up/down/left/right.\n    return 0;\n}\n\nint main() {\n    int m, n;\n    cin >> m >> n;\n    vector<string> grid(m);\n    for (auto& row : grid) cin >> row;\n    cout << numIslands(grid) << '\\n';\n}\n",
    },
    "coin-change": {
        "python": _py("def coin_change(coins: list[int], amount: int) -> int:", "Fewest coins that make up amount, or -1 if impossible.", "    return -1\n",
                      "    data = sys.stdin.read().split()\n    k = int(data[0])\n    coins = list(map(int, data[1:1 + k]))\n    amount = int(data[1 + k])\n    print(coin_change(coins, amount))\n"),
        "javascript": "function coinChange(coins, amount) {\n  // Fewest coins that make up amount, or -1 if impossible.\n  return -1;\n}\n\nconst data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\nconst coins = data.slice(1, 1 + data[0]);\nconsole.log(coinChange(coins, data[1 + data[0]]));\n",
        "java": "import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    static int coinChange(int[] coins, int amount) {\n        // Fewest coins that make up amount, or -1 if impossible.\n        return -1;\n    }\n\n    public static void main(String[] args) throws IOException {\n        StreamTokenizer in = new StreamTokenizer(new BufferedReader(new InputStreamReader(System.in)));\n        in.nextToken(); int k = (int) in.nval;\n        int[] coins = new int[k];\n        for (int i = 0; i < k; i++) { in.nextToken(); coins[i] = (int) in.nval; }\n        in.nextToken(); int amount = (int) in.nval;\n        System.out.println(coinChange(coins, amount));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint coinChange(const vector<int>& coins, int amount) {\n    // Fewest coins that make up amount, or -1 if impossible.\n    return -1;\n}\n\nint main() {\n    int k;\n    cin >> k;\n    vector<int> coins(k);\n    for (auto& c : coins) cin >> c;\n    int amount;\n    cin >> amount;\n    cout << coinChange(coins, amount) << '\\n';\n}\n",
    },
    "trapping-rain-water": {
        "python": _py("def trap(height: list[int]) -> int:", "Total units of water trapped between the bars.", "    return 0\n",
                      _READ_ARRAY["python"] + "    print(trap(nums))\n"),
        "javascript": "function trap(height) {\n  // Total units of water trapped between the bars.\n  return 0;\n}\n\n" + _READ_ARRAY["javascript"] + "console.log(trap(nums));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static long trap(int[] height) {\n        // Total units of water trapped between the bars.\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n" + _READ_ARRAY["java"] + "        System.out.println(trap(nums));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nlong long trap(const vector<int>& height) {\n    // Total units of water trapped between the bars.\n    return 0;\n}\n\nint main() {\n" + _READ_ARRAY["cpp"] + "    cout << trap(nums) << '\\n';\n}\n",
    },
    "edit-distance": {
        "python": _py("def min_distance(word1: str, word2: str) -> int:", "Minimum inserts, deletes and replacements to turn word1 into word2.", "    return 0\n",
                      "    lines = sys.stdin.read().split(\"\\n\")\n    word1 = lines[0].rstrip(\"\\r\")\n    word2 = lines[1].rstrip(\"\\r\") if len(lines) > 1 else \"\"\n    print(min_distance(word1, word2))\n"),
        "javascript": "function minDistance(word1, word2) {\n  // Minimum inserts, deletes and replacements to turn word1 into word2.\n  return 0;\n}\n\nconst lines = require('fs').readFileSync(0, 'utf8').split('\\n').map((l) => l.replace(/\\r$/, ''));\nconsole.log(minDistance(lines[0] ?? '', lines[1] ?? ''));\n",
        "java": "import java.io.*;\n\npublic class Main {\n    static int minDistance(String word1, String word2) {\n        // Minimum inserts, deletes and replacements to turn word1 into word2.\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        String a = in.readLine(), b = in.readLine();\n        System.out.println(minDistance(a == null ? \"\" : a, b == null ? \"\" : b));\n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint minDistance(const string& word1, const string& word2) {\n    // Minimum inserts, deletes and replacements to turn word1 into word2.\n    return 0;\n}\n\nint main() {\n    string a, b;\n    getline(cin, a);\n    getline(cin, b);\n    if (!a.empty() && a.back() == '\\r') a.pop_back();\n    if (!b.empty() && b.back() == '\\r') b.pop_back();\n    cout << minDistance(a, b) << '\\n';\n}\n",
    },
}

# -------------------------------------------------------------------- problems

EXTRA_PROBLEMS = [
    {
        "slug": "fizz-buzz", "title": "Fizz Buzz", "difficulty": "Easy", "tags": ["Math", "String"],
        "solver": _fizz_buzz,
        "description": (
            "Given an integer `n`, print one line for each number from `1` to `n`:\n\n"
            "- `FizzBuzz` if the number is divisible by both 3 and 5\n"
            "- `Fizz` if it is divisible by 3\n"
            "- `Buzz` if it is divisible by 5\n"
            "- otherwise the number itself\n\n"
            "### Input format\nA single integer `n`.\n\n### Output format\n`n` lines."
        ),
        "constraints": "- 1 ≤ n ≤ 10^4",
        "examples": [
            {"input": "5", "output": "1\n2\nFizz\n4\nBuzz", "explanation": None},
            {"input": "15", "output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz",
             "explanation": "15 is divisible by both 3 and 5."},
        ],
    },
    {
        "slug": "valid-palindrome", "title": "Valid Palindrome", "difficulty": "Easy",
        "tags": ["String", "Two Pointers"], "solver": _valid_palindrome,
        "description": (
            "A phrase is a **palindrome** if, after converting all uppercase letters to lowercase and "
            "removing every character that is not a letter or digit, it reads the same forward and backward.\n\n"
            "Given a line of text `s`, print `true` if it is a palindrome, otherwise `false`.\n\n"
            "### Input format\nA single line containing `s`.\n\n### Output format\n`true` or `false`."
        ),
        "constraints": "- 1 ≤ |s| ≤ 2·10^5\n- s consists of printable ASCII characters",
        "examples": [
            {"input": "A man, a plan, a canal: Panama", "output": "true",
             "explanation": "\"amanaplanacanalpanama\" is a palindrome."},
            {"input": "race a car", "output": "false", "explanation": "\"raceacar\" is not a palindrome."},
        ],
    },
    {
        "slug": "climbing-stairs", "title": "Climbing Stairs", "difficulty": "Easy",
        "tags": ["Math", "Dynamic Programming"], "solver": _climbing_stairs,
        "description": (
            "You are climbing a staircase with `n` steps. Each time you can climb either **1** or **2** "
            "steps. In how many distinct ways can you reach the top?\n\n"
            "### Input format\nA single integer `n`.\n\n### Output format\nThe number of distinct ways."
        ),
        "constraints": "- 1 ≤ n ≤ 45",
        "examples": [
            {"input": "2", "output": "2", "explanation": "1 + 1, or 2."},
            {"input": "3", "output": "3", "explanation": "1 + 1 + 1, 1 + 2, or 2 + 1."},
        ],
    },
    {
        "slug": "best-time-to-buy-and-sell-stock", "title": "Best Time to Buy and Sell Stock",
        "difficulty": "Easy", "tags": ["Array", "Greedy"], "solver": _max_profit,
        "description": (
            "You are given the price of a stock on each of `n` days. Choose one day to buy and a "
            "**later** day to sell. Print the maximum profit you can make, or `0` if no profit is possible.\n\n"
            "### Input format\n- Line 1: `n`\n- Line 2: `n` prices\n\n### Output format\nThe maximum profit."
        ),
        "constraints": "- 1 ≤ n ≤ 10^5\n- 0 ≤ price ≤ 10^4",
        "examples": [
            {"input": "6\n7 1 5 3 6 4", "output": "5", "explanation": "Buy at 1 (day 2), sell at 6 (day 5)."},
            {"input": "5\n7 6 4 3 1", "output": "0", "explanation": "Prices only fall, so don't trade."},
        ],
    },
    {
        "slug": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy",
        "tags": ["Array", "Hash Table"], "solver": _contains_duplicate,
        "description": (
            "Given an integer array `nums`, print `true` if any value appears **at least twice**, "
            "and `false` if every element is distinct.\n\n"
            "### Input format\n- Line 1: `n`\n- Line 2: `n` integers\n\n### Output format\n`true` or `false`."
        ),
        "constraints": "- 1 ≤ n ≤ 10^5\n- -10^9 ≤ nums[i] ≤ 10^9",
        "examples": [
            {"input": "4\n1 2 3 1", "output": "true", "explanation": "1 appears twice."},
            {"input": "4\n1 2 3 4", "output": "false", "explanation": None},
        ],
    },
    {
        "slug": "longest-substring-without-repeating-characters",
        "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium",
        "tags": ["String", "Hash Table", "Sliding Window"], "solver": _longest_substring,
        "description": (
            "Given a string `s`, find the length of the longest **substring** (a contiguous block of "
            "characters) that contains no repeated character.\n\n"
            "### Input format\nA single line containing `s`.\n\n### Output format\nThe length."
        ),
        "constraints": "- 1 ≤ |s| ≤ 5·10^4\n- s consists of printable ASCII characters",
        "examples": [
            {"input": "abcabcbb", "output": "3", "explanation": "\"abc\" has length 3."},
            {"input": "pwwkew", "output": "3",
             "explanation": "\"wke\" has length 3; \"pwke\" is a subsequence, not a substring."},
        ],
    },
    {
        "slug": "number-of-islands", "title": "Number of Islands", "difficulty": "Medium",
        "tags": ["Graph", "Matrix", "BFS / DFS"], "solver": _num_islands,
        "description": (
            "You are given an `m × n` grid of `1`s (land) and `0`s (water). An **island** is a group of "
            "land cells connected horizontally or vertically. Print the number of islands.\n\n"
            "### Input format\n- Line 1: `m n`\n- Next `m` lines: a row of `n` characters, each `0` or `1`\n\n"
            "### Output format\nThe number of islands."
        ),
        "constraints": "- 1 ≤ m, n ≤ 300",
        "examples": [
            {"input": "4 5\n11110\n11010\n11000\n00000", "output": "1", "explanation": None},
            {"input": "4 5\n11000\n11000\n00100\n00011", "output": "3", "explanation": None},
        ],
    },
    {
        "slug": "coin-change", "title": "Coin Change", "difficulty": "Medium",
        "tags": ["Array", "Dynamic Programming"], "solver": _coin_change,
        "description": (
            "You have coins of `k` different denominations and an unlimited supply of each. Print the "
            "**fewest** coins needed to make exactly `amount`, or `-1` if it cannot be done.\n\n"
            "### Input format\n- Line 1: `k`\n- Line 2: `k` coin values\n- Line 3: `amount`\n\n"
            "### Output format\nThe fewest number of coins, or `-1`."
        ),
        "constraints": "- 1 ≤ k ≤ 12\n- 1 ≤ coin ≤ 2^31 - 1\n- 0 ≤ amount ≤ 10^4",
        "examples": [
            {"input": "3\n1 2 5\n11", "output": "3", "explanation": "11 = 5 + 5 + 1"},
            {"input": "1\n2\n3", "output": "-1", "explanation": "3 can't be made from 2s."},
        ],
    },
    {
        "slug": "trapping-rain-water", "title": "Trapping Rain Water", "difficulty": "Hard",
        "tags": ["Array", "Two Pointers", "Stack"], "solver": _trap,
        "description": (
            "Given `n` non-negative integers representing an elevation map where each bar has width 1, "
            "compute how much water it can trap after raining.\n\n"
            "Aim for O(n) time and O(1) extra space.\n\n"
            "### Input format\n- Line 1: `n`\n- Line 2: `n` heights\n\n### Output format\nUnits of trapped water."
        ),
        "constraints": "- 1 ≤ n ≤ 2·10^5\n- 0 ≤ height[i] ≤ 10^4",
        "examples": [
            {"input": "12\n0 1 0 2 1 0 1 3 2 1 2 1", "output": "6", "explanation": None},
            {"input": "6\n4 2 0 3 2 5", "output": "9", "explanation": None},
        ],
    },
    {
        "slug": "edit-distance", "title": "Edit Distance", "difficulty": "Hard",
        "tags": ["String", "Dynamic Programming"], "solver": _edit_distance,
        "description": (
            "Given two words, print the minimum number of operations to convert `word1` into `word2`. "
            "Allowed operations on a single character: **insert**, **delete**, **replace**.\n\n"
            "### Input format\n- Line 1: `word1` (may be empty)\n- Line 2: `word2` (may be empty)\n\n"
            "### Output format\nThe minimum number of operations."
        ),
        "constraints": "- 0 ≤ |word1|, |word2| ≤ 500\n- Words consist of lowercase English letters",
        "examples": [
            {"input": "horse\nros", "output": "3",
             "explanation": "horse → rorse (replace h) → rose (delete r) → ros (delete e)"},
            {"input": "intention\nexecution", "output": "5", "explanation": None},
        ],
    },
]
