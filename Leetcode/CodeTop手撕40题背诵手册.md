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

**思路**：维护容量为 $k$ 的**小顶堆**，堆里始终是当前最大的 $k$ 个数，堆顶（这 $k$ 个中最小的）即第 $k$ 大，$O(n\log k)$ / 空间 $O(k)$。也可快排分区随机选择（平均 $O(n)$，最坏 $O(n^2)$）。

```python
import heapq
def findKthLargest(nums, k):
    heap = []                               # 小顶堆，容量固定为 k
    for x in nums:
        if len(heap) < k:
            heapq.heappush(heap, x)         # 先填满 k 个
        elif x > heap[0]:                   # 比堆顶大才有资格进来
            heapq.heapreplace(heap, x)      # 弹堆顶+压入，一次 O(log k)
    return heap[0]                          # 堆顶 = 第 k 大
```

**为什么是小顶堆**：要淘汰的是「前 $k$ 大中最早的最小值」，小顶堆堆顶正好是这个门槛；且空间只占 $O(k)$，海量数据/数据流（$n$ 装不下内存）依然可做，快排分区不行。

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

**思路**：后序递归；命中 p/q 就返回，左右都非空说明当前节点是分叉点。$O(n)$统计每个节点作为根的子树中有多少个目标点，**第一个满足`目标点数量 = 2` 的节点就是答案**
1.定义一个全局变量`LCA = None`
2.定义`dfs(node)` 返回 以`node`为根的子树中目标点的个数`cnt`。
3.自底向上的DFS,统计左右子树的目标点，以及检查`node`是否属于`p , q` 以得到`cnt`。
4.每次检查`node`是否满足**性质1(cnt = 2)** , `LCA`就是DFS过程中最早的满足**性质1**的节点。

```python
def lowestCommonAncestor(root, p, q):
    if not root or root == p or root == q: #找到目标节点或者搜到底
        return root
    left = lowestCommonAncestor(root.left, p, q) #搜左边
    right = lowestCommonAncestor(root.right, p, q) #搜右边
    if left and right: return root #如果两边都有就是答案
    return left or right #返回有的
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

快手一面手撕 → 详细解析（还原序列 / 变体题 / 正确性证明）见 [[秋招/面经/快手 AI infra面经#Q15 手撕：最长递增子序列（LC300）]]

**题目**：给定整数数组，找出其中最长**严格递增子序列**的长度（子序列不要求连续）。

**思路**：动态规划定义 dp[i]dp[i] 表示以第 ii 个元素结尾的最长递增子序列长度。然后对每个位置 ii，去看它前面的所有位置 jj：只要 nums[j]nums[j] 比 nums[i]nums[i] 小，就可以把 ii 接到 jj 后面，更新 dp[i]dp[i]。本质就是：尝试把当前元素接在之前所有“能接”的位置后面，取一个最长的。

```python
class Solution:
    def lengthOfLIS(self, nums: List[int]) -> int:
        n = len(nums)

        # dp[i] 表示以 nums[i] 作为结尾的最长递增子序列长度
        dp = [1] * n

        # ans 记录所有 dp[i] 中的最大值
        ans = 1

        # 从左到右枚举每个位置作为子序列结尾
        for i in range(n):
            # 枚举 i 前面的所有位置
            for j in range(i):
                # 只有 nums[j] < nums[i]，nums[i] 才能接在 nums[j] 后面
                if nums[j] < nums[i]:
                    dp[i] = max(dp[i], dp[j] + 1)

            # 更新最长递增子序列长度
            ans = max(ans, dp[i])

        return ans

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

res[-1][1] = max(res[-1][1], r)注意是取最大值

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
deque([root])
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

# 手撕题补充：20 道算法题 + 7 项机器学习基础

> 接续原《CodeTop 手撕 40 题背诵手册》，编号为 41–67。
> 每题包含题意、核心思路、可背诵实现、复杂度及易错点。编号不代表实时面试频率排名。
> 算法题使用 Python；机器学习部分使用 NumPy 手写核心计算，不调用内置 attention、softmax 或 normalization。

## 公共定义

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right
```

---

# 一、20 道算法补充题

## 41. LC76 最小覆盖子串

**题目**：给定字符串 `s` 和 `t`，返回 `s` 中包含 `t` 所有字符的最短子串；字符出现次数也必须满足。无解返回空字符串。

**思路**：滑动窗口。`need` 记录各字符还缺几个，`missing` 记录总共还缺多少个；补齐后不断收缩左边界。

```python
from collections import Counter


def minWindow(s, t):
    if not t:
        return ""
    need = Counter(t)
    missing = len(t)
    left = start = 0
    best = len(s) + 1
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        while missing == 0:
            if right - left + 1 < best:
                start, best = left, right - left + 1
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return "" if best > len(s) else s[start:start + best]
```

**复杂度**：时间 `O(|s| + |t|)`，辅助空间 `O(Σ)`，`Σ` 为两个字符串的不同字符数。

**易错点**：需要满足重复字符的次数，而不是仅满足字符种类；计数可以为负，表示窗口中的冗余字符。

## 42. LC239 滑动窗口最大值

**题目**：窗口大小为 `k`，从左到右滑过数组，返回每个窗口中的最大值。约定 `1 ≤ k ≤ len(nums)`。

**思路**：双端队列存下标，对应值单调递减；队首是最大值，先移除过期下标，再从队尾移除不可能成为最大值的元素。

```python
from collections import deque


