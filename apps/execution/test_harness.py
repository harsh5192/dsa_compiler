"""End to end execution tests.

These run real code through the sandbox for every bundled language, so the
harness generators (argument conversion, node helpers, result serialisation)
stay covered.  The reference solutions are deliberately small; the point is the
plumbing, not the algorithms.
"""

from django.core.management import call_command
from django.test import TestCase

from apps.execution import service
from apps.execution.models import Language
from apps.problems.models import Problem

#: Solutions that are short enough to keep in the test suite.
SOLUTIONS = {
    "two-sum": {
        "python": "def twoSum(nums, target):\n"
        "    seen = {}\n"
        "    for i, n in enumerate(nums):\n"
        "        if target - n in seen: return [seen[target - n], i]\n"
        "        seen[n] = i\n"
        "    return []\n",
        "javascript": "function twoSum(nums, target) {\n"
        "  const seen = new Map();\n"
        "  for (let i = 0; i < nums.length; i++) {\n"
        "    if (seen.has(target - nums[i])) return [seen.get(target - nums[i]), i];\n"
        "    seen.set(nums[i], i);\n"
        "  }\n"
        "  return [];\n"
        "}\n",
        "cpp": "#include <vector>\n#include <map>\nusing namespace std;\n"
        "vector<int> twoSum(vector<int>& nums, int target) {\n"
        "  map<int, int> seen;\n"
        "  for (int i = 0; i < (int) nums.size(); i++) {\n"
        "    if (seen.count(target - nums[i])) return {seen[target - nums[i]], i};\n"
        "    seen[nums[i]] = i;\n"
        "  }\n"
        "  return {};\n"
        "}\n",
        "java": "import java.util.*;\n"
        "class Solution {\n"
        "  public int[] twoSum(int[] nums, int target) {\n"
        "    Map<Integer, Integer> seen = new HashMap<>();\n"
        "    for (int i = 0; i < nums.length; i++) {\n"
        "      if (seen.containsKey(target - nums[i])) return new int[]{seen.get(target - nums[i]), i};\n"
        "      seen.put(nums[i], i);\n"
        "    }\n"
        "    return new int[0];\n"
        "  }\n"
        "}\n",
        "c": "#include <stdlib.h>\n"
        "int* twoSum(int* nums, int nums_len, int target) {\n"
        "  twoSum_len = 2;\n"
        "  int* out = (int*) malloc(sizeof(int) * 2);\n"
        "  for (int i = 0; i < nums_len; i++)\n"
        "    for (int j = i + 1; j < nums_len; j++)\n"
        "      if (nums[i] + nums[j] == target) { out[0] = i; out[1] = j; return out; }\n"
        "  out[0] = -1; out[1] = -1;\n"
        "  return out;\n"
        "}\n",
    },
    "reverse-linked-list": {
        "python": "def reverseList(head):\n"
        "    prev = None\n"
        "    while head:\n"
        "        head.next, prev, head = prev, head, head.next\n"
        "    return prev\n",
        "javascript": "function reverseList(head) {\n"
        "  let prev = null;\n"
        "  while (head) { const next = head.next; head.next = prev; prev = head; head = next; }\n"
        "  return prev;\n"
        "}\n",
        "cpp": "ListNode* reverseList(ListNode* head) {\n"
        "  ListNode* prev = nullptr;\n"
        "  while (head) { ListNode* next = head->next; head->next = prev; prev = head; head = next; }\n"
        "  return prev;\n"
        "}\n",
        "java": "class Solution {\n"
        "  public ListNode reverseList(ListNode head) {\n"
        "    ListNode prev = null;\n"
        "    while (head != null) { ListNode next = head.next; head.next = prev; prev = head; head = next; }\n"
        "    return prev;\n"
        "  }\n"
        "}\n",
        "c": "ListNode* reverseList(ListNode* head) {\n"
        "  ListNode* prev = NULL;\n"
        "  while (head) { ListNode* next = head->next; head->next = prev; prev = head; head = next; }\n"
        "  return prev;\n"
        "}\n",
    },
    "maximum-depth-of-binary-tree": {
        "python": "def maxDepth(root):\n"
        "    if root is None: return 0\n"
        "    return 1 + max(maxDepth(root.left), maxDepth(root.right))\n",
        "javascript": "function maxDepth(root) {\n"
        "  if (!root) return 0;\n"
        "  return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
        "}\n",
        "cpp": "int maxDepth(TreeNode* root) {\n"
        "  if (!root) return 0;\n"
        "  return 1 + max(maxDepth(root->left), maxDepth(root->right));\n"
        "}\n",
        "java": "class Solution {\n"
        "  public int maxDepth(TreeNode root) {\n"
        "    if (root == null) return 0;\n"
        "    return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
        "  }\n"
        "}\n",
        "c": "int maxDepth(TreeNode* root) {\n"
        "  if (!root) return 0;\n"
        "  int a = maxDepth(root->left), b = maxDepth(root->right);\n"
        "  return 1 + (a > b ? a : b);\n"
        "}\n",
    },
    "group-anagrams": {
        # Rows come back in a different order than the stored answer, which the
        # unordered comparison has to accept.
        "python": "def groupAnagrams(strs):\n"
        "    groups = {}\n"
        "    for s in strs: groups.setdefault(''.join(sorted(s)), []).append(s)\n"
        "    return [groups[k] for k in sorted(groups, reverse=True)]\n",
        "javascript": "function groupAnagrams(strs) {\n"
        "  const g = new Map();\n"
        "  for (const s of strs) { const k = s.split('').sort().join(''); if (!g.has(k)) g.set(k, []); g.get(k).push(s); }\n"
        "  return Array.from(g.entries()).sort((a, b) => (a[0] < b[0] ? 1 : -1)).map((e) => e[1]);\n"
        "}\n",
        "cpp": "#include <vector>\n#include <string>\n#include <map>\n#include <algorithm>\n"
        "using namespace std;\n"
        "vector<vector<string>> groupAnagrams(vector<string>& strs) {\n"
        "  map<string, vector<string>> g;\n"
        "  for (string s : strs) { string k = s; sort(k.begin(), k.end()); g[k].push_back(s); }\n"
        "  vector<vector<string>> out;\n"
        "  for (auto it = g.rbegin(); it != g.rend(); ++it) out.push_back(it->second);\n"
        "  return out;\n"
        "}\n",
        "java": "import java.util.*;\n"
        "class Solution {\n"
        "  public List<List<String>> groupAnagrams(String[] strs) {\n"
        "    Map<String, List<String>> g = new LinkedHashMap<>();\n"
        "    for (String s : strs) { char[] c = s.toCharArray(); Arrays.sort(c); g.computeIfAbsent(new String(c), k -> new ArrayList<>()).add(s); }\n"
        "    List<List<String>> out = new ArrayList<>(g.values());\n"
        "    Collections.reverse(out);\n"
        "    return out;\n"
        "  }\n"
        "}\n",
        "c": "#include <stdlib.h>\n#include <string.h>\n"
        "char*** groupAnagrams(char** strs, int strs_len) {\n"
        "  int cap = strs_len > 0 ? strs_len : 1;\n"
        "  char*** out = (char***) malloc(sizeof(char**) * (size_t) cap);\n"
        "  char** keys = (char**) malloc(sizeof(char*) * (size_t) cap);\n"
        "  int* sizes = (int*) malloc(sizeof(int) * (size_t) cap);\n"
        "  int groups = 0;\n"
        "  for (int i = 0; i < strs_len; i++) {\n"
        "    char key[128]; int n = 0;\n"
        "    for (const char* s = strs[i]; *s && n < 127; s++) key[n++] = *s;\n"
        "    key[n] = 0;\n"
        "    for (int a = 0; a < n; a++) for (int b = a + 1; b < n; b++)\n"
        "      if (key[b] < key[a]) { char t = key[a]; key[a] = key[b]; key[b] = t; }\n"
        "    int found = -1;\n"
        "    for (int g = 0; g < groups; g++) if (strcmp(keys[g], key) == 0) { found = g; break; }\n"
        "    if (found < 0) { keys[groups] = strdup(key); sizes[groups] = 0;\n"
        "      out[groups] = (char**) malloc(sizeof(char*) * (size_t) (cap + 1)); found = groups++; }\n"
        "    out[found][sizes[found]++] = strs[i];\n"
        "  }\n"
        "  for (int g = 0; g < groups; g++) out[g][sizes[g]] = NULL;\n"
        "  groupAnagrams_rows = groups;\n"
        "  return out;\n"
        "}\n",
    },
    "binary-tree-level-order-traversal": {
        # Ragged rows, so the matrix has to be walked row by row.
        "python": "def levelOrder(root):\n"
        "    if not root: return []\n"
        "    out, queue = [], [root]\n"
        "    while queue:\n"
        "        row = []\n"
        "        for _ in range(len(queue)):\n"
        "            node = queue.pop(0); row.append(node.val)\n"
        "            if node.left: queue.append(node.left)\n"
        "            if node.right: queue.append(node.right)\n"
        "        out.append(row)\n"
        "    return out\n",
        "javascript": "function levelOrder(root) {\n"
        "  if (!root) return [];\n"
        "  const out = [], queue = [root];\n"
        "  while (queue.length) {\n"
        "    const row = [], size = queue.length;\n"
        "    for (let i = 0; i < size; i++) {\n"
        "      const node = queue.shift(); row.push(node.val);\n"
        "      if (node.left) queue.push(node.left);\n"
        "      if (node.right) queue.push(node.right);\n"
        "    }\n"
        "    out.push(row);\n"
        "  }\n"
        "  return out;\n"
        "}\n",
        "cpp": "#include <vector>\n#include <queue>\nusing namespace std;\n"
        "vector<vector<int>> levelOrder(TreeNode* root) {\n"
        "  vector<vector<int>> out;\n"
        "  if (!root) return out;\n"
        "  queue<TreeNode*> q; q.push(root);\n"
        "  while (!q.empty()) {\n"
        "    int size = (int) q.size(); vector<int> row;\n"
        "    for (int i = 0; i < size; i++) {\n"
        "      TreeNode* node = q.front(); q.pop(); row.push_back(node->val);\n"
        "      if (node->left) q.push(node->left);\n"
        "      if (node->right) q.push(node->right);\n"
        "    }\n"
        "    out.push_back(row);\n"
        "  }\n"
        "  return out;\n"
        "}\n",
        "java": "import java.util.*;\n"
        "class Solution {\n"
        "  public List<List<Integer>> levelOrder(TreeNode root) {\n"
        "    List<List<Integer>> out = new ArrayList<>();\n"
        "    if (root == null) return out;\n"
        "    Deque<TreeNode> q = new ArrayDeque<>(); q.add(root);\n"
        "    while (!q.isEmpty()) {\n"
        "      int size = q.size(); List<Integer> row = new ArrayList<>();\n"
        "      for (int i = 0; i < size; i++) {\n"
        "        TreeNode node = q.poll(); row.add(node.val);\n"
        "        if (node.left != null) q.add(node.left);\n"
        "        if (node.right != null) q.add(node.right);\n"
        "      }\n"
        "      out.add(row);\n"
        "    }\n"
        "    return out;\n"
        "  }\n"
        "}\n",
        "c": "#include <stdlib.h>\n"
        "int** levelOrder(TreeNode* root) {\n"
        "  if (!root) { levelOrder_rows = 0; return NULL; }\n"
        "  int cap = 16, width = 0, rows = 0, tail = 0, head = 0;\n"
        "  TreeNode** queue = (TreeNode**) malloc(sizeof(TreeNode*) * (size_t) cap);\n"
        "  int** out = (int**) malloc(sizeof(int*) * (size_t) cap);\n"
        "  int* sizes = (int*) malloc(sizeof(int) * (size_t) cap);\n"
        "  queue[tail++] = root;\n"
        "  while (head < tail) {\n"
        "    int level_end = tail, count = level_end - head;\n"
        "    out[rows] = (int*) malloc(sizeof(int) * (size_t) (count > 0 ? count : 1));\n"
        "    for (int i = 0; i < count; i++) {\n"
        "      TreeNode* node = queue[head++];\n"
        "      out[rows][i] = node->val;\n"
        "      if (node->left) { if (tail + 2 > cap) { cap *= 2; queue = (TreeNode**) realloc(queue, sizeof(TreeNode*) * (size_t) cap); } queue[tail++] = node->left; }\n"
        "      if (node->right) { if (tail + 2 > cap) { cap *= 2; queue = (TreeNode**) realloc(queue, sizeof(TreeNode*) * (size_t) cap); } queue[tail++] = node->right; }\n"
        "    }\n"
        "    sizes[rows] = count;\n"
        "    if (count > width) width = count;\n"
        "    rows++;\n"
        "  }\n"
        "  for (int r = 0; r < rows; r++) out[r][sizes[r]] = DSA_ROW_END_INT;\n"
        "  levelOrder_rows = rows;\n"
        "  return out;\n"
        "}\n",
    },
    "matrix-spiral-traversal": {
        "python": "def spiralOrder(matrix):\n"
        "    out = []\n"
        "    if not matrix or not matrix[0]: return out\n"
        "    top, bottom = 0, len(matrix) - 1\n"
        "    left, right = 0, len(matrix[0]) - 1\n"
        "    while top <= bottom and left <= right:\n"
        "        out.extend(matrix[top][left:right + 1]); top += 1\n"
        "        for r in range(top, bottom + 1): out.append(matrix[r][right])\n"
        "        right -= 1\n"
        "        if top <= bottom:\n"
        "            out.extend(matrix[bottom][left:right + 1][::-1]); bottom -= 1\n"
        "        if left <= right:\n"
        "            for r in range(bottom, top - 1, -1): out.append(matrix[r][left])\n"
        "            left += 1\n"
        "    return out\n",
        "javascript": "function spiralOrder(matrix) {\n"
        "  const out = [];\n"
        "  if (!matrix.length || !matrix[0].length) return out;\n"
        "  let top = 0, bottom = matrix.length - 1, left = 0, right = matrix[0].length - 1;\n"
        "  while (top <= bottom && left <= right) {\n"
        "    for (let c = left; c <= right; c++) out.push(matrix[top][c]);\n"
        "    top++;\n"
        "    for (let r = top; r <= bottom; r++) out.push(matrix[r][right]);\n"
        "    right--;\n"
        "    if (top <= bottom) { for (let c = right; c >= left; c--) out.push(matrix[bottom][c]); bottom--; }\n"
        "    if (left <= right) { for (let r = bottom; r >= top; r--) out.push(matrix[r][left]); left++; }\n"
        "  }\n"
        "  return out;\n"
        "}\n",
        "cpp": "#include <vector>\nusing namespace std;\n"
        "vector<int> spiralOrder(vector<vector<int>>& matrix) {\n"
        "  vector<int> out;\n"
        "  if (matrix.empty() || matrix[0].empty()) return out;\n"
        "  int top = 0, bottom = (int) matrix.size() - 1, left = 0, right = (int) matrix[0].size() - 1;\n"
        "  while (top <= bottom && left <= right) {\n"
        "    for (int c = left; c <= right; c++) out.push_back(matrix[top][c]);\n"
        "    top++;\n"
        "    for (int r = top; r <= bottom; r++) out.push_back(matrix[r][right]);\n"
        "    right--;\n"
        "    if (top <= bottom) { for (int c = right; c >= left; c--) out.push_back(matrix[bottom][c]); bottom--; }\n"
        "    if (left <= right) { for (int r = bottom; r >= top; r--) out.push_back(matrix[r][left]); left++; }\n"
        "  }\n"
        "  return out;\n"
        "}\n",
        "java": "import java.util.*;\n"
        "class Solution {\n"
        "  public int[] spiralOrder(int[][] matrix) {\n"
        "    List<Integer> l = new ArrayList<>();\n"
        "    if (matrix.length == 0 || matrix[0].length == 0) return new int[0];\n"
        "    int top = 0, bottom = matrix.length - 1, left = 0, right = matrix[0].length - 1;\n"
        "    while (top <= bottom && left <= right) {\n"
        "      for (int c = left; c <= right; c++) l.add(matrix[top][c]);\n"
        "      top++;\n"
        "      for (int r = top; r <= bottom; r++) l.add(matrix[r][right]);\n"
        "      right--;\n"
        "      if (top <= bottom) { for (int c = right; c >= left; c--) l.add(matrix[bottom][c]); bottom--; }\n"
        "      if (left <= right) { for (int r = bottom; r >= top; r--) l.add(matrix[r][left]); left++; }\n"
        "    }\n"
        "    int[] out = new int[l.size()];\n"
        "    for (int i = 0; i < out.length; i++) out[i] = l.get(i);\n"
        "    return out;\n"
        "  }\n"
        "}\n",
        "c": "#include <stdlib.h>\n"
        "int* spiralOrder(int** matrix, int matrix_rows, int matrix_cols) {\n"
        "  int total = matrix_rows * matrix_cols;\n"
        "  int* out = (int*) malloc(sizeof(int) * (size_t) (total > 0 ? total : 1));\n"
        "  int k = 0, top = 0, bottom = matrix_rows - 1, left = 0, right = matrix_cols - 1;\n"
        "  while (top <= bottom && left <= right) {\n"
        "    for (int c = left; c <= right; c++) out[k++] = matrix[top][c];\n"
        "    top++;\n"
        "    for (int r = top; r <= bottom; r++) out[k++] = matrix[r][right];\n"
        "    right--;\n"
        "    if (top <= bottom) { for (int c = right; c >= left; c--) out[k++] = matrix[bottom][c]; bottom--; }\n"
        "    if (left <= right) { for (int r = bottom; r >= top; r--) out[k++] = matrix[r][left]; left++; }\n"
        "  }\n"
        "  spiralOrder_len = k;\n"
        "  return out;\n"
        "}\n",
    },
    "n-queens": {
        # Any valid arrangement is accepted, so the answers deliberately do not
        # match the stored ones.
        "python": "def solveNQueens(n):\n"
        "    boards, cols = [], []\n"
        "    def place(row):\n"
        "        if row == n:\n"
        "            boards.append([''.join('Q' if c == col else '.' for c in range(n)) for col in cols])\n"
        "            return\n"
        "        for col in range(n):\n"
        "            if any(col == c or abs(row - r) == abs(col - c) for r, c in enumerate(cols)): continue\n"
        "            cols.append(col); place(row + 1); cols.pop()\n"
        "    place(0)\n"
        "    return boards\n",
        "javascript": "function solveNQueens(n) {\n"
        "  const boards = [], cols = [];\n"
        "  function place(row) {\n"
        "    if (row === n) {\n"
        "      boards.push(cols.map((col) => { let s = ''; for (let c = 0; c < n; c++) s += c === col ? 'Q' : '.'; return s; }));\n"
        "      return;\n"
        "    }\n"
        "    for (let col = 0; col < n; col++) {\n"
        "      let ok = true;\n"
        "      for (let r = 0; r < cols.length; r++) if (cols[r] === col || Math.abs(row - r) === Math.abs(col - cols[r])) { ok = false; break; }\n"
        "      if (!ok) continue;\n"
        "      cols.push(col); place(row + 1); cols.pop();\n"
        "    }\n"
        "  }\n"
        "  place(0);\n"
        "  return boards;\n"
        "}\n",
        "cpp": "#include <vector>\n#include <string>\nusing namespace std;\n"
        "vector<vector<string>> solveNQueens(int n) {\n"
        "  vector<vector<string>> out; vector<int> cols;\n"
        "  function<void(int)> place = [&](int row) {\n"
        "    if (row == n) {\n"
        "      vector<string> board;\n"
        "      for (int c = 0; c < n; c++) { string s; for (int k = 0; k < n; k++) s += (cols[k] == c ? 'Q' : '.'); board.push_back(s); }\n"
        "      out.push_back(board); return;\n"
        "    }\n"
        "    for (int col = 0; col < n; col++) {\n"
        "      bool ok = true;\n"
        "      for (int r = 0; r < row; r++) if (cols[r] == col || (row - r) == abs(cols[r] - col)) { ok = false; break; }\n"
        "      if (!ok) continue;\n"
        "      cols.push_back(col); place(row + 1); cols.pop_back();\n"
        "    }\n"
        "  };\n"
        "  place(0);\n"
        "  return out;\n"
        "}\n",
        "java": "import java.util.*;\n"
        "class Solution {\n"
        "  public List<List<String>> solveNQueens(int n) {\n"
        "    List<List<String>> out = new ArrayList<>();\n"
        "    List<Integer> cols = new ArrayList<>();\n"
        "    solve(0, n, cols, out);\n"
        "    return out;\n"
        "  }\n"
        "  void solve(int row, int n, List<Integer> cols, List<List<String>> out) {\n"
        "    if (row == n) {\n"
        "      List<String> board = new ArrayList<>();\n"
        "      for (int k = 0; k < n; k++) { StringBuilder s = new StringBuilder(); for (int c = 0; c < n; c++) s.append(c == cols.get(k) ? 'Q' : '.'); board.add(s.toString()); }\n"
        "      out.add(board); return;\n"
        "    }\n"
        "    for (int col = 0; col < n; col++) {\n"
        "      boolean ok = true;\n"
        "      for (int r = 0; r < row; r++) if (cols.get(r) == col || (row - r) == Math.abs(cols.get(r) - col)) { ok = false; break; }\n"
        "      if (!ok) continue;\n"
        "      cols.add(col); solve(row + 1, n, cols, out); cols.remove(cols.size() - 1);\n"
        "    }\n"
        "  }\n"
        "}\n",
        "c": "#include <stdlib.h>\n#include <string.h>\n"
        "#define MAXN 8\n#define MAXSOL 100\n"
        "static int g_n, g_cols[MAXN], g_count;\n"
        "static char g_boards[MAXSOL][MAXN][MAXN + 1];\n"
        "static void place(int row) {\n"
        "  if (row == g_n) {\n"
        "    for (int r = 0; r < g_n; r++) {\n"
        "      for (int c = 0; c < g_n; c++) g_boards[g_count][r][c] = (g_cols[r] == c) ? 'Q' : '.';\n"
        "      g_boards[g_count][r][g_n] = 0;\n"
        "    }\n"
        "    g_count++; return;\n"
        "  }\n"
        "  for (int col = 0; col < g_n; col++) {\n"
        "    int ok = 1;\n"
        "    for (int r = 0; r < row; r++) { int d = col - g_cols[r]; if (d < 0) d = -d;\n"
        "      if (g_cols[r] == col || (row - r) == d) { ok = 0; break; } }\n"
        "    if (!ok) continue;\n"
        "    g_cols[row] = col; place(row + 1);\n"
        "  }\n"
        "}\n"
        "char*** solveNQueens(int n) {\n"
        "  g_n = n; g_count = 0;\n"
        "  if (n < 1 || n > MAXN) { solveNQueens_rows = 0; return NULL; }\n"
        "  place(0);\n"
        "  char*** out = (char***) malloc(sizeof(char**) * (size_t) (g_count > 0 ? g_count : 1));\n"
        "  for (int s = 0; s < g_count; s++) {\n"
        "    out[s] = (char**) malloc(sizeof(char*) * (size_t) (n + 1));\n"
        "    for (int r = 0; r < n; r++) out[s][r] = strdup(g_boards[s][r]);\n"
        "    out[s][n] = NULL;\n"
        "  }\n"
        "  solveNQueens_rows = g_count;\n"
        "  return out;\n"
        "}\n",
    },
}


