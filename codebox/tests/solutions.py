"""Reference solutions, expressed as patches to the real starter code so the
starter templates' I/O handling is verified in every language."""

from app.seed.problems import STARTER_CODE

# slug -> language -> (stub text in the starter code, replacement)
PATCHES = {
    "two-sum": {
        "python": ("    return -1, -1\n",
                   "    seen = {}\n    for i, v in enumerate(nums):\n        if target - v in seen:\n            return seen[target - v], i\n        seen[v] = i\n    return -1, -1\n"),
        "javascript": ("  return [-1, -1];\n",
                       "  const seen = new Map();\n  for (let i = 0; i < nums.length; i++) {\n    if (seen.has(target - nums[i])) return [seen.get(target - nums[i]), i];\n    seen.set(nums[i], i);\n  }\n  return [-1, -1];\n"),
        "java": ("        return new int[]{-1, -1};\n",
                 "        Map<Long, Integer> seen = new HashMap<>();\n        for (int i = 0; i < nums.length; i++) {\n            Integer j = seen.get((long) target - nums[i]);\n            if (j != null) return new int[]{j, i};\n            seen.put((long) nums[i], i);\n        }\n        return new int[]{-1, -1};\n"),
        "cpp": ("    return {-1, -1};\n",
                "    unordered_map<long long, int> seen;\n    for (int i = 0; i < (int)nums.size(); i++) {\n        auto it = seen.find((long long)target - nums[i]);\n        if (it != seen.end()) return {it->second, i};\n        seen[nums[i]] = i;\n    }\n    return {-1, -1};\n"),
    },
    "reverse-string": {
        "python": ("    return s\n", "    return s[::-1]\n"),
        "javascript": ("  return s;\n", "  return s.split('').reverse().join('');\n"),
        "java": ("        return s;\n", "        return new StringBuilder(s).reverse().toString();\n"),
        "cpp": ("    return s;\n", "    reverse(s.begin(), s.end());\n    return s;\n"),
    },
    "valid-parentheses": {
        "python": ("    return False\n",
                   "    pairs, stack = {')': '(', ']': '[', '}': '{'}, []\n    for ch in s:\n        if ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n        else:\n            stack.append(ch)\n    return not stack\n"),
        "javascript": ("  return false;\n",
                       "  const pairs = { ')': '(', ']': '[', '}': '{' };\n  const stack = [];\n  for (const ch of s) {\n    if (pairs[ch]) { if (stack.pop() !== pairs[ch]) return false; }\n    else stack.push(ch);\n  }\n  return stack.length === 0;\n"),
        "java": ("        return false;\n",
                 "        char[] stack = new char[s.length()];\n        int top = 0;\n        for (char c : s.toCharArray()) {\n            if (c == '(' || c == '[' || c == '{') { stack[top++] = c; continue; }\n            char open = c == ')' ? '(' : c == ']' ? '[' : '{';\n            if (top == 0 || stack[--top] != open) return false;\n        }\n        return top == 0;\n"),
        "cpp": ("    return false;\n",
                "    string st;\n    for (char c : s) {\n        if (c == '(' || c == '[' || c == '{') { st.push_back(c); continue; }\n        char open = c == ')' ? '(' : c == ']' ? '[' : '{';\n        if (st.empty() || st.back() != open) return false;\n        st.pop_back();\n    }\n    return st.empty();\n"),
    },
    "maximum-subarray": {
        "python": ("    return 0\n",
                   "    best = cur = nums[0]\n    for v in nums[1:]:\n        cur = max(v, cur + v)\n        best = max(best, cur)\n    return best\n"),
        "javascript": ("  return 0;\n",
                       "  let best = nums[0], cur = nums[0];\n  for (let i = 1; i < nums.length; i++) { cur = Math.max(nums[i], cur + nums[i]); best = Math.max(best, cur); }\n  return best;\n"),
        "java": ("        return 0;\n",
                 "        long best = nums[0], cur = nums[0];\n        for (int i = 1; i < nums.length; i++) { cur = Math.max(nums[i], cur + nums[i]); best = Math.max(best, cur); }\n        return best;\n"),
        "cpp": ("    return 0;\n",
                "    long long best = nums[0], cur = nums[0];\n    for (size_t i = 1; i < nums.size(); i++) { cur = max<long long>(nums[i], cur + nums[i]); best = max(best, cur); }\n    return best;\n"),
    },
    "binary-search": {
        "python": ("    return -1\n",
                   "    lo, hi = 0, len(nums) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if nums[mid] == target:\n            return mid\n        if nums[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n"),
        "javascript": ("  return -1;\n",
                       "  let lo = 0, hi = nums.length - 1;\n  while (lo <= hi) {\n    const mid = (lo + hi) >> 1;\n    if (nums[mid] === target) return mid;\n    if (nums[mid] < target) lo = mid + 1; else hi = mid - 1;\n  }\n  return -1;\n"),
        "java": ("        return -1;\n",
                 "        int lo = 0, hi = nums.length - 1;\n        while (lo <= hi) {\n            int mid = (lo + hi) >>> 1;\n            if (nums[mid] == target) return mid;\n            if (nums[mid] < target) lo = mid + 1; else hi = mid - 1;\n        }\n        return -1;\n"),
        "cpp": ("    return -1;\n",
                "    int lo = 0, hi = (int)nums.size() - 1;\n    while (lo <= hi) {\n        int mid = lo + (hi - lo) / 2;\n        if (nums[mid] == target) return mid;\n        if (nums[mid] < target) lo = mid + 1; else hi = mid - 1;\n    }\n    return -1;\n"),
    },
}