def maxSlidingWindow(nums, k):
    q, ans = deque(), []
    for i, x in enumerate(nums):
        while q and q[0] <= i - k:
            q.popleft()
        while q and nums[q[-1]] <= x:
            q.pop()
        q.append(i)
        if i >= k - 1:
            ans.append(nums[q[0]])
    return ans
```

**复杂度**：时间 `O(n)`，辅助空间 `O(k)`，不含输出。每个下标最多入队、出队一次。

**易错点**：存下标而不是值，才能判断是否过期；单次循环虽有 `while`，总时间仍是线性。

## 43. LC560 和为 K 的子数组

**题目**：统计数组中和为 `k` 的非空连续子数组数量，数组可以包含负数。

**思路**：若当前前缀和为 `prefix`，此前每个值为 `prefix-k` 的前缀和都对应一个答案。哈希表存出现次数。

```python
from collections import defaultdict


def subarraySum(nums, k):
    count = defaultdict(int)
    count[0] = 1
    prefix = ans = 0
    for x in nums:
        prefix += x
        ans += count[prefix - k]
        count[prefix] += 1
    return ans
```

**复杂度**：时间 `O(n)`，辅助空间 `O(n)`。

**易错点**：初始化 `count[0] = 1`；先查再存，避免把空子数组算进去；有负数时不能直接用普通滑动窗口。

## 44. LC128 最长连续序列

**题目**：在未排序数组中找出最长连续整数序列的长度，不要求元素在原数组中相邻，要求期望线性时间。

**思路**：放入集合，只有 `x-1` 不存在时，才从 `x` 开始往后查找整段。

```python
def longestConsecutive(nums):
    values = set(nums)
    best = 0
    for x in values:
        if x - 1 not in values:
            end = x
            while end + 1 in values:
                end += 1
            best = max(best, end - x + 1)
    return best
```

**复杂度**：哈希操作期望 `O(1)` 时，时间 `O(n)`，辅助空间 `O(n)`。

**易错点**：遍历去重后的集合；必须从连续段起点出发，否则可能重复扫描。

## 45. LC31 下一个排列

**题目**：原地将数组改成字典序中的下一个排列；如果已是最大排列，改成最小排列。

**思路**：从右找第一个 `nums[i] < nums[i+1]` 的位置；与右侧刚好大于它的值交换；反转右侧后缀。

```python
def nextPermutation(nums):
    i = len(nums) - 2
    while i >= 0 and nums[i] >= nums[i + 1]:
        i -= 1
    if i >= 0:
        j = len(nums) - 1
        while nums[j] <= nums[i]:
            j -= 1
        nums[i], nums[j] = nums[j], nums[i]
    left, right = i + 1, len(nums) - 1
    while left < right:
        nums[left], nums[right] = nums[right], nums[left]
        left += 1
        right -= 1
```

**复杂度**：时间 `O(n)`，辅助空间 `O(1)`。

**易错点**：后缀原本非递增，从最右侧找第一个更大的数即可；全降序时 `i=-1`，反转整个数组。

## 46. LC41 缺失的第一个正数

**题目**：返回数组中没有出现过的最小正整数，要求时间 `O(n)`、辅助空间 `O(1)`。

**思路**：长度为 `n` 时答案在 `[1, n+1]`；把范围内的数 `x` 放到下标 `x-1`。

```python
def firstMissingPositive(nums):
    n = len(nums)
    for i in range(n):
        while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
            j = nums[i] - 1
            nums[i], nums[j] = nums[j], nums[i]
    for i, x in enumerate(nums):
        if x != i + 1:
            return i + 1
    return n + 1
```

**复杂度**：时间 `O(n)`，辅助空间 `O(1)`；每次有效交换都会让至少一个数归位。

**易错点**：必须检查目标位置是否已经是同一个值，否则重复元素会导致死循环；先保存目标下标 `j`。

## 47. LC34 查找元素的第一个和最后一个位置

**题目**：在非递减数组中返回 `target` 的首次、末次出现位置，不存在返回 `[-1, -1]`。

**思路**：两次半开区间二分：分别找第一个 `≥ target` 和第一个 `> target` 的位置。

```python
def searchRange(nums, target):
    def boundary(strict):
        left, right = 0, len(nums)
        while left < right:
            mid = (left + right) // 2
            if nums[mid] < target or (strict and nums[mid] == target):
                left = mid + 1
            else:
                right = mid
        return left

    first = boundary(False)
    if first == len(nums) or nums[first] != target:
        return [-1, -1]
    return [first, boundary(True) - 1]
```

**复杂度**：时间 `O(log n)`，辅助空间 `O(1)`。

**易错点**：搜索区间为 `[left, right)`，初始化 `right=n`，收缩右边界用 `right=mid`。

## 48. LC155 最小栈

**题目**：实现 `push`、`pop`、`top`、`getMin`，均要求 `O(1)`。查询、弹出操作保证栈非空。

**思路**：普通栈存值，辅助栈同步存“截至这一层的最小值”。

```python
class MinStack:
    def __init__(self):
        self.values = []
        self.mins = []

    def push(self, val):
        self.values.append(val)
        self.mins.append(min(val, self.mins[-1]) if self.mins else val)

    def pop(self):
        self.values.pop()
        self.mins.pop()

    def top(self):
        return self.values[-1]

    def getMin(self):
        return self.mins[-1]