class ExecutionHarnessTests(TestCase):
    """Every bundled language runs every reference solution."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_languages", verbosity=0)
        call_command("seed_dsa_data", verbosity=0)

    def test_reference_solutions_are_accepted(self):
        problems = {p.slug: p for p in Problem.objects.filter(slug__in=SOLUTIONS)}
        self.assertEqual(
            set(problems), set(SOLUTIONS), "a bundled problem referenced by the tests is missing"
        )
        for slug, per_language in SOLUTIONS.items():
            for language_slug, source in per_language.items():
                with self.subTest(problem=slug, language=language_slug):
                    problem = problems[slug]
                    language = Language.objects.get(slug=language_slug)
                    report = service.execute(
                        problem=problem, language=language, source_code=source, mode="submit"
                    )
                    self.assertTrue(
                        report.accepted,
                        f"{slug}/{language_slug} was rejected: {report.verdict} "
                        f"{(report.cases[0].actual_output if report.cases else '')[:200]}"
                        f" {report.cases[0].error if report.cases else report.error_message}",
                    )

    def test_wrong_answer_is_reported(self):
        problem = Problem.objects.get(slug="two-sum")
        language = Language.objects.get(slug="python")
        report = service.execute(
            problem=problem, language=language, source_code="def twoSum(nums, target):\n    return [0, 0]\n",
            mode="submit",
        )
        self.assertFalse(report.accepted)
        self.assertEqual(report.verdict, "wrong_answer")

    def test_runtime_error_is_reported(self):
        problem = Problem.objects.get(slug="two-sum")
        language = Language.objects.get(slug="python")
        report = service.execute(
            problem=problem,
            language=language,
            source_code="def twoSum(nums, target):\n    raise ValueError('boom')\n",
            mode="submit",
        )
        self.assertFalse(report.accepted)
        self.assertEqual(report.verdict, "runtime_error")

    def test_missing_function_is_reported(self):
        problem = Problem.objects.get(slug="two-sum")
        language = Language.objects.get(slug="python")
        report = service.execute(
            problem=problem, language=language, source_code="x = 1\n", mode="submit"
        )
        self.assertFalse(report.accepted)
        self.assertEqual(report.verdict, "runtime_error")
        self.assertIn("twoSum", report.error_message)
