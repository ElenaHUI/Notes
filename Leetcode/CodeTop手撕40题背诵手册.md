---
tags:
  - leetcode
  - 面试
created: 2026-08-31
source: https://leetcode.cn/discuss/post/3623463/codetop-mian-shi-ti-ti-jie-ge-ren-you-hu-rjhy/
---


# CodeTop 手撕 40 题背诵手册

> 题目来自 CodeTop 高频面试手撕题（insorker 题解整理）。
> Python 实现，每题 = **题意 + 一句话思路 + 可背诵模板 + 复杂度**。相关笔记：[[Leetcode/LeetCode 刷题汇总]]、[[Leetcode/数据结构操作速记]]

## 公共定义（链表/树题默认使用）

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right
```

---

# 第一页

## 1. LC3 无重复字符的最长子串

**题目**：给定字符串 `s`，找出其中**不含重复字符**的最长子串的长度。

**思路**：滑动窗口，哈希表记录字符最近出现位置；右端扩张，遇到重复左端跳到重复位置之后。$O(n)$

```python
def lengthOfLongestSubstring(s: str) -> int:
    pos = {}                      # 字符 -> 最近下标
    left = ans = 0
    for right, c in enumerate(s):
        if c in pos and pos[c] >= left:
            left = pos[c] + 1
        pos[c] = right
        ans = max(ans, right - left + 1)
    return ans
```

## 2. LC146 LRU 缓存机制

**题目**：设计最近最少使用（LRU）缓存，支持 `get(key)` 和 `put(key, value)`，容量满时淘汰最久未使用的键，两个操作都要求 $O(1)$。

**思路**：哈希表 + 双向链表。哈希表 $O(1)$ 定位，链表维护使用顺序（头=最新，尾=最旧）。

```python
class Node:
    def __init__(self, key=0, val=0):
        self.key, self.val, self.prev, self.next = key, val, None, None

class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.map = {}
        self.head, self.tail = Node(), Node()      # 哨兵头尾
        self.head.next, self.tail.prev = self.tail, self.head

    def _remove(self, node):
        node.prev.next, node.next.prev = node.next, node.prev

    def _add_front(self, node):
        node.next, node.prev = self.head.next, self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: int) -> int:
        if key not in self.map:
            return -1
        node = self.map[key]
        self._remove(node); self._add_front(node)  # 提到头部
        return node.val

    def put(self, key: int, value: int) -> None:
        if key in self.map:
            self._remove(self.map[key])
        node = Node(key, value)
        self.map[key] = node
        self._add_front(node)
        if len(self.map) > self.cap:               # 淘汰尾部
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]
```

## 3. LC206 反转链表

**题目**：给定单链表头节点，将整个链表反转，返回新的头节点。

**思路**：迭代三指针，逐个掉头。$O(n)$，$O(1)$ 空间。

```python
def reverseList(head):
    prev, cur = None, head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev
```

## 4. LC215 数组中的第 K 个最大元素

**题目**：在未排序数组 `nums` 中找出第 `k` 大的元素（排序后从大到小第 k 个）。

**思路**：快排分区随机选择（平均 $O(n)$）；或大小为 $k$ 的小顶堆（$O(n\log k)$）。

```python
import random
def findKthLargest(nums, k):
    def quickselect(l, r):
        p = random.randint(l, r)                    # 随机化防最坏
        nums[p], nums[r] = nums[r], nums[p]
        pivot, i = nums[r], l
        for j in range(l, r):
            if nums[j] >= pivot:                    # 降序，第 k 大在下标 k-1
                nums[i], nums[j] = nums[j], nums[i]
                i += 1
        nums[i], nums[r] = nums[r], nums[i]
        if i == k - 1: return nums[i]
        return quickselect(i + 1, r) if i < k - 1 else quickselect(l, i - 1)
    return quickselect(0, len(nums) - 1)