```

**复杂度**：每个操作 `O(1)`，总辅助空间 `O(n)`。

**易错点**：重复最小值不能丢失；同步存每层最小值最容易写对。

## 49. LC32 最长有效括号

**题目**：给定只含 `(` 和 `)` 的字符串，返回最长连续有效括号子串的长度。

**思路**：栈存下标；栈底记录最近一次无法匹配的右括号位置，初始为 `-1`。

```python
def longestValidParentheses(s):
    stack = [-1]
    best = 0
    for i, ch in enumerate(s):
        if ch == '(':
            stack.append(i)
        else:
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                best = max(best, i - stack[-1])
    return best
```

**复杂度**：时间 `O(n)`，辅助空间 `O(n)`。

**易错点**：弹栈后为空时，要重设无效边界；长度是当前下标减栈顶下标。

## 50. LC739 每日温度

**题目**：对每天的温度，返回还要等待多少天才会出现更高温度；没有则为 0。

**思路**：单调栈存尚未找到答案的下标，对应温度非递增；当前更热时，逐个结算栈顶。

```python
def dailyTemperatures(temperatures):
    ans = [0] * len(temperatures)
    stack = []
    for i, value in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < value:
            j = stack.pop()
            ans[j] = i - j
        stack.append(i)
    return ans
```

**复杂度**：时间 `O(n)`，辅助空间 `O(n)`，不含输出。

**易错点**：题目要求严格更高，相等温度不能结算。

## 51. LC148 排序链表

**题目**：将单链表按升序排序，目标时间复杂度为 `O(n log n)`。

**思路**：快慢指针找中点，断成两段，分别排序再合并。

```python
def sortList(head):
    if not head or not head.next:
        return head
    slow, fast = head, head.next
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    right = slow.next
    slow.next = None
    left = sortList(head)
    right = sortList(right)
    dummy = tail = ListNode()
    while left and right:
        if left.val <= right.val:
            tail.next, left = left, left.next
        else:
            tail.next, right = right, right.next
        tail = tail.next
    tail.next = left or right
    return dummy.next
```

**复杂度**：时间 `O(n log n)`，辅助空间 `O(log n)`，来自递归栈。

**易错点**：必须断链；`fast=head.next` 保证两个节点时正确分开。若要求 `O(1)` 辅助空间，需改为自底向上的迭代归并，不能把这个递归版本说成常数空间。

## 52. LC138 随机链表的复制

**题目**：链表节点含 `next` 和 `random` 指针，`random` 可以指向任意节点或空；返回不共享节点的深拷贝。

**思路**：第一遍建立“原节点 → 新节点”的映射，第二遍连接 `next`、`random`。

```python
class RandomNode:
    def __init__(self, val, next=None, random=None):
        self.val, self.next, self.random = val, next, random


def copyRandomList(head):
    copies = {None: None}
    cur = head
    while cur:
        copies[cur] = RandomNode(cur.val)
        cur = cur.next
    cur = head
    while cur:
        copies[cur].next = copies[cur.next]
        copies[cur].random = copies[cur.random]
        cur = cur.next
    return copies[head]
```

**复杂度**：时间 `O(n)`，辅助空间 `O(n)`，不含输出节点。

**易错点**：按节点身份映射，不能按节点值映射；新节点的随机指针不能指回旧链表。常数辅助空间追问用“交织复制 → 设置 random → 拆分”，并恢复原链表。

## 53. LC105 从前序与中序遍历序列构造二叉树

**题目**：给定同一棵树的前序、中序遍历，节点值互不相同，重建二叉树。

**思路**：前序当前元素是根；哈希表查根在中序中的位置，递归先左后右。

```python
def buildTree(preorder, inorder):
    positions = {value: i for i, value in enumerate(inorder)}
    index = 0

    def build(left, right):
        nonlocal index
        if left > right:
            return None
        value = preorder[index]
        index += 1
        mid = positions[value]
        root = TreeNode(value)
        root.left = build(left, mid - 1)
        root.right = build(mid + 1, right)
        return root

    return build(0, len(inorder) - 1)
```

**复杂度**：时间 `O(n)`，辅助空间 `O(n)`，包括哈希表及递归栈，不含输出树。

**易错点**：前序指针必须先构造左子树再构造右子树；避免反复切片及调用 `inorder.index`，否则可能退化。

## 54. LC98 验证二叉搜索树

**题目**：判断二叉树是否为严格二叉搜索树：左子树所有值小于当前值，右子树所有值大于当前值。

**思路**：递归传递当前节点允许的开区间 `(low, high)`。

```python
def isValidBST(root):
    def check(node, low, high):
        if not node:
            return True
        if not low < node.val < high:
            return False
        return (check(node.left, low, node.val)
                and check(node.right, node.val, high))

    return check(root, float('-inf'), float('inf'))
```

**复杂度**：时间 `O(n)`，辅助空间 `O(h)`，`h` 为树高，最坏 `O(n)`。

**易错点**：不能只比较父子节点，需要满足所有祖先的约束；此题不允许重复值。

## 55. LC297 二叉树的序列化与反序列化

**题目**：将整数值二叉树编码为字符串，并能恢复出完全相同的树结构。

**思路**：前序遍历，空节点写 `#`，逗号分隔；反序列化按同样的根、左、右顺序消费标记。