PATCHES.update({
    "fizz-buzz": {
        "python": ("    return []\n",
                   "    return [(\"Fizz\" if i % 3 == 0 else \"\") + (\"Buzz\" if i % 5 == 0 else \"\") or str(i)\n"
                   "            for i in range(1, n + 1)]\n"),
        "javascript": ("  return [];\n",
                       "  const out = [];\n  for (let i = 1; i <= n; i++) out.push(((i % 3 ? '' : 'Fizz') + (i % 5 ? '' : 'Buzz')) || String(i));\n  return out;\n"),
        "java": ("        return new ArrayList<>();\n",
                 "        List<String> out = new ArrayList<>();\n        for (int i = 1; i <= n; i++) {\n            String s = (i % 3 == 0 ? \"Fizz\" : \"\") + (i % 5 == 0 ? \"Buzz\" : \"\");\n            out.add(s.isEmpty() ? String.valueOf(i) : s);\n        }\n        return out;\n"),
        "cpp": ("    return {};\n",
                "    vector<string> out;\n    for (int i = 1; i <= n; i++) {\n        string s = string(i % 3 ? \"\" : \"Fizz\") + (i % 5 ? \"\" : \"Buzz\");\n        out.push_back(s.empty() ? to_string(i) : s);\n    }\n    return out;\n"),
    },
    "valid-palindrome": {
        "python": ("    return False\n",
                   "    t = [c.lower() for c in s if c.isascii() and c.isalnum()]\n    return t == t[::-1]\n"),
        "javascript": ("  return false;\n",
                       "  const t = s.toLowerCase().replace(/[^a-z0-9]/g, '');\n  return t === [...t].reverse().join('');\n"),
        "java": ("        return false;\n",
                 "        int i = 0, j = s.length() - 1;\n        while (i < j) {\n            char a = s.charAt(i), b = s.charAt(j);\n            if (!(Character.isLetterOrDigit(a) && a < 128)) { i++; continue; }\n            if (!(Character.isLetterOrDigit(b) && b < 128)) { j--; continue; }\n            if (Character.toLowerCase(a) != Character.toLowerCase(b)) return false;\n            i++; j--;\n        }\n        return true;\n"),
        "cpp": ("    return false;\n",
                "    int i = 0, j = (int)s.size() - 1;\n    while (i < j) {\n        if (!isalnum((unsigned char)s[i])) { i++; continue; }\n        if (!isalnum((unsigned char)s[j])) { j--; continue; }\n        if (tolower((unsigned char)s[i]) != tolower((unsigned char)s[j])) return false;\n        i++; j--;\n    }\n    return true;\n"),
    },
    "climbing-stairs": {
        "python": ("    return 0\n", "    a, b = 1, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n"),
        "javascript": ("  return 0;\n", "  let a = 1, b = 1;\n  for (let i = 0; i < n; i++) [a, b] = [b, a + b];\n  return a;\n"),
        "java": ("        return 0;\n", "        long a = 1, b = 1;\n        for (int i = 0; i < n; i++) { long t = a + b; a = b; b = t; }\n        return a;\n"),
        "cpp": ("    return 0;\n", "    long long a = 1, b = 1;\n    for (int i = 0; i < n; i++) { long long t = a + b; a = b; b = t; }\n    return a;\n"),
    },
    "best-time-to-buy-and-sell-stock": {
        "python": ("    return 0\n", "    best, low = 0, prices[0]\n    for p in prices:\n        low = min(low, p)\n        best = max(best, p - low)\n    return best\n"),
        "javascript": ("  return 0;\n", "  let best = 0, low = prices[0];\n  for (const p of prices) { low = Math.min(low, p); best = Math.max(best, p - low); }\n  return best;\n"),
        "java": ("        return 0;\n", "        int best = 0, low = prices[0];\n        for (int p : prices) { low = Math.min(low, p); best = Math.max(best, p - low); }\n        return best;\n"),
        "cpp": ("    return 0;\n", "    int best = 0, low = prices[0];\n    for (int p : prices) { low = min(low, p); best = max(best, p - low); }\n    return best;\n"),
    },
    "contains-duplicate": {
        "python": ("    return False\n", "    return len(set(nums)) != len(nums)\n"),
        "javascript": ("  return false;\n", "  return new Set(nums).size !== nums.length;\n"),
        "java": ("        return false;\n", "        Set<Integer> seen = new HashSet<>();\n        for (int x : nums) if (!seen.add(x)) return true;\n        return false;\n"),
        "cpp": ("    return false;\n", "    unordered_set<int> seen(nums.begin(), nums.end());\n    return seen.size() != nums.size();\n"),
    },
    "longest-substring-without-repeating-characters": {
        "python": ("    return 0\n", "    last, start, best = {}, 0, 0\n    for i, c in enumerate(s):\n        if last.get(c, -1) >= start:\n            start = last[c] + 1\n        last[c] = i\n        best = max(best, i - start + 1)\n    return best\n"),
        "javascript": ("  return 0;\n", "  const last = new Map();\n  let start = 0, best = 0;\n  for (let i = 0; i < s.length; i++) {\n    if (last.has(s[i]) && last.get(s[i]) >= start) start = last.get(s[i]) + 1;\n    last.set(s[i], i);\n    best = Math.max(best, i - start + 1);\n  }\n  return best;\n"),
        "java": ("        return 0;\n", "        int[] last = new int[128];\n        Arrays.fill(last, -1);\n        int start = 0, best = 0;\n        for (int i = 0; i < s.length(); i++) {\n            char c = s.charAt(i);\n            if (last[c] >= start) start = last[c] + 1;\n            last[c] = i;\n            best = Math.max(best, i - start + 1);\n        }\n        return best;\n"),
        "cpp": ("    return 0;\n", "    vector<int> last(256, -1);\n    int start = 0, best = 0;\n    for (int i = 0; i < (int)s.size(); i++) {\n        unsigned char c = s[i];\n        if (last[c] >= start) start = last[c] + 1;\n        last[c] = i;\n        best = max(best, i - start + 1);\n    }\n    return best;\n"),
    },
    "number-of-islands": {
        "python": ("    return 0\n", "    m, n, count = len(grid), len(grid[0]), 0\n    for r in range(m):\n        for c in range(n):\n            if grid[r][c] == \"1\":\n                count += 1\n                grid[r][c] = \"0\"\n                stack = [(r, c)]\n                while stack:\n                    y, x = stack.pop()\n                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):\n                        if 0 <= ny < m and 0 <= nx < n and grid[ny][nx] == \"1\":\n                            grid[ny][nx] = \"0\"\n                            stack.append((ny, nx))\n    return count\n"),
        "javascript": ("  return 0;\n", "  const m = grid.length, n = grid[0].length;\n  let count = 0;\n  for (let r = 0; r < m; r++) for (let c = 0; c < n; c++) {\n    if (grid[r][c] !== '1') continue;\n    count++;\n    grid[r][c] = '0';\n    const stack = [[r, c]];\n    while (stack.length) {\n      const [y, x] = stack.pop();\n      for (const [ny, nx] of [[y + 1, x], [y - 1, x], [y, x + 1], [y, x - 1]]) {\n        if (ny >= 0 && ny < m && nx >= 0 && nx < n && grid[ny][nx] === '1') { grid[ny][nx] = '0'; stack.push([ny, nx]); }\n      }\n    }\n  }\n  return count;\n"),
        "java": ("        return 0;\n", "        int m = grid.length, n = grid[0].length, count = 0;\n        int[] stack = new int[m * n];\n        for (int r = 0; r < m; r++) for (int c = 0; c < n; c++) {\n            if (grid[r][c] != '1') continue;\n            count++;\n            grid[r][c] = '0';\n            int top = 0;\n            stack[top++] = r * n + c;\n            while (top > 0) {\n                int cell = stack[--top], y = cell / n, x = cell % n;\n                int[][] next = {{y + 1, x}, {y - 1, x}, {y, x + 1}, {y, x - 1}};\n                for (int[] p : next) {\n                    if (p[0] >= 0 && p[0] < m && p[1] >= 0 && p[1] < n && grid[p[0]][p[1]] == '1') {\n                        grid[p[0]][p[1]] = '0';\n                        stack[top++] = p[0] * n + p[1];\n                    }\n                }\n            }\n        }\n        return count;\n"),
        "cpp": ("    return 0;\n", "    int m = grid.size(), n = grid[0].size(), count = 0;\n    for (int r = 0; r < m; r++) for (int c = 0; c < n; c++) {\n        if (grid[r][c] != '1') continue;\n        count++;\n        grid[r][c] = '0';\n        vector<pair<int, int>> st{{r, c}};\n        while (!st.empty()) {\n            auto [y, x] = st.back();\n            st.pop_back();\n            int dy[] = {1, -1, 0, 0}, dx[] = {0, 0, 1, -1};\n            for (int d = 0; d < 4; d++) {\n                int ny = y + dy[d], nx = x + dx[d];\n                if (ny >= 0 && ny < m && nx >= 0 && nx < n && grid[ny][nx] == '1') { grid[ny][nx] = '0'; st.push_back({ny, nx}); }\n            }\n        }\n    }\n    return count;\n"),
    },
    "coin-change": {
        "python": ("    return -1\n", "    dp = [0] + [amount + 1] * amount\n    for a in range(1, amount + 1):\n        for coin in coins:\n            if coin <= a:\n                dp[a] = min(dp[a], dp[a - coin] + 1)\n    return dp[amount] if dp[amount] <= amount else -1\n"),
        "javascript": ("  return -1;\n", "  const dp = new Array(amount + 1).fill(amount + 1);\n  dp[0] = 0;\n  for (let a = 1; a <= amount; a++) for (const c of coins) if (c <= a) dp[a] = Math.min(dp[a], dp[a - c] + 1);\n  return dp[amount] <= amount ? dp[amount] : -1;\n"),
        "java": ("        return -1;\n", "        int[] dp = new int[amount + 1];\n        Arrays.fill(dp, amount + 1);\n        dp[0] = 0;\n        for (int a = 1; a <= amount; a++) for (int c : coins) if (c <= a) dp[a] = Math.min(dp[a], dp[a - c] + 1);\n        return dp[amount] <= amount ? dp[amount] : -1;\n"),
        "cpp": ("    return -1;\n", "    vector<int> dp(amount + 1, amount + 1);\n    dp[0] = 0;\n    for (int a = 1; a <= amount; a++) for (int c : coins) if (c <= a) dp[a] = min(dp[a], dp[a - c] + 1);\n    return dp[amount] <= amount ? dp[amount] : -1;\n"),
    },
    "trapping-rain-water": {
        "python": ("    return 0\n", "    l, r, lm, rm, w = 0, len(height) - 1, 0, 0, 0\n    while l < r:\n        if height[l] < height[r]:\n            lm = max(lm, height[l]); w += lm - height[l]; l += 1\n        else:\n            rm = max(rm, height[r]); w += rm - height[r]; r -= 1\n    return w\n"),
        "javascript": ("  return 0;\n", "  let l = 0, r = height.length - 1, lm = 0, rm = 0, w = 0;\n  while (l < r) {\n    if (height[l] < height[r]) { lm = Math.max(lm, height[l]); w += lm - height[l]; l++; }\n    else { rm = Math.max(rm, height[r]); w += rm - height[r]; r--; }\n  }\n  return w;\n"),
        "java": ("        return 0;\n", "        int l = 0, r = height.length - 1, lm = 0, rm = 0;\n        long w = 0;\n        while (l < r) {\n            if (height[l] < height[r]) { lm = Math.max(lm, height[l]); w += lm - height[l]; l++; }\n            else { rm = Math.max(rm, height[r]); w += rm - height[r]; r--; }\n        }\n        return w;\n"),
        "cpp": ("    return 0;\n", "    int l = 0, r = (int)height.size() - 1, lm = 0, rm = 0;\n    long long w = 0;\n    while (l < r) {\n        if (height[l] < height[r]) { lm = max(lm, height[l]); w += lm - height[l]; l++; }\n        else { rm = max(rm, height[r]); w += rm - height[r]; r--; }\n    }\n    return w;\n"),
    },
    "edit-distance": {
        "python": ("    return 0\n", "    prev = list(range(len(word2) + 1))\n    for i, a in enumerate(word1, 1):\n        cur = [i] + [0] * len(word2)\n        for j, b in enumerate(word2, 1):\n            cur[j] = prev[j - 1] if a == b else 1 + min(prev[j - 1], prev[j], cur[j - 1])\n        prev = cur\n    return prev[-1]\n"),
        "javascript": ("  return 0;\n", "  let prev = Array.from({ length: word2.length + 1 }, (_, j) => j);\n  for (let i = 1; i <= word1.length; i++) {\n    const cur = [i];\n    for (let j = 1; j <= word2.length; j++) {\n      cur[j] = word1[i - 1] === word2[j - 1] ? prev[j - 1] : 1 + Math.min(prev[j - 1], prev[j], cur[j - 1]);\n    }\n    prev = cur;\n  }\n  return prev[word2.length];\n"),
        "java": ("        return 0;\n", "        int n = word2.length();\n        int[] prev = new int[n + 1];\n        for (int j = 0; j <= n; j++) prev[j] = j;\n        for (int i = 1; i <= word1.length(); i++) {\n            int[] cur = new int[n + 1];\n            cur[0] = i;\n            for (int j = 1; j <= n; j++) {\n                cur[j] = word1.charAt(i - 1) == word2.charAt(j - 1) ? prev[j - 1] : 1 + Math.min(prev[j - 1], Math.min(prev[j], cur[j - 1]));\n            }\n            prev = cur;\n        }\n        return prev[n];\n"),
        "cpp": ("    return 0;\n", "    int n = word2.size();\n    vector<int> prev(n + 1), cur(n + 1);\n    iota(prev.begin(), prev.end(), 0);\n    for (int i = 1; i <= (int)word1.size(); i++) {\n        cur[0] = i;\n        for (int j = 1; j <= n; j++) {\n            cur[j] = word1[i - 1] == word2[j - 1] ? prev[j - 1] : 1 + min({prev[j - 1], prev[j], cur[j - 1]});\n        }\n        swap(prev, cur);\n    }\n    return prev[n];\n"),
    },
})


def solution(slug: str, language: str) -> str:
    stub, replacement = PATCHES[slug][language]
    starter = STARTER_CODE[slug][language]
    assert starter.count(stub) == 1, f"stub not unique in {slug}/{language}"
    return starter.replace(stub, replacement)