```

堆写法（一行保底）：`heapq.nlargest(k, nums)[-1]`。

## 5. LC25 K 个一组翻转链表

**题目**：每 `k` 个节点一组进行翻转；不足 `k` 个的尾部保持原序，只能改变节点本身（不能只改值）。

**思路**：先数够 $k$ 个（不够则保持原样），反转本段，尾部递归接后续。$O(n)$

```python
def reverseKGroup(head, k):
    node, cnt = head, 0                 # 检查剩余是否有 k 个
    while node and cnt < k:
        node, cnt = node.next, cnt + 1
    if cnt < k:
        return head
    prev, cur = None, head              # 反转 k 个
    for _ in range(k):
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    head.next = reverseKGroup(cur, k)   # head 现在是本段尾
    return prev
```

## 6. LC15 三数之和

**题目**：在数组 `nums` 中找出所有和为 0 的三元组，答案中不能包含重复的三元组。

**思路**：排序 + 固定一个数 + 双指针；三处去重。$O(n^2)$

```python
def threeSum(nums):
    nums.sort()
    res = []
    for i in range(len(nums) - 2):
        if nums[i] > 0: break                          # 剪枝
        if i > 0 and nums[i] == nums[i - 1]: continue  # 去重①
        l, r = i + 1, len(nums) - 1
        while l < r:
            s = nums[i] + nums[l] + nums[r]
            if s == 0:
                res.append([nums[i], nums[l], nums[r]])
                while l < r and nums[l] == nums[l + 1]: l += 1   # 去重②
                while l < r and nums[r] == nums[r - 1]: r -= 1   # 去重③
                l += 1; r -= 1
            elif s < 0: l += 1
            else: r -= 1
    return res
```

## 7. LC53 最大子数组和

**题目**：在整数数组中找出一个**连续子数组**，使其和最大，返回该最大和。

**思路**：Kadane 动规：$f(i)=\max(f(i-1)+x,\ x)$。$O(n)$

```python
def maxSubArray(nums):
    cur = best = nums[0]
    for x in nums[1:]:
        cur = max(cur + x, x)
        best = max(best, cur)
    return best
```

## 8. 补充：手撕快速排序

**题目**：原地实现快速排序，将数组升序排列。

**思路**：分区 + 递归；随机枢轴避免最坏 $O(n^2)$。平均 $O(n\log n)$。

```python
import random
def quick_sort(nums, l, r):
    if l >= r: return
    p = random.randint(l, r)
    nums[p], nums[r] = nums[r], nums[p]
    pivot, i = nums[r], l              # i: 小于 pivot 区的右边界
    for j in range(l, r):
        if nums[j] < pivot:
            nums[i], nums[j] = nums[j], nums[i]
            i += 1
    nums[i], nums[r] = nums[r], nums[i]
    quick_sort(nums, l, i - 1)
    quick_sort(nums, i + 1, r)
```

## 9. LC5 最长回文子串

**题目**：给定字符串 `s`，返回其中最长的回文子串。

**思路**：中心向两边扩展，枚举 $2n-1$ 个中心。$O(n^2)$

```python
def longestPalindrome(s):
    def expand(l, r):
        while l >= 0 and r < len(s) and s[l] == s[r]:
            l -= 1; r += 1
        return l + 1, r - 1
    start = end = 0
    for i in range(len(s)):
        l1, r1 = expand(i, i)          # 奇中心
        l2, r2 = expand(i, i + 1)      # 偶中心
        if r1 - l1 > end - start: start, end = l1, r1
        if r2 - l2 > end - start: start, end = l2, r2
    return s[start:end + 1]
```

## 10. LC21 合并两个有序链表

**题目**：将两个升序链表合并为一个新的升序链表并返回。

**思路**：哑节点 + 双指针，小的先接。$O(n+m)$

```python
def mergeTwoLists(l1, l2):
    dummy = cur = ListNode()
    while l1 and l2:
        if l1.val <= l2.val:
            cur.next, l1 = l1, l1.next
        else:
            cur.next, l2 = l2, l2.next
        cur = cur.next
    cur.next = l1 or l2
    return dummy.next