```python
class Codec:
    def serialize(self, root):
        tokens = []

        def visit(node):
            if not node:
                tokens.append('#')
                return
            tokens.append(str(node.val))
            visit(node.left)
            visit(node.right)

        visit(root)
        return ','.join(tokens)

    def deserialize(self, data):
        tokens = iter(data.split(','))

        def build():
            value = next(tokens)
            if value == '#':
                return None
            node = TreeNode(int(value))
            node.left = build()
            node.right = build()
            return node

        return build()
```

**复杂度**：按节点值编码长度有界计，时间 `O(n)`，辅助空间 `O(n)`；递归栈为 `O(h)`。若整数长度不固定，还需计入字符串总长度。

**易错点**：没有空节点标记就无法唯一恢复结构；空树序列化为 `#`。这里假设输入来自同一编码器，而不是任意外部字符串。

## 56. LC22 括号生成

**题目**：给定 `n` 对括号，生成所有有效括号组合。

**思路**：回溯；左括号数量不超过 `n`，右括号数量不超过已经放置的左括号数量。

```python
def generateParenthesis(n):
    ans, path = [], []

    def dfs(left, right):
        if left == right == n:
            ans.append(''.join(path))
            return
        if left < n:
            path.append('(')
            dfs(left + 1, right)
            path.pop()
        if right < left:
            path.append(')')
            dfs(left, right + 1)
            path.pop()

    dfs(0, 0)
    return ans
```

**复杂度**：结果数为卡特兰数 `C_n`，时间 `O(n C_n)`，辅助空间 `O(n)`，输出空间 `O(n C_n)`。

**易错点**：不是最后再判断合法性，而是在生成过程中剪枝。

## 57. LC78 子集

**题目**：给定无重复元素的数组，返回所有子集，包括空集。

**思路**：回溯枚举下一个选取位置；每次进入递归都收集当前路径。

```python
def subsets(nums):
    ans, path = [], []

    def dfs(start):
        ans.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            dfs(i + 1)
            path.pop()

    dfs(0)
    return ans
```

**复杂度**：时间 `O(n 2^n)`，辅助空间 `O(n)`，输出空间 `O(n 2^n)`。

**易错点**：收集时拷贝路径；递归传 `i+1`，避免重复使用元素。

## 58. LC322 零钱兑换

**题目**：给定正整数面额 `coins`，每种硬币可无限使用，求凑出非负金额 `amount` 所需最少硬币数；不能凑出返回 `-1`。

**思路**：`dp[x]` 表示凑出金额 `x` 的最少硬币数，枚举最后使用的一枚硬币。

```python
def coinChange(coins, amount):
    dp = [amount + 1] * (amount + 1)
    dp[0] = 0
    for value in range(1, amount + 1):
        for coin in coins:
            if coin <= value:
                dp[value] = min(dp[value], dp[value - coin] + 1)
    return -1 if dp[amount] == amount + 1 else dp[amount]
```

**复杂度**：时间 `O(amount × len(coins))`，辅助空间 `O(amount)`。

**易错点**：`dp[0]=0`，其他状态初始化不可达；最少枚数、组合数、排列数是不同问题，不能随意套同一循环顺序。

## 59. LC139 单词拆分

**题目**：判断字符串能否拆成字典中的若干非空单词，字典单词可以重复使用。

**思路**：`dp[i]` 表示前 `i` 个字符能否拆分；枚举最后一个单词的长度，字典转集合。

```python
def wordBreak(s, wordDict):
    words = set(wordDict)
    lengths = {len(word) for word in words if word}
    dp = [False] * (len(s) + 1)
    dp[0] = True
    for end in range(1, len(s) + 1):
        for length in lengths:
            start = end - length
            if start >= 0 and dp[start] and s[start:end] in words:
                dp[end] = True
                break
    return dp[-1]
```

**复杂度**：设字符串长度为 `n`，不同单词长度数为 `U`，最长单词长度为 `L`，字典总字符数为 `W`。Python 中切片和字符串哈希都需计入，时间上界 `O(W + n U L)`，辅助空间 `O(n + |wordDict| + L)`，不含输入字符串存储。

**易错点**：`dp[0]=True`；不要忽略 Python 字符串切片、哈希的开销。若使用枚举全部切分点的切片写法，其 Python 最坏时间可能达到 `O(n^3)`。

## 60. LC207 课程表

**题目**：`prerequisites` 中 `[a,b]` 表示选课 `a` 前必须先选 `b`，判断是否能修完所有课程。

**思路**：建立边 `b → a`；入度为 0 的课入队，学习一门就删除其出边。处理课程数等于总数则无环。

```python
from collections import deque


def canFinish(numCourses, prerequisites):
    graph = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses
    for course, prerequisite in prerequisites:
        graph[prerequisite].append(course)
        indegree[course] += 1
    q = deque(i for i in range(numCourses) if indegree[i] == 0)
    done = 0
    while q:
        course = q.popleft()
        done += 1
        for nxt in graph[course]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                q.append(nxt)
    return done == numCourses
```

**复杂度**：时间、辅助空间均为 `O(V+E)`，`V` 为课程数，`E` 为依赖数。

**易错点**：边的方向是先修课指向后续课；不连通图和孤立课程也必须纳入。LC210 的变体只需保存出队顺序，若有环返回空列表。

---

# 二、机器学习与深度学习手撕

## 61. 稳定版 Softmax

**题目**：沿指定轴把实数 logits 转成概率，各概率非负、和为 1；避免大 logits 导致指数溢出。

**公式**：

\[
p_i = \frac{e^{x_i-m}}{\sum_j e^{x_j-m}},\qquad m=\max_j x_j
\]