```

## 11. LC102 二叉树的层序遍历

**题目**：逐层从左到右返回二叉树每层的节点值（列表的列表）。

**思路**：BFS 队列，一次处理一整层。$O(n)$

```python
from collections import deque
def levelOrder(root):
    if not root: return []
    res, q = [], deque([root])
    while q:
        level = []
        for _ in range(len(q)):        # 固定本层大小
            node = q.popleft()
            level.append(node.val)
            if node.left: q.append(node.left)
            if node.right: q.append(node.right)
        res.append(level)
    return res
```

## 12. LC1 两数之和

**题目**：在数组 `nums` 中找出和为目标值 `target` 的两个数，返回它们的下标（每种输入只有一组答案）。

**思路**：哈希表存「已见过的值→下标」，先查后存。$O(n)$

```python
def twoSum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
```

## 13. LC200 岛屿数量

**题目**：给定由 `'1'`（陆地）和 `'0'`（水）组成的二维网格，计算岛屿的数量（水平/垂直相连的陆地算一座岛）。

**思路**：遍历网格，遇到 `'1'` 计数加一并 DFS 把整座岛「淹没」。$O(mn)$

```python
def numIslands(grid):
    def dfs(i, j):
        if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] != '1':
            return
        grid[i][j] = '0'
        dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1)

    count = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                dfs(i, j)
                count += 1
    return count
```

## 14. LC33 搜索旋转排序数组

**题目**：升序无重复数组在某个未知下标处旋转过（如 `[4,5,6,7,0,1,2]`），在其中搜索 `target`，返回下标或 -1，要求 $O(\log n)$。

**思路**：二分；中点必有一侧有序，看 target 是否落在有序那侧。$O(\log n)$

```python
def search(nums, target):
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target: return mid
        if nums[l] <= nums[mid]:                    # 左半有序
            if nums[l] <= target < nums[mid]: r = mid - 1
            else: l = mid + 1
        else:                                       # 右半有序
            if nums[mid] < target <= nums[r]: l = mid + 1
            else: r = mid - 1
    return -1
```

## 15. LC46 全排列

**题目**：给定一个**不含重复数字**的数组，返回其所有可能的排列。

**思路**：回溯 + used 数组。$O(n\cdot n!)$

```python
def permute(nums):
    res, path, used = [], [], [False] * len(nums)
    def backtrack():
        if len(path) == len(nums):
            res.append(path[:])            # 注意拷贝
            return
        for i, x in enumerate(nums):
            if used[i]: continue
            used[i] = True
            path.append(x)
            backtrack()
            path.pop()
            used[i] = False
    backtrack()
    return res
```

## 16. LC88 合并两个有序数组（原地）

**题目**：`nums1` 长度为 `m+n`、前 `m` 个元素有序，`nums2` 有 `n` 个有序元素；将 `nums2` 原地合并进 `nums1` 保持升序。

**思路**：反向双指针，从后往前填（利用 nums1 尾部空位）。$O(m+n)$

```python
def merge(nums1, m, nums2, n):
    p, i, j = m + n - 1, m - 1, n - 1
    while j >= 0:
        if i >= 0 and nums1[i] > nums2[j]:
            nums1[p] = nums1[i]; i -= 1
        else:
            nums1[p] = nums2[j]; j -= 1
        p -= 1
```

## 17. LC121 买卖股票的最佳时机

**题目**：给定数组 `prices` 表示每天股价，只能买入一次、卖出一次（先买后卖），求最大利润；无法获利则返回 0。

**思路**：维护历史最低价，枚举卖出日。$O(n)$

```python
def maxProfit(prices):
    min_price, profit = float('inf'), 0
    for p in prices:
        min_price = min(min_price, p)
        profit = max(profit, p - min_price)
    return profit
```

## 18. LC103 二叉树的锯齿形层次遍历

**题目**：层序遍历二叉树，但各层方向交替：第一层左→右，第二层右→左，依此往返。

**思路**：层序 BFS，奇数层（第 2、4…层）反转结果。$O(n)$

```python
from collections import deque
def zigzagLevelOrder(root):
    if not root: return []
    res, q = [], deque([root])
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left: q.append(node.left)
            if node.right: q.append(node.right)
        res.append(level if len(res) % 2 == 0 else level[::-1])
    return res