**思路**：减最大值不改变概率；保留归约维度，便于广播。

```python
import numpy as np


def softmax(x, axis=-1):
    x = np.asarray(x, dtype=np.float64)
    shifted = x - np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(shifted)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)
```

**复杂度**：输入共 `N` 个元素，时间、辅助空间均为 `O(N)`。

**易错点**：不能直接 `exp(x)`；`keepdims=True` 避免广播出错。此函数约定 logits 有限、归约轴非空；attention 的全屏蔽行需另外处理。

**常见追问**：

- 温度采样：`softmax(logits / temperature)`，要求 `temperature > 0`。
- LogSoftmax：直接计算 `shifted - log(sum(exp(shifted)))`，不要先 softmax 再取 log。
- Jacobian：`∂p_i/∂x_j = p_i(δ_ij-p_j)`。
- 对归一化目标分布的交叉熵，单样本 logits 梯度为 `p-y`；batch mean 还需除以样本数。

## 62. Scaled Dot-Product Attention

**题目**：给定查询 `Q`、键 `K`、值 `V`，实现缩放点积注意力，支持布尔 mask 和 causal mask。

**公式**：

\[
\operatorname{Attention}(Q,K,V)
=\operatorname{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}+M\right)V
\]

**维度**：

- `Q: [..., Lq, dk]`
- `K: [..., Lk, dk]`
- `V: [..., Lk, dv]`
- 分数及权重：`[..., Lq, Lk]`
- 输出：`[..., Lq, dv]`

**思路**：点积 → 缩放 → 屏蔽 → 沿 key 维归一化 → 对 `V` 加权求和。布尔 mask 的 `True` 表示允许关注。

```python
import numpy as np


def attention(q, k, v, mask=None, causal=False):
    q = np.asarray(q, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    scores = (q @ np.swapaxes(k, -1, -2)) / np.sqrt(q.shape[-1])
    allowed = np.ones(scores.shape, dtype=bool)
    if mask is not None:
        allowed &= np.asarray(mask, dtype=bool)
    if causal:
        if q.shape[-2] != k.shape[-2]:
            raise ValueError("causal=True requires equal query/key lengths")
        length = q.shape[-2]
        allowed &= np.tril(np.ones((length, length), dtype=bool))
    scores = np.where(allowed, scores, -np.inf)
    row_max = np.max(scores, axis=-1, keepdims=True)
    row_max = np.where(np.isneginf(row_max), 0.0, row_max)
    exp_scores = np.exp(scores - row_max)
    denominator = exp_scores.sum(axis=-1, keepdims=True)
    weights = np.divide(
        exp_scores,
        denominator,
        out=np.zeros_like(exp_scores),
        where=denominator > 0,
    )
    return weights @ v, weights
```

**复杂度**：单个 batch、单个 head 的时间为 `O(Lq Lk (dk+dv))`，分数/权重空间为 `O(Lq Lk)`；batch 和 head 数量额外相乘。自注意力且 `dk=dv=d` 时为 `O(L²d)`。

**易错点**：

- softmax 沿最后一个维度，也就是 key 维进行。
- mask 必须在 softmax 前应用；被屏蔽位置权重为 0。
- 本实现对完全屏蔽的查询行约定权重、输出均为 0，避免 `-inf - (-inf)` 产生 NaN。
- `causal=True` 只适用于未使用 KV cache 的等长注意力；缓存解码需根据绝对位置构造显式 mask，不能直接套左上三角。
- 约定 `Q/K/V` 有限，key 长度与 `dk` 非零，mask 可广播到分数形状。

**常见追问**：独立、零均值、单位方差的 Q/K 分量，其点积方差约为 `dk`；除以 `sqrt(dk)` 能控制分数尺度，缓解 softmax 饱和。FlashAttention 通过分块和在线 softmax 避免存储完整注意力矩阵，并非消除标准密集注意力的二次计算量。

## 63. Multi-Head Attention

**题目**：实现自注意力多头模块，输入 `[B,L,D]`，头数 `H`，要求 `D % H == 0`，输出仍为 `[B,L,D]`。

**公式**：

\[
\text{head}_i=\operatorname{Attention}(XW_i^Q,XW_i^K,XW_i^V),\quad
\operatorname{MHA}(X)=\operatorname{Concat}(\text{head}_1,\ldots,\text{head}_H)W^O
\]

**思路**：先做 Q/K/V 投影，再拆成多个头，每个头独立计算注意力，最后合并并做输出投影。依赖第 62 节的 `attention`。

```python
import numpy as np


class MultiHeadAttention:
    def __init__(self, d_model, num_heads, seed=0):
        if d_model <= 0 or num_heads <= 0 or d_model % num_heads:
            raise ValueError("d_model must be positive and divisible by num_heads")
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        rng = np.random.default_rng(seed)
        scale = 1.0 / np.sqrt(d_model)
        self.wq = rng.normal(0, scale, (d_model, d_model))
        self.wk = rng.normal(0, scale, (d_model, d_model))
        self.wv = rng.normal(0, scale, (d_model, d_model))
        self.wo = rng.normal(0, scale, (d_model, d_model))
        self.bq = np.zeros(d_model)
        self.bk = np.zeros(d_model)
        self.bv = np.zeros(d_model)
        self.bo = np.zeros(d_model)

    def forward(self, x, mask=None, causal=False):
        x = np.asarray(x, dtype=np.float64)
        batch, length, width = x.shape
        if width != self.d_model:
            raise ValueError("input width must equal d_model")

        def split(projected):
            return projected.reshape(
                batch, length, self.num_heads, self.head_dim
            ).transpose(0, 2, 1, 3)

        q = split(x @ self.wq + self.bq)
        k = split(x @ self.wk + self.bk)
        v = split(x @ self.wv + self.bv)
        context, weights = attention(q, k, v, mask=mask, causal=causal)
        merged = context.transpose(0, 2, 1, 3).reshape(batch, length, width)
        return merged @ self.wo + self.bo, weights
```