```

## 19. LC20 有效的括号

**题目**：给定只含 `()[]{}` 的字符串，判断括号是否有效（左右配对且嵌套顺序正确）。

**思路**：栈匹配，右括号映射到对应左括号。$O(n)$

```python
def isValid(s):
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for c in s:
        if c in pairs:
            if not stack or stack[-1] != pairs[c]:
                return False
            stack.pop()
        else:
            stack.append(c)
    return not stack
```

## 20. LC236 二叉树的最近公共祖先

**题目**：给定二叉树和两个节点 `p`、`q`，找到它们的最近公共祖先（节点本身也可以是自己的祖先）。

**思路**：后序递归；命中 p/q 就返回，左右都非空说明当前节点是分叉点。$O(n)$

```python
def lowestCommonAncestor(root, p, q):
    if not root or root == p or root == q:
        return root
    left = lowestCommonAncestor(root.left, p, q)
    right = lowestCommonAncestor(root.right, p, q)
    if left and right: return root
    return left or right
```

---

# 第二页

## 21. LC141 环形链表

**题目**：给定链表头节点，判断链表中是否有环。

**思路**：快慢指针，快 2 慢 1，有环必相遇。$O(n)$

```python
def hasCycle(head):
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow == fast: return True
    return False
```

## 22. LC92 反转链表 II

**题目**：反转链表中位置 `left` 到 `right` 的节点（位置从 1 计），返回头节点，要求一趟扫描。

**思路**：哑节点 + 走到 left 前驱，「头插法」反转 $[left, right]$。$O(n)$

```python
def reverseBetween(head, left, right):
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(left - 1):
        prev = prev.next
    cur = prev.next
    for _ in range(right - left):       # 头插：把 cur.next 挪到 prev 之后
        nxt = cur.next
        cur.next = nxt.next
        nxt.next = prev.next
        prev.next = nxt
    return dummy.next
```

## 23. LC54 螺旋矩阵

**题目**：给定 `m×n` 矩阵，按顺时针螺旋顺序返回所有元素。

**思路**：按 右→下→左→上 模拟，走完一条边收缩一次边界。$O(mn)$

```python
def spiralOrder(matrix):
    res = []
    top, bottom, left, right = 0, len(matrix) - 1, 0, len(matrix[0]) - 1
    while top <= bottom and left <= right:
        for j in range(left, right + 1): res.append(matrix[top][j])
        top += 1
        for i in range(top, bottom + 1): res.append(matrix[i][right])
        right -= 1
        if top > bottom or left > right: break    # 单行/单列保护
        for j in range(right, left - 1, -1): res.append(matrix[bottom][j])
        bottom -= 1
        for i in range(bottom, top - 1, -1): res.append(matrix[i][left])
        left += 1
    return res
```

## 24. LC23 合并 K 个排序链表

**题目**：给定 `k` 个升序链表，将它们合并成一个升序链表。

**思路**：小顶堆，存各链表头；每次弹最小接上，再推入其后继。$O(N\log k)$

```python
import heapq
def mergeKLists(lists):
    heap = []
    for i, node in enumerate(lists):
        if node: heapq.heappush(heap, (node.val, i, node))   # i 防并列比较
    dummy = cur = ListNode()
    while heap:
        val, i, node = heapq.heappop(heap)
        cur.next = node
        cur = cur.next
        if node.next:
            heapq.heappush(heap, (node.next.val, i, node.next))
    return dummy.next
```

## 25. LC300 最长上升子序列

**题目**：给定整数数组，找出其中最长**严格递增子序列**的长度（子序列不要求连续）。

**思路**：维护 tails 数组（各长度 LIS 的最小结尾），二分找替换位。$O(n\log n)$

```python
import bisect
def lengthOfLIS(nums):
    tails = []
    for x in nums:
        i = bisect.bisect_left(tails, x)
        if i == len(tails): tails.append(x)
        else: tails[i] = x
    return len(tails)
```

## 26. LC415 字符串相加

**题目**：给定两个用字符串表示的非负整数，返回它们的和（大数相加，不能转整数）。

**思路**：模拟竖式加法，从末位开始，带进位。$O(\max(m,n))$

```python
def addStrings(a, b):
    res, carry, i, j = [], 0, len(a) - 1, len(b) - 1
    while i >= 0 or j >= 0 or carry:
        x = ord(a[i]) - 48 if i >= 0 else 0
        y = ord(b[j]) - 48 if j >= 0 else 0
        carry += x + y
        res.append(str(carry % 10))
        carry //= 10
        i -= 1; j -= 1
    return ''.join(res[::-1])
```

## 27. LC160 相交链表

**题目**：给定两个单链表，找出它们相交的起始节点；不相交返回 `None`。

**思路**：双指针分别走 A 链 + B 链、B 链 + A 链，等长后必在交点（或同时到 None）相遇。$O(m+n)$

```python
def getIntersectionNode(headA, headB):
    a, b = headA, headB
    while a != b:
        a = a.next if a else headB
        b = b.next if b else headA
    return a
```

## 28. LC143 重排链表

**题目**：将链表原地重排为 $L_0 \to L_n \to L_1 \to L_{n-1} \to \dots$ 的形式（只能移动节点，不能改值）。

**思路**：三步走——①快慢指针找中点 ②反转后半 ③交替合并。$O(n)$

```python
def reorderList(head):
    if not head: return
    slow, fast = head, head                     # ① 找中点
    while fast.next and fast.next.next:
        slow, fast = slow.next, fast.next.next
    prev, cur = None, slow.next                 # ② 反转后半
    slow.next = None
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    a, b = head, prev                           # ③ 交替合并
    while b:
        a.next, b.next, a, b = b, a.next, a.next, b.next
```

## 29. LC56 合并区间

**题目**：给定若干区间 `[l, r]`，合并所有重叠区间，返回不重叠的区间数组。

**思路**：按左端点排序，当前左端点 ≤ 上一个右端点则合并。$O(n\log n)$

```python
def merge(intervals):
    intervals.sort()
    res = []
    for l, r in intervals:
        if res and l <= res[-1][1]:
            res[-1][1] = max(res[-1][1], r)
        else:
            res.append([l, r])
    return res
```

## 30. LC42 接雨水

**题目**：给定 `n` 个非负整数表示宽度为 1 的柱子的高度，计算下雨之后这些柱子之间能接住多少雨水。

**思路**：双指针，移动较矮一侧；该侧历史最大值减去当前高度即存水量。$O(n)$

```python
def trap(height):
    l, r = 0, len(height) - 1
    left_max = right_max = ans = 0
    while l < r:
        if height[l] < height[r]:
            left_max = max(left_max, height[l])
            ans += left_max - height[l]
            l += 1
        else:
            right_max = max(right_max, height[r])
            ans += right_max - height[r]
            r -= 1
    return ans
```

## 31. LC72 编辑距离

**题目**：给定两个单词，求将 `word1` 转换成 `word2` 所需的最少操作数（每次操作限插入/删除/替换一个字符）。

**思路**：二维 DP，`dp[i][j]` = word1 前 i 个字符变成 word2 前 j 个字符的最少操作数。$O(mn)$

```python
def minDistance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                # 替换 / 删除 / 插入
                dp[i][j] = 1 + min(dp[i-1][j-1], dp[i-1][j], dp[i][j-1])
    return dp[m][n]
```

## 32. LC124 二叉树中的最大路径和

**题目**：在二叉树中找一条节点值之和最大的路径（路径可在任意节点起止，节点可为负，至少含一个节点）。

**思路**：后序 DFS 返回「该节点单边最大贡献」（负贡献取 0），在节点处用左右全路径更新全局答案。$O(n)$

```python
def maxPathSum(root):
    best = float('-inf')
    def dfs(node):
        nonlocal best
        if not node: return 0
        left = max(dfs(node.left), 0)                 # 只取正贡献
        right = max(dfs(node.right), 0)
        best = max(best, node.val + left + right)     # 经过本节点的全路径
        return node.val + max(left, right)            # 向父只能选一边
    dfs(root)
    return best