**维度变化**：`[B,L,D] → [B,L,H,dh] → [B,H,L,dh] → [B,H,L,L] → [B,H,L,dh] → [B,L,H,dh] → [B,L,D]`。

**复杂度**：时间 `O(BLD² + BL²D)`；分数/权重空间 `O(BHL²)`，投影中间张量 `O(BLD)`，参数空间 `O(D²)`。带 bias 的参数量为 `4D²+4D`。

**易错点**：

- 合并头之前先 transpose，不能直接把 `[B,H,L,dh]` reshape 成 `[B,L,D]`。
- `[L,L]` mask 可广播到所有 batch/head；每个 batch 的 key padding mask 要整理成 `[B,1,1,L]`；每个 batch 的二维注意力 mask 用 `[B,1,L,L]`。
- 本模板为纯自注意力前向，不含 dropout、残差、归一化或训练反向；交叉注意力需分别传入 query 输入和 key/value 输入。
- 迁移到 PyTorch 后，transpose 结果若用 `view` 通常需先 `.contiguous()`，或直接使用 `reshape`。

**常见追问**：标准 MHA 的 Q/K/V 头数相同；MQA 共享一个 KV 头，GQA 让多组 Q 头共享较少的 KV 头，主要降低 KV cache 大小及解码时的 KV 读取带宽。

## 64. LayerNorm

**题目**：对每个 token 的最后一个维度做归一化，再进行可学习的仿射变换。输入 `[B,L,D]`，`gamma/beta` 为 `[D]`。

**公式**：

\[
\mu=\frac{1}{D}\sum_i x_i,\quad
\sigma^2=\frac{1}{D}\sum_i(x_i-\mu)^2,\quad
 y_i=\gamma_i\frac{x_i-\mu}{\sqrt{\sigma^2+\epsilon}}+\beta_i
\]

**思路**：最后一维求均值、总体方差，保留维度广播。约定 `eps > 0`。

```python
import numpy as np


def layer_norm(x, gamma, beta, eps=1e-5):
    x = np.asarray(x, dtype=np.float64)
    gamma = np.asarray(gamma, dtype=np.float64)
    beta = np.asarray(beta, dtype=np.float64)
    mean = x.mean(axis=-1, keepdims=True)
    variance = ((x - mean) ** 2).mean(axis=-1, keepdims=True)
    normalized = (x - mean) / np.sqrt(variance + eps)
    return normalized * gamma + beta
```

**复杂度**：时间、辅助空间均为 `O(BLD)`；仿射参数量 `2D`。

**易错点**：总体方差除以 `D`，不是 `D-1`；若用 PyTorch `var`，要设 `unbiased=False` 或 `correction=0`。`eps` 加在根号内部。

**常见追问**：LayerNorm 不跨 batch 统计，训练和推理不依赖 running statistics；BatchNorm 则通常按通道跨 batch、空间维统计。`gamma=1,beta=0` 时输出均值约为 0，由于 `eps`，方差不一定精确等于 1。

## 65. RMSNorm

**题目**：对每个 token 最后一维按均方根缩放，不减均值，再乘可学习参数 `gamma`。

**公式**：

\[
 y_i=\gamma_i\frac{x_i}{\sqrt{\frac{1}{D}\sum_j x_j^2+\epsilon}}
\]

**思路**：平方 → 求均值 → 加 eps → 开根号 → 缩放。约定 `eps > 0`。

```python
import numpy as np


def rms_norm(x, gamma, eps=1e-6):
    x = np.asarray(x, dtype=np.float64)
    gamma = np.asarray(gamma, dtype=np.float64)
    mean_square = (x * x).mean(axis=-1, keepdims=True)
    return x / np.sqrt(mean_square + eps) * gamma
```

**复杂度**：时间、辅助空间均为 `O(BLD)`；该版本参数量为 `D`。

**易错点**：不能写成标准差归一化；没有减均值，一般也没有 beta。输出均值不必为 0。

**常见追问**：LayerNorm 做“中心化 + 缩放”，RMSNorm 只做“缩放”，计算更简洁；二者不能视为数值等价。半精度实现通常用 FP32 累积平方和、统计量，再转回目标 dtype。

## 66. KNN 分类

**题目**：给定训练特征 `X_train: [N,D]`、标签 `y_train: [N]` 和测试特征 `X_test: [M,D]`，用欧氏距离找最近 `k` 个样本，多数投票分类。

**思路**：逐个测试样本计算平方距离，取最近 k 个标签，统计票数。约定标签为可排序的整数或字符串；票数相同时选排序更小的标签，距离相同时按训练输入顺序选邻居。

```python
import numpy as np


def knn_predict(X_train, y_train, X_test, k=3):
    X_train = np.asarray(X_train, dtype=np.float64)
    X_test = np.asarray(X_test, dtype=np.float64)
    y_train = np.asarray(y_train)
    if not 1 <= k <= len(X_train):
        raise ValueError("k must be between 1 and the training size")
    predictions = []
    for x in X_test:
        distances = ((X_train - x) ** 2).sum(axis=1)
        indices = np.argsort(distances, kind='stable')[:k]
        labels, counts = np.unique(y_train[indices], return_counts=True)
        predictions.append(labels[np.argmax(counts)])
    return np.asarray(predictions, dtype=y_train.dtype)
```

**复杂度**：时间 `O(M(ND + N log N))`，单个查询的辅助空间 `O(ND+N)`，不含输入和输出；这里使用完整排序以明确处理距离相等。

**易错点**：

- 按行计算距离，即 `axis=1`；平方距离足以排序，不必开平方。
- 特征尺度不同会支配距离，需要先标准化；标准化参数只能由训练集拟合，避免数据泄漏。
- KNN 分类是多数投票；KNN 回归通常取邻居目标的均值。
- `k` 较小容易受噪声影响，较大更平滑但可能欠拟合；奇数 k 不能保证多分类时没有平票。

**常见追问**：用 `np.argpartition(distances, k-1)[:k]` 可将邻居选取的期望时间降为 `O(N)`，但第 k 个距离并列时要另外定义选择规则；KD-tree 在低维可能有效，高维会遭遇维度灾难。

## 67. SiLU / Swish 激活函数

**题目**：实现逐元素激活 `SiLU(x) = x × sigmoid(x)`，避免计算 sigmoid 时指数溢出。

**公式**：

\[
\operatorname{SiLU}(x)=x\sigma(x),\qquad
\operatorname{SiLU}'(x)=\sigma(x)+x\sigma(x)(1-\sigma(x))
\]

**思路**：非负输入用 `1/(1+exp(-x))`，负输入用 `exp(x)/(1+exp(x))`，两支的指数输入均不为正。

```python
import numpy as np


def sigmoid(x):
    x = np.asarray(x, dtype=np.float64)
    result = np.empty_like(x)
    positive = x >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    result[~positive] = exp_x / (1.0 + exp_x)
    return result


def silu(x):
    x = np.asarray(x, dtype=np.float64)
    return x * sigmoid(x)


def silu_grad(x):
    x = np.asarray(x, dtype=np.float64)
    probability = sigmoid(x)
    return probability + x * probability * (1.0 - probability)
```

**复杂度**：输入共 `N` 个元素，时间、辅助空间均为 `O(N)`。

**易错点**：SiLU 不是 ReLU，也不是 `sigmoid(x)`；它允许小幅负输出，并且不是全局单调函数。代码约定输入有限。

**常见追问**：

- SiLU 是 `beta=1` 的 Swish：`Swish_beta(x)=x sigmoid(beta x)`。
- SwiGLU 不是单独的 SiLU，而是门控结构，例如 `SiLU(xW_gate) ⊙ (xW_up)`，再接输出投影。
- ReLU 非光滑且负区间梯度为 0；SiLU 光滑。SiLU 在 `x=0` 的导数为 `1/2`。

---

# 三、速查卡

| 编号 | 题目 / 模块 | 背诵关键词 |
|---|---|---|
| 41 | LC76 最小覆盖子串 | need + missing，补齐后收缩 |
| 42 | LC239 窗口最大值 | 单调队列，下标过期，队首最大 |
| 43 | LC560 和为 K | 前缀和频次，先查后存，0 出现一次 |
| 44 | LC128 最长连续序列 | 集合，只从无前驱的起点扩展 |
| 45 | LC31 下一个排列 | 找下降点，交换更大值，反转后缀 |
| 46 | LC41 缺失正数 | x 放 x-1，重复值防死循环 |
| 47 | LC34 查左右边界 | 第一个 ≥ target，第一个 > target |
| 48 | LC155 最小栈 | 值栈 + 每层最小值栈 |
| 49 | LC32 最长有效括号 | 下标栈，-1 哨兵，无效边界 |
| 50 | LC739 每日温度 | 非递增下标栈，严格更热才结算 |
| 51 | LC148 排序链表 | 找中断链，递归归并 |
| 52 | LC138 随机链表复制 | 节点身份映射，先建节点后连指针 |
| 53 | LC105 重建树 | 前序取根，中序划范围，先左后右 |
| 54 | LC98 验证 BST | 祖先传上下界，严格开区间 |
| 55 | LC297 序列化 | 前序 + 空标记，同顺序还原 |
| 56 | LC22 括号生成 | 左 < n，右 < 左 |
| 57 | LC78 子集 | 每层收集，i+1，拷贝路径 |
| 58 | LC322 零钱兑换 | dp[0]=0，不可达初始化，最少枚数 |
| 59 | LC139 单词拆分 | 可达前缀 + 字典匹配 |
| 60 | LC207 课程表 | 先修指向后续，入度 0 队列，计数判环 |
| 61 | Softmax | 减最大值，最后维归一化 |
| 62 | Attention | QKᵀ / sqrt(dk)，mask，softmax，乘 V |
| 63 | MHA | 投影，拆头，注意力，转置合头，输出投影 |
| 64 | LayerNorm | 减均值，除标准差，gamma + beta |
| 65 | RMSNorm | 不减均值，除均方根，只乘 gamma |
| 66 | KNN | 平方距离，最近 k 个，多数投票 |
| 67 | SiLU | x × sigmoid(x)，分支避免溢出 |

# 四、建议的自测用例