```

## 33. LC142 环形链表 II

**题目**：给定链表头节点，返回链表入环的第一个节点；无环返回 `None`。

**思路**：快慢指针相遇后，一个指针回 head，两者各走 1 步，再次相遇即环入口。$O(n)$

```python
def detectCycle(head):
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow == fast:
            node = head
            while node != slow:
                node, slow = node.next, slow.next
            return node
    return None
```

## 34. LC19 删除链表的倒数第 N 个节点

**题目**：删除链表的**倒数**第 `n` 个节点，返回头节点（要求一趟扫描）。

**思路**：哑节点 + 快慢指针，fast 先走 n 步。$O(L)$

```python
def removeNthFromEnd(head, n):
    dummy = ListNode(0, head)
    fast = slow = dummy
    for _ in range(n):
        fast = fast.next
    while fast.next:
        fast, slow = fast.next, slow.next
    slow.next = slow.next.next
    return dummy.next
```

## 35. LC93 复原 IP 地址

**题目**：给定只含数字的字符串，返回所有可能复原出的**合法 IP 地址**（4 段，每段 0~255，不能有前导零）。

**思路**：回溯切 4 段，每段 0~255 且无前导零。

```python
def restoreIpAddresses(s):
    res = []
    def backtrack(start, path):
        if len(path) == 4:
            if start == len(s):
                res.append('.'.join(path))
            return
        for length in range(1, 4):
            if start + length > len(s): break
            seg = s[start:start + length]
            if (len(seg) > 1 and seg[0] == '0') or int(seg) > 255:
                break                       # 更长的段也必然非法
            backtrack(start + length, path + [seg])
    backtrack(0, [])
    return res
```

## 36. LC1143 最长公共子序列

**题目**：给定两个字符串，返回它们最长公共子序列的长度（子序列不要求连续）。

**思路**：二维 DP，字符相同则 `dp[i-1][j-1]+1`，否则取左/上最大值。$O(mn)$

```python
def longestCommonSubsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]
```

## 37. LC4 寻找两个正序数组的中位数

**题目**：给定两个正序数组 `nums1`、`nums2`，返回它们合并后的中位数，要求 $O(\log(m+n))$。

**思路**：在较短数组上二分切分点 $i$，使左半共 $(m+n+1)/2$ 个且「左最大 ≤ 右最小」。$O(\log\min(m,n))$

```python
def findMedianSortedArrays(nums1, nums2):
    if len(nums1) > len(nums2):
        nums1, nums2 = nums2, nums1
    m, n = len(nums1), len(nums2)
    total_left = (m + n + 1) // 2
    l, r = 0, m
    while l <= r:
        i = (l + r) // 2                   # nums1 左半取 i 个
        j = total_left - i
        a_left  = nums1[i - 1] if i > 0 else float('-inf')
        a_right = nums1[i]     if i < m else float('inf')
        b_left  = nums2[j - 1] if j > 0 else float('-inf')
        b_right = nums2[j]     if j < n else float('inf')
        if a_left <= b_right and b_left <= a_right:      # 切分合法
            if (m + n) % 2 == 1:
                return max(a_left, b_left)
            return (max(a_left, b_left) + min(a_right, b_right)) / 2
        elif a_left > b_right:
            r = i - 1                      # nums1 取多了
        else:
            l = i + 1                      # nums1 取少了
```

## 38. LC82 删除排序链表中的重复元素 II

**题目**：在排序链表中，删除所有**出现过重复**的节点，只保留原链表中未重复的数字。

**思路**：哑节点站在重复段之前，发现 `cur.next` 与 `cur.next.next` 相等就删光整段。$O(n)$

```python
def deleteDuplicates(head):
    dummy = ListNode(0, head)
    cur = dummy
    while cur.next and cur.next.next:
        if cur.next.val == cur.next.next.val:
            x = cur.next.val
            while cur.next and cur.next.val == x:
                cur.next = cur.next.next
        else:
            cur = cur.next
    return dummy.next