- 最小覆盖：`s="ADOBECODEBANC", t="ABC" → "BANC"`；`s="a", t="aa" → ""`。
- 滑动窗口：`[1,3,-1,-3,5,3,6,7], k=3 → [3,3,5,5,6,7]`；补测 `k=1` 和 `k=n`。
- 前缀和：`[1,1,1], k=2 → 2`；`[0,0], k=0 → 3`；加入负数测试。
- 下一个排列：`[1,2,3] → [1,3,2]`；`[3,2,1] → [1,2,3]`；`[1,1,5] → [1,5,1]`。
- 缺失正数：`[3,4,-1,1] → 2`；`[1,1] → 2`；空数组返回 1。
- 二分：空数组、目标不存在、所有元素相等、目标在首尾。
- 链表：空链表、单节点、两个节点、重复值；随机指针测空指针、自指及回指。
- 树：空树、单节点、退化树、负值、违反祖先但满足父子大小关系的伪 BST；序列化往返结构一致。
- 回溯：空数组子集为 `[[]]`；`n=3` 的括号组合有 5 个。
- DP：`coins=[1,2,5], amount=11 → 3`；`coins=[2], amount=3 → -1`；`amount=0 → 0`。
- 拓扑：无依赖、自环、两节点环、不连通图。
- Softmax：`[1000,1001,1002]` 不溢出，概率和为 1；增加同一常数后结果不变。
- Attention：causal 上三角权重为 0；有效行权重和为 1；全屏蔽行输出为 0；非等长 Q/K 用显式 mask。
- MHA：输出 `[B,L,D]`、权重 `[B,H,L,L]`；逐头计算结果与向量化版本一致；单头恒等投影时退化为标准 attention。
- LayerNorm：全相同输入、`gamma=1,beta=0` 时输出为 0；测试特征维为 1。
- RMSNorm：全零输入不会出现 NaN；常数非零输入与 LayerNorm 结果不同。
- KNN：`k=1`、`k=N`、票数相同、距离相同、非法 k、空测试集。
- SiLU：`x=-1000,0,1000` 不溢出；`SiLU(0)=0`、导数为 `0.5`；解析梯度与中心差分对比。

---

# 速查卡（只背关键词版）

| #    | 题目      | 核心模板                       | 熟悉程度 |
| ---- | ------- | -------------------------- | ---- |
| 3    | 最长无重复子串 | 滑窗 + 哈希记位置                 |      |
| 146  | LRU     | 哈希 + 双向链表，头新尾旧             |      |
| 206  | 反转链表    | prev/cur/nxt 三指针           |      |
| 215  | 第 K 大   | 快排分区 / 大小为 k 的小顶堆          |      |
| 25   | K 组翻转   | 先数够 k，反转 + 递归接尾            |      |
| 15   | 三数之和    | 排序 + 固定 + 双指针 + 三处去重       |      |
| 53   | 最大子数组和  | Kadane：cur = max(cur+x, x) |      |
| —    | 快排      | 随机枢轴分区，i 为小区右界             |      |
| 5    | 最长回文    | 中心扩展 ×(2n-1)               |      |
| 21   | 合并两链表   | 哑节点，小者先接，余者直接接             |      |
| 102  | 层序      | BFS，for len(q) 一层一收        |      |
| 1    | 两数之和    | 哈希先查 target-x 再存           |      |
| 200  | 岛屿数量    | 遇 1 计数 + DFS 淹没            |      |
| 33   | 旋转数组搜索  | 二分，必有半边有序                  |      |
| 46   | 全排列     | 回溯 + used，收时拷贝             |      |
| 88   | 合并有序数组  | 从后往前填                      |      |
| 121  | 买卖股票    | 记最小价，枚举卖出                  |      |
| 103  | 锯齿层序    | 层序 + 奇数层 reverse           |      |
| 20   | 有效括号    | 栈 + 右括号映射表                 |      |
| 236  | 最近公共祖先  | 后序递归，左右皆非空即答案              |      |
| 141  | 环形链表    | 快 2 慢 1                    |      |
| 92   | 反转区间    | 前驱 + 头插法                   |      |
| 54   | 螺旋矩阵    | 右下左上 + 缩边界                 |      |
| 23   | 合并 K 链表 | 小顶堆 (val, idx, node)       |      |
| 300  | LIS     | tails + 二分                 |      |
| 415  | 字符串相加   | 竖式加法 + 进位                  |      |
| 160  | 相交链表    | A+B 与 B+A 双指针              |      |
| 143  | 重排链表    | 找中 → 反转 → 交替合并             |      |
| 56   | 合并区间    | 排序，l ≤ 上段 r 则合并            |      |
| 42   | 接雨水     | 双指针移矮侧，侧最大值积水              |      |
| 72   | 编辑距离    | 二维 DP，替/删/插                |      |
| 124  | 最大路径和   | 后序，贡献取 0，节点处更新全路径          |      |
| 142  | 环入口     | 相遇后 head 出发同速再遇            |      |
| 19   | 删倒数第 N  | 哑节点，fast 先走 n              |      |
| 93   | 复原 IP   | 回溯 4 段，0~255 无前导零          |      |
| 1143 | LCS     | 二维 DP，同字符 +1               |      |
| 4    | 双数组中位数  | 短数组二分切分点                   |      |
| 82   | 去重链表    | 哑节点，删整段                    |      |
| 94   | 中序迭代    | 压左到底，弹后转右                  |      |
| 199  | 右视图     | 层序取每层最后                    |      |