```

## 39. LC94 二叉树的中序遍历（迭代）

**题目**：返回二叉树的中序遍历结果（左→根→右），面试通常要求用迭代法（栈）实现。

**思路**：栈 + 指针，一路压左到底，弹出后转向右子树。$O(n)$

```python
def inorderTraversal(root):
    res, stack = [], []
    cur = root
    while cur or stack:
        while cur:
            stack.append(cur)
            cur = cur.left
        cur = stack.pop()
        res.append(cur.val)
        cur = cur.right
    return res
```

## 40. LC199 二叉树的右视图

**题目**：想象自己站在二叉树右侧，按从顶到底的顺序返回能看到的节点值。

**思路**：层序 BFS，每层取最后一个节点（队列尾部）。$O(n)$

```python
from collections import deque
def rightSideView(root):
    if not root: return []
    res, q = [], deque([root])
    while q:
        res.append(q[-1].val)            # 本层最右
        for _ in range(len(q)):
            node = q.popleft()
            if node.left: q.append(node.left)
            if node.right: q.append(node.right)
    return res
```

---

# 速查卡（只背关键词版）

| # | 题目 | 核心模板 |
|---|------|----------|
| 3 | 最长无重复子串 | 滑窗 + 哈希记位置 |
| 146 | LRU | 哈希 + 双向链表，头新尾旧 |
| 206 | 反转链表 | prev/cur/nxt 三指针 |
| 215 | 第 K 大 | 快排分区 / 大小为 k 的小顶堆 |
| 25 | K 组翻转 | 先数够 k，反转 + 递归接尾 |
| 15 | 三数之和 | 排序 + 固定 + 双指针 + 三处去重 |
| 53 | 最大子数组和 | Kadane：cur = max(cur+x, x) |
| — | 快排 | 随机枢轴分区，i 为小区右界 |
| 5 | 最长回文 | 中心扩展 ×(2n-1) |
| 21 | 合并两链表 | 哑节点，小者先接，余者直接接 |
| 102 | 层序 | BFS，for len(q) 一层一收 |
| 1 | 两数之和 | 哈希先查 target-x 再存 |
| 200 | 岛屿数量 | 遇 1 计数 + DFS 淹没 |
| 33 | 旋转数组搜索 | 二分，必有半边有序 |
| 46 | 全排列 | 回溯 + used，收时拷贝 |
| 88 | 合并有序数组 | 从后往前填 |
| 121 | 买卖股票 | 记最小价，枚举卖出 |
| 103 | 锯齿层序 | 层序 + 奇数层 reverse |
| 20 | 有效括号 | 栈 + 右括号映射表 |
| 236 | 最近公共祖先 | 后序递归，左右皆非空即答案 |
| 141 | 环形链表 | 快 2 慢 1 |
| 92 | 反转区间 | 前驱 + 头插法 |
| 54 | 螺旋矩阵 | 右下左上 + 缩边界 |
| 23 | 合并 K 链表 | 小顶堆 (val, idx, node) |
| 300 | LIS | tails + 二分 |
| 415 | 字符串相加 | 竖式加法 + 进位 |
| 160 | 相交链表 | A+B 与 B+A 双指针 |
| 143 | 重排链表 | 找中 → 反转 → 交替合并 |
| 56 | 合并区间 | 排序，l ≤ 上段 r 则合并 |
| 42 | 接雨水 | 双指针移矮侧，侧最大值积水 |
| 72 | 编辑距离 | 二维 DP，替/删/插 |
| 124 | 最大路径和 | 后序，贡献取 0，节点处更新全路径 |
| 142 | 环入口 | 相遇后 head 出发同速再遇 |
| 19 | 删倒数第 N | 哑节点，fast 先走 n |
| 93 | 复原 IP | 回溯 4 段，0~255 无前导零 |
| 1143 | LCS | 二维 DP，同字符 +1 |
| 4 | 双数组中位数 | 短数组二分切分点 |
| 82 | 去重链表 | 哑节点，删整段 |
| 94 | 中序迭代 | 压左到底，弹后转右 |
| 199 | 右视图 | 层序取每层最后 |
