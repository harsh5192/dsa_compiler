"""Full definitions for the problems that ship with real content.

Everything here is original text written for this project.  The bundled sheet
files reference the widely published *titles* of popular DSA problems, but the
statements, examples and test cases below were authored here rather than copied
from any third party.  If you own a richer dataset, import it and it will
update these entries in place.
"""

PROBLEMS = [
    # ------------------------------------------------------------------ arrays
    {
        "title": "Two Sum",
        "slug": "two-sum",
        "difficulty": "Easy",
        "domains": ["Array", "Hashing"],
        "tags": ["Array", "Hash Table"],
        "description": (
            "Given an array of integers <code>nums</code> and an integer "
            "<code>target</code>, return the indices of the two numbers that add "
            "up to <code>target</code>.\n\nYou may assume that each input has "
            "<strong>exactly one</strong> solution and you may not use the same "
            "element twice. Return the answer in any order."
        ),
        "input_format": "The first element of the JSON array is the list of numbers, the second is the target.",
        "output_format": "A JSON array with the two indices.",
        "constraints": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\nOnly one valid answer exists.",
        "examples": (
            "Input: nums = [2,7,11,15], target = 9\n"
            "Output: [0,1]\n"
            "Explanation: nums[0] + nums[1] == 9."
        ),
        "function_name": "twoSum",
        "param_spec": [{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[2,7,11,15], 9]", "expected_output": "[0,1]", "is_sample": True},
            {"input": "[[3,2,4], 6]", "expected_output": "[1,2]", "is_sample": True},
            {"input": "[[3,3], 6]", "expected_output": "[0,1]", "is_sample": True},
            {"input": "[[-1,-2,-3,-4,-5], -8]", "expected_output": "[2,4]", "is_hidden": True},
            {"input": "[[1,5,9,13,7,4,3,2], 22]", "expected_output": "[2,3]", "is_hidden": True},
        ],
    },
    {
        "title": "Best Time to Buy and Sell Stock",
        "slug": "best-time-to-buy-and-sell-stock",
        "difficulty": "Easy",
        "domains": ["Array", "Dynamic Programming"],
        "tags": ["Array", "Dynamic Programming"],
        "description": (
            "You are given an array <code>prices</code> where <code>prices[i]</code> "
            "is the price of a given stock on day <code>i</code>.\n\nChoose one day "
            "to buy and a different later day to sell, and return the maximum profit "
            "you can achieve. If no profit is possible, return 0."
        ),
        "function_name": "maxProfit",
        "param_spec": [{"name": "prices", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[7,1,5,3,6,4]]", "expected_output": "5", "is_sample": True},
            {"input": "[[7,6,4,3,1]]", "expected_output": "0", "is_sample": True},
            {"input": "[[1,2,3,4,5]]", "expected_output": "4", "is_hidden": True},
        ],
    },
    {
        "title": "Maximum Subarray",
        "slug": "maximum-subarray",
        "difficulty": "Medium",
        "domains": ["Array", "Dynamic Programming"],
        "tags": ["Array", "Dynamic Programming", "Divide and Conquer"],
        "description": (
            "Given an integer array <code>nums</code>, find the contiguous "
            "subarray (containing at least one number) which has the largest sum "
            "and return its sum."
        ),
        "function_name": "maxSubArray",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[-2,1,-3,4,-1,2,1,-5,4]]", "expected_output": "6", "is_sample": True},
            {"input": "[[1]]", "expected_output": "1", "is_sample": True},
            {"input": "[[5,4,-1,7,8]]", "expected_output": "23", "is_sample": True},
            {"input": "[[-3,-2,-5]]", "expected_output": "-2", "is_hidden": True},
        ],
    },
    {
        "title": "Array Maximum Equal",
        "slug": "array-maximum-equal",
        "difficulty": "Medium",
        "domains": ["Array", "Hashing", "Union Find"],
        "tags": ["Array", "Hash Table", "Union Find"],
        "description": (
            "Given a list of numbers, return the number of items that appear more "
            "than once. This mirrors the classic \"elements appearing more than "
            "twice\" check: report how many distinct values occur two or more times."
        ),
        "function_name": "findDuplicates",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[1,2,3,1,2,3]]", "expected_output": "[1,2,3]", "is_sample": True},
            {"input": "[[1,1,1,1]]", "expected_output": "[1]", "is_sample": True},
            {"input": "[[1,2,3]]", "expected_output": "[]", "is_hidden": True},
        ],
    },
    {
        "title": "Missing Number",
        "slug": "missing-number",
        "difficulty": "Easy",
        "domains": ["Array", "Math"],
        "tags": ["Array", "Math", "Bit Manipulation"],
        "description": (
            "Given an array <code>nums</code> containing <code>n</code> distinct "
            "integers in the range <code>[0, n]</code>, return the one integer in "
            "that range which is missing."
        ),
        "function_name": "missingNumber",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[3,0,1]]", "expected_output": "2", "is_sample": True},
            {"input": "[[0,1]]", "expected_output": "2", "is_sample": True},
            {"input": "[[9,6,4,2,3,5,7,0,1]]", "expected_output": "8", "is_hidden": True},
        ],
    },
    {
        "title": "Kadane's Algorithm - Max Subarray Sum",
        "slug": "kadanes-algorithm-max-subarray-sum",
        "difficulty": "Medium",
        "domains": ["Array", "Dynamic Programming"],
        "tags": ["Array", "Dynamic Programming"],
        "description": (
            "Kadane's algorithm in its textbook form: extend the running sum while "
            "it helps, restart when it does not. Same contract as Maximum Subarray."
        ),
        "function_name": "maxSubArray",
        "param_spec": [{"name": "arr", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,-2,3,-1,2]]", "expected_output": "4", "is_sample": True},
            {"input": "[[-5,-2,-9]]", "expected_output": "-2", "is_hidden": True},
        ],
    },
    {
        "title": "Second Largest Element",
        "slug": "second-largest-element",
        "difficulty": "Easy",
        "domains": ["Array"],
        "tags": ["Array"],
        "description": "Return the second largest distinct element of the array, or -1 when it does not exist.",
        "function_name": "secondLargest",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[3,4,2,9,7]]", "expected_output": "7", "is_sample": True},
            {"input": "[[5,5]]", "expected_output": "-1", "is_sample": True},
            {"input": "[[1]]", "expected_output": "-1", "is_hidden": True},
        ],
    },
    # ----------------------------------------------------------------- sorting
    {
        "title": "Merge Sort",
        "slug": "merge-sort",
        "difficulty": "Medium",
        "domains": ["Sorting", "Recursion", "Divide and Conquer"],
        "tags": ["Sorting", "Divide and Conquer", "Recursion"],
        "description": (
            "Implement merge sort yourself. Return the sorted array as a new list; "
            "do not call the built-in sort."
        ),
        "function_name": "mergeSort",
        "param_spec": [{"name": "arr", "type": "int[]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n log n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[5,2,3,1]]", "expected_output": "[1,2,3,5]", "is_sample": True},
            {"input": "[[2,1]]", "expected_output": "[1,2]", "is_sample": True},
            {"input": "[[9,8,7,6,5,4,3,2,1]]", "expected_output": "[1,2,3,4,5,6,7,8,9]", "is_hidden": True},
        ],
    },
    {
        "title": "Bubble Sort",
        "slug": "bubble-sort",
        "difficulty": "Easy",
        "domains": ["Sorting"],
        "tags": ["Sorting"],
        "description": "Sort the array in place with the bubble sort algorithm and return it.",
        "function_name": "bubbleSort",
        "param_spec": [{"name": "arr", "type": "int[]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n^2)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[5,1,4,2,8]]", "expected_output": "[1,2,4,5,8]", "is_sample": True},
            {"input": "[[1,2,3]]", "expected_output": "[1,2,3]", "is_hidden": True},
        ],
    },
    {
        "title": "Sort Colors",
        "slug": "sort-colors",
        "difficulty": "Medium",
        "domains": ["Array", "Two Pointer"],
        "tags": ["Array", "Two Pointers", "Sorting"],
        "description": (
            "Given an array <code>nums</code> containing only the values 0, 1 and 2, "
            "sort them in place so that 0s come first, then 1s, then 2s. Do not use "
            "the built-in sort."
        ),
        "function_name": "sortColors",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[2,0,2,1,1,0]]", "expected_output": "[0,0,1,1,2,2]", "is_sample": True},
            {"input": "[[2,0,1]]", "expected_output": "[0,1,2]", "is_sample": True},
            {"input": "[[0]]", "expected_output": "[0]", "is_hidden": True},
        ],
    },
    # ---------------------------------------------------------------- strings
    {
        "title": "Valid Parentheses",
        "slug": "valid-parentheses",
        "difficulty": "Easy",
        "domains": ["String", "Stack"],
        "tags": ["Stack", "String"],
        "description": (
            "Given a string <code>s</code> containing just the characters "
            "<code>( ) { } [ ]</code>, return true if every opening bracket is closed "
            "by the same type of bracket in the correct order."
        ),
        "function_name": "isValid",
        "param_spec": [{"name": "s", "type": "string"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": '["()"]', "expected_output": "true", "is_sample": True},
            {"input": '["()[]{}"]', "expected_output": "true", "is_sample": True},
            {"input": '["(]"]', "expected_output": "false", "is_sample": True},
            {"input": '["([)]"]', "expected_output": "false", "is_hidden": True},
        ],
    },
    {
        "title": "Valid Palindrome",
        "slug": "valid-palindrome",
        "difficulty": "Easy",
        "domains": ["String", "Two Pointer"],
        "tags": ["Two Pointers", "String"],
        "description": (
            "Return true if <code>s</code> is a palindrome when ignoring "
            "non-alphanumeric characters and treating letters case-insensitively."
        ),
        "function_name": "isPalindrome",
        "param_spec": [{"name": "s", "type": "string"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": '["A man, a plan, a canal: Panama"]', "expected_output": "true", "is_sample": True},
            {"input": '["race a car"]', "expected_output": "false", "is_sample": True},
            {"input": '[" "]', "expected_output": "true", "is_hidden": True},
        ],
    },
    {
        "title": "Reverse String",
        "slug": "reverse-string",
        "difficulty": "Easy",
        "domains": ["String", "Two Pointer"],
        "tags": ["Two Pointers", "String"],
        "description": "Reverse the characters of the input string and return the result.",
        "function_name": "reverseString",
        "param_spec": [{"name": "s", "type": "string"}],
        "return_spec": "string",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": '["hello"]', "expected_output": '"olleh"', "is_sample": True},
            {"input": '["Hannah"]', "expected_output": '"hannaH"', "is_sample": True},
        ],
    },
    {
        "title": "Reverse Words in a String",
        "slug": "reverse-words-in-a-string",
        "difficulty": "Medium",
        "domains": ["String"],
        "tags": ["String"],
        "description": (
            "Given a sentence, return the sentence with the word order reversed and "
            "extra spaces collapsed."
        ),
        "function_name": "reverseWords",
        "param_spec": [{"name": "s", "type": "string"}],
        "return_spec": "string",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": '["the sky is blue"]', "expected_output": '"blue is sky the"', "is_sample": True},
            {"input": '["  hello   world  "]', "expected_output": '"world hello"', "is_hidden": True},
        ],
    },
    # ----------------------------------------------------------- binary search
    {
        "title": "Binary Search",
        "slug": "binary-search",
        "difficulty": "Easy",
        "domains": ["Binary Search", "Array"],
        "tags": ["Binary Search", "Array"],
        "description": (
            "Given a sorted array of distinct integers <code>nums</code> and a "
            "target value, return the index of the target, or -1 when it is absent."
        ),
        "function_name": "search",
        "param_spec": [{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(log n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[-1,0,3,5,9,12], 9]", "expected_output": "4", "is_sample": True},
            {"input": "[[-1,0,3,5,9,12], 2]", "expected_output": "-1", "is_sample": True},
            {"input": "[[5], 5]", "expected_output": "0", "is_hidden": True},
        ],
    },
    {
        "title": "Search in Rotated Sorted Array",
        "slug": "search-in-rotated-sorted-array",
        "difficulty": "Medium",
        "domains": ["Binary Search", "Array"],
        "tags": ["Binary Search", "Array"],
        "description": (
            "An ascending sorted array was rotated at an unknown pivot. Given the "
            "rotated array and a target, return its index or -1 in O(log n)."
        ),
        "function_name": "search",
        "param_spec": [{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(log n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[4,5,6,7,0,1,2], 0]", "expected_output": "4", "is_sample": True},
            {"input": "[[4,5,6,7,0,1,2], 3]", "expected_output": "-1", "is_sample": True},
            {"input": "[[1], 0]", "expected_output": "-1", "is_hidden": True},
        ],
    },
    {
        "title": "First and Last Position of Target",
        "slug": "first-and-last-position-of-target",
        "difficulty": "Medium",
        "domains": ["Binary Search", "Array"],
        "tags": ["Binary Search"],
        "description": (
            "Return the first and last index of <code>target</code> in the sorted "
            "array, or [-1, -1] when it is absent."
        ),
        "function_name": "searchRange",
        "param_spec": [{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(log n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[5,7,7,8,8,10], 8]", "expected_output": "[3,4]", "is_sample": True},
            {"input": "[[5,7,7,8,8,10], 6]", "expected_output": "[-1,-1]", "is_sample": True},
            {"input": "[[], 0]", "expected_output": "[-1,-1]", "is_hidden": True},
        ],
    },
    # ------------------------------------------------------------ linked list
    {
        "title": "Reverse Linked List",
        "slug": "reverse-linked-list",
        "difficulty": "Easy",
        "domains": ["Linked List"],
        "tags": ["Linked List"],
        "description": (
            "Given the head of a singly linked list, reverse the list and return "
            "the new head. The nodes themselves are given to you; you only need to "
            "relink them."
        ),
        "function_name": "reverseList",
        "param_spec": [{"name": "head", "type": "ListNode"}],
        "return_spec": "ListNode",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,2,3,4,5]]", "expected_output": "[5,4,3,2,1]", "is_sample": True},
            {"input": "[[1]]", "expected_output": "[1]", "is_sample": True},
            {"input": "[[]]", "expected_output": "[]", "is_hidden": True},
        ],
    },
    {
        "title": "Add Two Numbers",
        "slug": "add-two-numbers",
        "difficulty": "Medium",
        "domains": ["Linked List", "Math"],
        "tags": ["Linked List", "Math"],
        "description": (
            "Two non-empty linked lists represent two non-negative integers whose "
            "digits are stored in reverse order. Return the sum as a linked list in "
            "the same reversed order."
        ),
        "function_name": "addTwoNumbers",
        "param_spec": [{"name": "l1", "type": "ListNode"}, {"name": "l2", "type": "ListNode"}],
        "return_spec": "ListNode",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[2,4,3],[5,6,4]]", "expected_output": "[7,0,8]", "is_sample": True},
            {"input": "[[0],[0]]", "expected_output": "[0]", "is_sample": True},
            {"input": "[[9,9],[1]]", "expected_output": "[0,0,1]", "is_hidden": True},
        ],
    },
    {
        "title": "Linked List Cycle",
        "slug": "linked-list-cycle",
        "difficulty": "Easy",
        "domains": ["Linked List", "Two Pointer"],
        "tags": ["Linked List", "Two Pointers"],
        "description": (
            "Return true if the linked list contains a cycle. Because JSON cannot "
            "describe a self referencing list, the second argument "
            "<code>pos</code> carries the cycle information: it is the index "
            "(0 based) whose node the tail links back to, or <code>-1</code> when "
            "the list is acyclic."
        ),
        "function_name": "hasCycle",
        "param_spec": [{"name": "head", "type": "ListNode"}, {"name": "pos", "type": "int"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[3,2,0,-4], 1]", "expected_output": "true", "is_sample": True},
            {"input": "[[1,2], -1]", "expected_output": "false", "is_sample": True},
            {"input": "[[1], 0]", "expected_output": "true", "is_sample": True},
            {"input": "[[1,2,3,4], 3]", "expected_output": "true", "is_hidden": True},
            {"input": "[[1,2,3,4], -1]", "expected_output": "false", "is_hidden": True},
        ],
    },
    {
        "title": "Remove Nth Node From End of List",
        "slug": "remove-nth-node-from-end-of-list",
        "difficulty": "Medium",
        "domains": ["Linked List", "Two Pointer"],
        "tags": ["Linked List", "Two Pointers"],
        "description": (
            "Remove the n-th node from the end of the list and return its head "
            "(1-indexed from the end)."
        ),
        "function_name": "removeNthFromEnd",
        "param_spec": [{"name": "head", "type": "ListNode"}, {"name": "n", "type": "int"}],
        "return_spec": "ListNode",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,2,3,4,5], 2]", "expected_output": "[1,2,3,5]", "is_sample": True},
            {"input": "[[1], 1]", "expected_output": "[]", "is_sample": True},
            {"input": "[[1,2], 1]", "expected_output": "[1]", "is_hidden": True},
        ],
    },
    # ------------------------------------------------------------------ stack
    {
        "title": "Next Greater Element",
        "slug": "next-greater-element",
        "difficulty": "Medium",
        "domains": ["Stack", "Array"],
        "tags": ["Stack", "Monotonic Stack"],
        "description": (
            "For each element, return the index of the next strictly greater "
            "element to its right, or -1 when there is none."
        ),
        "function_name": "nextGreaterElement",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[1,2,1]]", "expected_output": "[2,-1,2]", "is_sample": True},
            {"input": "[[1,1,0,0,1]]", "expected_output": "[1,2,2,4,4]", "is_hidden": True},
        ],
    },
    {
        "title": "Min Stack",
        "slug": "min-stack",
        "difficulty": "Medium",
        "domains": ["Stack"],
        "tags": ["Stack", "Design"],
        "description": (
            "Design a stack that supports <code>push</code>, <code>pop</code>, "
            "<code>top</code> and <code>getMin</code>, all in O(1).\n\n"
            "You receive two arrays: <code>operations</code> lists the operation "
            "names to perform in order, and <code>values</code> holds the numbers to "
            "push, consumed in order. <code>push</code> and <code>pop</code> return "
            "nothing, so report one number per <code>top</code> and "
            "<code>getMin</code> call, in the order those calls appear. "
            "<code>getMin</code> must work in O(1) as well."
        ),
        "function_name": "solve",
        "param_spec": [
            {"name": "operations", "type": "string[]"},
            {"name": "values", "type": "int[]"},
        ],
        "return_spec": "int[]",
        "expected_time_complexity": "O(1) per operation",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {
                "input": '[["push","push","push","getMin","pop","top","getMin"],[-2,0,-3]]',
                "expected_output": "[-3,0,-2]",
                "is_sample": True,
                "explanation": "Push -2, 0, -3, then read the minimum.",
            },
            {
                "input": '[["push","getMin","top"],[5]]',
                "expected_output": "[5,5]",
                "is_sample": True,
            },
            {
                "input": '[["push","push","top","pop","getMin"],[7,-3]]',
                "expected_output": "[-3,7]",
                "is_hidden": True,
            },
        ],
    },
    # ------------------------------------------------------------------ queue
    {
        "title": "Sliding Window Maximum",
        "slug": "sliding-window-maximum",
        "difficulty": "Hard",
        "domains": ["Array", "Sliding Window", "Queue"],
        "tags": ["Sliding Window", "Monotonic Deque", "Heap"],
        "description": (
            "Given an array and a window size k, return the maximum value in each "
            "window of size k."
        ),
        "function_name": "maxSlidingWindow",
        "param_spec": [{"name": "nums", "type": "int[]"}, {"name": "k", "type": "int"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(k)",
        "test_cases": [
            {"input": "[[1,3,-1,-3,5,3,6,7], 3]", "expected_output": "[3,3,5,5,6,7]", "is_sample": True},
            {"input": "[[1], 1]", "expected_output": "[1]", "is_sample": True},
            {"input": "[[9,11], 2]", "expected_output": "[11]", "is_hidden": True},
        ],
    },
    {
        "title": "Number of Islands",
        "slug": "number-of-islands",
        "difficulty": "Medium",
        "domains": ["Matrix", "Graph", "BFS", "DFS"],
        "tags": ["Depth-First Search", "Breadth-First Search", "Union Find", "Matrix"],
        "description": (
            "Given an m x n grid of '1' (land) and '0' (water), return the number of "
            "islands. Neighbours share an edge."
        ),
        "function_name": "numIslands",
        "param_spec": [{"name": "grid", "type": "string[][]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(m * n)",
        "expected_space_complexity": "O(m * n)",
        "test_cases": [
            {
                "input": '[[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]]',
                "expected_output": "3",
                "is_sample": True,
            },
            {
                "input": '[[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","0","0","0"],["0","0","0","1","1"]]]',
                "expected_output": "1",
                "is_hidden": True,
            },
        ],
    },
    # ------------------------------------------------------------------ trees
    {
        "title": "Binary Tree Inorder Traversal",
        "slug": "binary-tree-inorder-traversal",
        "difficulty": "Easy",
        "domains": ["Tree", "Recursion", "Stack"],
        "tags": ["Tree", "Depth-First Search", "Recursion", "Binary Tree"],
        "description": (
            "Given the root of a binary tree, return the inorder traversal of its "
            "values. Input is the level-order array with nulls for missing children."
        ),
        "function_name": "inorderTraversal",
        "param_spec": [{"name": "root", "type": "TreeNode"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[1,null,2,3]]", "expected_output": "[1,3,2]", "is_sample": True},
            {"input": "[[]]", "expected_output": "[]", "is_sample": True},
            {"input": "[[1,2,3,4,5]]", "expected_output": "[4,2,5,1,3]", "is_hidden": True},
        ],
    },
    {
        "title": "Maximum Depth of Binary Tree",
        "slug": "maximum-depth-of-binary-tree",
        "difficulty": "Easy",
        "domains": ["Tree", "Recursion"],
        "tags": ["Tree", "Depth-First Search", "Binary Tree"],
        "description": "Return the maximum depth of the binary tree (the longest root-to-leaf path).",
        "function_name": "maxDepth",
        "param_spec": [{"name": "root", "type": "TreeNode"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[3,9,20,null,null,15,7]]", "expected_output": "3", "is_sample": True},
            {"input": "[[1,null,2]]", "expected_output": "2", "is_sample": True},
            {"input": "[[]]", "expected_output": "0", "is_hidden": True},
        ],
    },
    {
        "title": "Same Tree",
        "slug": "same-tree",
        "difficulty": "Easy",
        "domains": ["Tree", "Recursion"],
        "tags": ["Tree", "Depth-First Search", "Binary Tree"],
        "description": "Return true when the two trees have the same shape and values.",
        "function_name": "isSameTree",
        "param_spec": [{"name": "p", "type": "TreeNode"}, {"name": "q", "type": "TreeNode"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[1,2,3],[1,2,3]]", "expected_output": "true", "is_sample": True},
            {"input": "[[1,2],[1,null,2]]", "expected_output": "false", "is_sample": True},
        ],
    },
    {
        "title": "Binary Tree Level Order Traversal",
        "slug": "binary-tree-level-order-traversal",
        "difficulty": "Medium",
        "domains": ["Tree", "BFS", "Queue"],
        "tags": ["Tree", "Breadth-First Search", "Binary Tree"],
        "description": "Return the values of the tree grouped level by level, left to right.",
        "function_name": "levelOrder",
        "param_spec": [{"name": "root", "type": "TreeNode"}],
        "return_spec": "int[][]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[3,9,20,null,null,15,7]]", "expected_output": "[[3],[9,20],[15,7]]", "is_sample": True},
            {"input": "[[1]]", "expected_output": "[[1]]", "is_sample": True},
            {"input": "[[]]", "expected_output": "[]", "is_hidden": True},
        ],
    },
    {
        "title": "Validate Binary Search Tree",
        "slug": "validate-binary-search-tree",
        "difficulty": "Medium",
        "domains": ["Tree", "BST"],
        "tags": ["Tree", "Depth-First Search", "Binary Search Tree"],
        "description": "Return true when the tree satisfies the BST ordering property.",
        "function_name": "isValidBST",
        "param_spec": [{"name": "root", "type": "TreeNode"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[2,1,3]]", "expected_output": "true", "is_sample": True},
            {"input": "[[5,1,4,null,null,3,6]]", "expected_output": "false", "is_hidden": True},
        ],
    },
    # ------------------------------------------------------------------ graph
    {
        "title": "Number of Connected Components in an Undirected Graph",
        "slug": "number-of-connected-components-in-an-undirected-graph",
        "difficulty": "Medium",
        "domains": ["Graph", "Union Find", "BFS", "DFS"],
        "tags": ["Union Find", "Depth-First Search", "Breadth-First Search", "Graph"],
        "description": (
            "Given n nodes and the undirected edges between them, return the number "
            "of connected components. Edges are given as flat pairs."
        ),
        "function_name": "countComponents",
        "param_spec": [
            {"name": "n", "type": "int"},
            {"name": "edges", "type": "int[][]"},
        ],
        "return_spec": "int",
        "expected_time_complexity": "O(n + e)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[5, [[0,1],[0,2],[1,3],[2,3]]]", "expected_output": "2", "is_sample": True},
            {"input": "[6, [[0,1],[0,2],[0,3],[1,2],[1,3]]]", "expected_output": "2", "is_sample": True},
            {"input": "[3, []]", "expected_output": "3", "is_hidden": True},
        ],
    },
    {
        "title": "Bipartite Check",
        "slug": "bipartite-check",
        "difficulty": "Medium",
        "domains": ["Graph", "BFS", "DFS"],
        "tags": ["Breadth-First Search", "Depth-First Search", "Union Find", "Graph"],
        "description": (
            "Return true when the undirected graph can be two-coloured so that no "
            "edge joins two nodes of the same colour. Edges arrive as flat pairs."
        ),
        "function_name": "isBipartite",
        "param_spec": [{"name": "n", "type": "int"}, {"name": "edges", "type": "int[][]"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n + e)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[4, [[1,2],[2,3],[3,4],[4,1]]]", "expected_output": "false", "is_sample": True},
            {"input": "[3, [[1,2]]]", "expected_output": "true", "is_sample": True},
        ],
    },
    # --------------------------------------------------------- sliding window
    {
        "title": "Longest Substring Without Repeating Characters",
        "slug": "longest-substring-without-repeating-characters",
        "difficulty": "Medium",
        "domains": ["String", "Sliding Window", "Hashing"],
        "tags": ["Sliding Window", "Hash Table", "String"],
        "description": "Return the length of the longest substring without repeated characters.",
        "function_name": "lengthOfLongestSubstring",
        "param_spec": [{"name": "s", "type": "string"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": '["abcabcbb"]', "expected_output": "3", "is_sample": True},
            {"input": '["bbbbb"]', "expected_output": "1", "is_sample": True},
            {"input": '[""]', "expected_output": "0", "is_hidden": True},
        ],
    },
    # -------------------------------------------------------------------- dp
    {
        "title": "Climbing Stairs",
        "slug": "climbing-stairs",
        "difficulty": "Easy",
        "domains": ["Dynamic Programming", "Recursion"],
        "tags": ["Dynamic Programming", "Math", "Recursion"],
        "description": (
            "You are climbing a staircase with n steps. You may climb one or two "
            "steps at a time. Return the number of distinct ways to reach the top."
        ),
        "function_name": "climbStairs",
        "param_spec": [{"name": "n", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[2]", "expected_output": "2", "is_sample": True},
            {"input": "[3]", "expected_output": "3", "is_sample": True},
            {"input": "[10]", "expected_output": "89", "is_hidden": True},
        ],
    },
    {
        "title": "House Robber",
        "slug": "house-robber",
        "difficulty": "Medium",
        "domains": ["Dynamic Programming"],
        "tags": ["Dynamic Programming"],
        "description": (
            "Given the amount of money in each house, return the maximum amount you "
            "can rob without ever robbing two adjacent houses."
        ),
        "function_name": "rob",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,2,3,1]]", "expected_output": "4", "is_sample": True},
            {"input": "[[2,7,9,3,1]]", "expected_output": "12", "is_sample": True},
        ],
    },
    {
        "title": "Coin Change",
        "slug": "coin-change",
        "difficulty": "Medium",
        "domains": ["Dynamic Programming"],
        "tags": ["Dynamic Programming"],
        "description": (
            "Given coin denominations and an amount, return the fewest coins needed "
            "to make up that amount, or -1 when it cannot be made."
        ),
        "function_name": "coinChange",
        "param_spec": [{"name": "coins", "type": "int[]"}, {"name": "amount", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(amount * n)",
        "expected_space_complexity": "O(amount)",
        "test_cases": [
            {"input": "[[1,2,5], 11]", "expected_output": "3", "is_sample": True},
            {"input": "[[2], 3]", "expected_output": "-1", "is_sample": True},
            {"input": "[[1], 0]", "expected_output": "0", "is_hidden": True},
        ],
    },
    {
        "title": "Longest Increasing Subsequence",
        "slug": "longest-increasing-subsequence",
        "difficulty": "Medium",
        "domains": ["Dynamic Programming", "Binary Search"],
        "tags": ["Dynamic Programming", "Binary Search", "Array"],
        "description": "Return the length of the longest strictly increasing subsequence.",
        "function_name": "lengthOfLIS",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n log n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[10,9,2,5,3,7,101,18]]", "expected_output": "4", "is_sample": True},
            {"input": "[[0,1,0,3,2,3]]", "expected_output": "4", "is_sample": True},
            {"input": "[[7,7,7,7]]", "expected_output": "1", "is_hidden": True},
        ],
    },
    # -------------------------------------------------------------- backtracking
    {
        "title": "Permutations",
        "slug": "permutations",
        "difficulty": "Medium",
        "domains": ["Backtracking", "Recursion"],
        "tags": ["Backtracking", "Recursion"],
        "description": "Return all possible permutations of the distinct integers in nums.",
        "function_name": "permute",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int[][]",
        "expected_time_complexity": "O(n * n!)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[1,2,3]]", "expected_output": "[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]", "is_sample": True},
            {"input": "[[1]]", "expected_output": "[[1]]", "is_sample": True},
            {"input": "[[0,1]]", "expected_output": "[[0,1],[1,0]]", "is_hidden": True},
        ],
    },
    {
        "title": "N-Queens",
        "slug": "n-queens",
        "difficulty": "Hard",
        "domains": ["Backtracking", "Matrix"],
        "tags": ["Backtracking", "Matrix"],
        "description": (
            "Place n queens on an n x n board so that no two attack each other, "
            "using <code>\"Q\"</code> for a queen and <code>\".\"</code> for an "
            "empty square. Return one valid arrangement as an array of n "
            "strings, or a list of distinct valid arrangements. An empty array "
            "is correct only when no solution exists at all."
        ),
        "function_name": "solveNQueens",
        "param_spec": [{"name": "n", "type": "int"}],
        "return_spec": "string[][]",
        "expected_time_complexity": "O(n!)",
        "expected_space_complexity": "O(n)",
        "checker": "n_queens",
        "test_cases": [
            {
                "input": "[4]",
                "expected_output": '[[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]]',
                "explanation": "n = 4 has exactly two solutions.",
                "is_sample": True,
            },
            {"input": "[1]", "expected_output": '[["Q"]]', "is_sample": True},
            {"input": "[2]", "expected_output": "[]", "explanation": "n = 2 has no solution.", "is_sample": True},
            {"input": "[8]", "expected_output": "[]", "explanation": "The expected output only shows a sample board; any valid arrangement is accepted.", "is_hidden": True},
        ],
    },
    # -------------------------------------------------------------- two pointer
    {
        "title": "Container With Most Water",
        "slug": "container-with-most-water",
        "difficulty": "Medium",
        "domains": ["Array", "Two Pointer"],
        "tags": ["Two Pointers", "Greedy", "Array"],
        "description": (
            "Given the heights of vertical lines, return the largest amount of water "
            "two lines can hold."
        ),
        "function_name": "maxArea",
        "param_spec": [{"name": "height", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,8,6,2,5,4,8,3,7]]", "expected_output": "49", "is_sample": True},
            {"input": "[[1,1]]", "expected_output": "1", "is_sample": True},
        ],
    },
    # ------------------------------------------------------------------ heap
    {
        "title": "Find Kth Smallest Element",
        "slug": "find-kth-smallest-element",
        "difficulty": "Medium",
        "domains": ["Heap", "Array"],
        "tags": ["Heap", "Sorting", "Quickselect"],
        "description": "Return the k-th smallest element of the array (1-indexed).",
        "function_name": "findKthSmallest",
        "param_spec": [{"name": "arr", "type": "int[]"}, {"name": "k", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n) on average",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[3,2,1,5,6,4], 2]", "expected_output": "2", "is_sample": True},
            {"input": "[[3,2,3,1,2,4,5,5,6], 3]", "expected_output": "3", "is_sample": True},
        ],
    },
    # ------------------------------------------------------------------- trie
    {
        "title": "Implement Trie",
        "slug": "implement-trie",
        "difficulty": "Medium",
        "domains": ["Trie"],
        "tags": ["Trie", "Design"],
        "description": (
            "Implement a prefix tree with <code>insert</code>, <code>search</code> "
            "and <code>startsWith</code>.<br><br>"
            "You receive <code>operations</code>, a flat list of strings read in "
            "pairs: the operation name followed by its word. Perform them in order "
            "and return one string per <code>search</code> and <code>startsWith</code> "
            "call, in that order, as the text <code>\"true\"</code> or "
            "<code>\"false\"</code>."
        ),
        "function_name": "solve",
        "param_spec": [{"name": "operations", "type": "string[]"}],
        "return_spec": "string[]",
        "expected_time_complexity": "O(L) per operation",
        "expected_space_complexity": "O(total characters)",
        "test_cases": [
            {
                "input": '["insert","apple","search","apple","search","app","startsWith","app"]',
                "expected_output": '["true","false","true"]',
                "is_sample": True,
            },
            {
                "input": '["insert","hello","startsWith","hell","startsWith","world"]',
                "expected_output": '["true","false"]',
                "is_hidden": True,
            },
        ],
    },
    # ------------------------------------------------------------ bit manip
    {
        "title": "Count Set Bits",
        "slug": "count-set-bits",
        "difficulty": "Easy",
        "domains": ["Bit Manipulation", "Math"],
        "tags": ["Bit Manipulation"],
        "description": "Return the number of set bits in n using the classic bit tricks.",
        "function_name": "countSetBits",
        "param_spec": [{"name": "n", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(log n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[11]", "expected_output": "3", "is_sample": True},
            {"input": "[128]", "expected_output": "1", "is_sample": True},
            {"input": "[0]", "expected_output": "0", "is_hidden": True},
        ],
    },
    # -------------------------------------------------------------- recursion
    {
        "title": "Reverse an Array",
        "slug": "reverse-an-array",
        "difficulty": "Easy",
        "domains": ["Array", "Recursion", "Two Pointer"],
        "tags": ["Recursion", "Array", "Two Pointers"],
        "description": "Return the array reversed using recursion rather than a loop.",
        "function_name": "reverseArray",
        "param_spec": [{"name": "arr", "type": "int[]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[[1,2,3,4,5]]", "expected_output": "[5,4,3,2,1]", "is_sample": True},
            {"input": "[[1]]", "expected_output": "[1]", "is_sample": True},
            {"input": "[[]]", "expected_output": "[]", "is_hidden": True},
        ],
    },
    {
        "title": "Fibonacci Number",
        "slug": "fibonacci-number",
        "difficulty": "Easy",
        "domains": ["Recursion", "Dynamic Programming", "Math"],
        "tags": ["Math", "Recursion", "Dynamic Programming", "Memoization"],
        "description": "Return the n-th Fibonacci number, with F(0) = 0 and F(1) = 1.",
        "function_name": "fib",
        "param_spec": [{"name": "n", "type": "int"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "test_cases": [
            {"input": "[0]", "expected_output": "0", "is_sample": True},
            {"input": "[1]", "expected_output": "1", "is_sample": True},
            {"input": "[10]", "expected_output": "55", "is_sample": True},
            {"input": "[30]", "expected_output": "832040", "is_hidden": True},
        ],
    },
    # ------------------------------------------------------------------ queue
    {
        "title": "BFS Traversal",
        "slug": "bfs-traversal",
        "difficulty": "Medium",
        "domains": ["Graph", "BFS", "Queue"],
        "tags": ["Breadth-First Search", "Graph"],
        "description": (
            "Breadth-first traversal of a graph given as an adjacency list "
            "<code>adj</code> with n nodes numbered 0..n-1. Return the visit order."
        ),
        "function_name": "bfs",
        "param_spec": [{"name": "n", "type": "int"}, {"name": "adj", "type": "int[][]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n + e)",
        "expected_space_complexity": "O(n + e)",
        "test_cases": [
            {"input": "[5, [[1,2],[0,3],[0],[3],[]]]", "expected_output": "[0,1,2,3]", "is_sample": True},
            {"input": "[1, [[]]]", "expected_output": "[0]", "is_hidden": True},
        ],
    },
    {
        "title": "DFS Traversal",
        "slug": "dfs-traversal",
        "difficulty": "Medium",
        "domains": ["Graph", "DFS", "Recursion"],
        "tags": ["Depth-First Search", "Graph", "Recursion"],
        "description": (
            "Depth-first traversal of a graph given as an adjacency list. Return the "
            "visit order starting from node 0."
        ),
        "function_name": "dfs",
        "param_spec": [{"name": "n", "type": "int"}, {"name": "adj", "type": "int[][]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n + e)",
        "expected_space_complexity": "O(n + e)",
        "test_cases": [
            {"input": "[5, [[1,2],[0,3],[0],[1],[]]]", "expected_output": "[0,1,2,3]", "is_sample": True},
            {"input": "[1, [[]]]", "expected_output": "[0]", "is_hidden": True},
        ],
    },
    # ------------------------------------------------------------- two sum v2
    {
        "title": "3Sum",
        "slug": "3sum",
        "difficulty": "Medium",
        "domains": ["Array", "Two Pointer", "Sorting"],
        "tags": ["Array", "Two Pointers", "Sorting"],
        "description": (
            "Return every unique triple in the array that adds up to zero. The list "
            "of triples must itself be sorted and contain no duplicates."
        ),
        "function_name": "threeSum",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int[][]",
        "expected_time_complexity": "O(n^2)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[-1,0,1,2,-1,-4]]", "expected_output": "[[-1,-1,2],[-1,0,1]]", "is_sample": True},
            {"input": "[[0,1,1]]", "expected_output": "[]", "is_sample": True},
            {"input": "[[0,0,0]]", "expected_output": "[[0,0,0]]", "is_hidden": True},
        ],
    },
    {
        "title": "Rotate Array",
        "slug": "rotate-array",
        "difficulty": "Medium",
        "domains": ["Array", "Two Pointer"],
        "tags": ["Array", "Two Pointers", "Math"],
        "description": "Rotate the array to the right by k steps and return it.",
        "function_name": "rotate",
        "param_spec": [{"name": "nums", "type": "int[]"}, {"name": "k", "type": "int"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,2,3,4,5,6,7], 3]", "expected_output": "[5,6,7,1,2,3,4]", "is_sample": True},
            {"input": "[[-1,-100,3,99], 2]", "expected_output": "[3,99,-1,-100]", "is_sample": True},
            {"input": "[[1,2], 3]", "expected_output": "[2,1]", "is_hidden": True},
        ],
    },
    {
        "title": "Remove Duplicates from Sorted Array",
        "slug": "remove-duplicates-from-sorted-array",
        "difficulty": "Easy",
        "domains": ["Array", "Two Pointer"],
        "tags": ["Array", "Two Pointers"],
        "description": (
            "Remove the duplicates from a sorted array in place and return the new "
            "length. The harness only reads the first k elements."
        ),
        "function_name": "removeDuplicates",
        "param_spec": [{"name": "nums", "type": "int[]"}],
        "return_spec": "int",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": "[[1,1,2,2,3,3,4]]", "expected_output": "5", "is_sample": True},
            {"input": "[[0,0,1,1,1,2,2,3]]", "expected_output": "5", "is_sample": True},
        ],
    },
    {
        "title": "Matrix Spiral Traversal",
        "slug": "matrix-spiral-traversal",
        "difficulty": "Medium",
        "domains": ["Matrix", "Recursion"],
        "tags": ["Matrix", "Simulation", "Recursion"],
        "description": "Return the elements of an m x n matrix in clockwise spiral order.",
        "function_name": "spiralOrder",
        "param_spec": [{"name": "matrix", "type": "int[][]"}],
        "return_spec": "int[]",
        "expected_time_complexity": "O(m * n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {
                "input": "[[[1,2,3],[4,5,6],[7,8,9]]]",
                "expected_output": "[1,2,3,6,9,8,7,4,5]",
                "is_sample": True,
            },
            {"input": "[[[1,1,1],[1,1,1]]]", "expected_output": "[1,1,1,1,1,1]", "is_hidden": True},
        ],
    },
    {
        "title": "Set Matrix Zeroes",
        "slug": "set-matrix-zeroes",
        "difficulty": "Medium",
        "domains": ["Matrix", "Array"],
        "tags": ["Array", "Matrix", "Hash Table"],
        "description": (
            "If a cell of the matrix is 0, set its entire row and column to 0. Do "
            "it in place."
        ),
        "function_name": "setZeroes",
        "param_spec": [{"name": "matrix", "type": "int[][]"}],
        "return_spec": "int[][]",
        "expected_time_complexity": "O(m * n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {
                "input": "[[[1,1,1],[1,0,1],[1,1,1]]]",
                "expected_output": "[[1,0,1],[0,0,0],[1,0,1]]",
                "is_sample": True,
            },
            {
                "input": "[[[0,1,2,0],[3,4,5,2],[1,3,1,5]]]",
                "expected_output": "[[0,0,0,0],[0,4,5,0],[0,3,1,0]]",
                "is_hidden": True,
            },
        ],
    },
    {
        "title": "Search a 2D Matrix",
        "slug": "search-a-2d-matrix",
        "difficulty": "Medium",
        "domains": ["Matrix", "Binary Search"],
        "tags": ["Binary Search", "Matrix"],
        "description": (
            "Every row is sorted and the first value of a row is greater than the "
            "last value of the previous row. Return true if target is present."
        ),
        "function_name": "searchMatrix",
        "param_spec": [
            {"name": "matrix", "type": "int[][]"},
            {"name": "target", "type": "int"},
        ],
        "return_spec": "bool",
        "expected_time_complexity": "O(log(m * n))",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {
                "input": "[[[1,3,5,7],[10,11,16,20],[23,30,34,60]], 3]",
                "expected_output": "true",
                "is_sample": True,
            },
            {
                "input": "[[[1,3,5,7],[10,11,16,20],[23,30,34,60]], 13]",
                "expected_output": "false",
                "is_sample": True,
            },
        ],
    },
    {
        "title": "Valid Anagram",
        "slug": "valid-anagram",
        "difficulty": "Easy",
        "domains": ["String", "Hashing"],
        "tags": ["Hash Table", "String", "Sorting"],
        "description": "Return true when s and t are anagrams of each other.",
        "function_name": "isAnagram",
        "param_spec": [{"name": "s", "type": "string"}, {"name": "t", "type": "string"}],
        "return_spec": "bool",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "test_cases": [
            {"input": '["anagram","nagaram"]', "expected_output": "true", "is_sample": True},
            {"input": '["rat","car"]', "expected_output": "false", "is_sample": True},
        ],
    },
    {
        "title": "Group Anagrams",
        "slug": "group-anagrams",
        "difficulty": "Medium",
        "domains": ["Array", "Hashing", "String"],
        "tags": ["Hash Table", "String", "Sorting"],
        "description": (
            "Group the strings so that each group contains anagrams. The order of "
            "the groups, and of the words inside a group, does not matter."
        ),
        "function_name": "groupAnagrams",
        "param_spec": [{"name": "strs", "type": "string[]"}],
        "return_spec": "string[][]",
        "expected_time_complexity": "O(n * k log k)",
        "expected_space_complexity": "O(n * k)",
        "test_cases": [
            {
                "input": '[["eat","tea","tan","ate","nat","bat"]]',
                "expected_output": '[["eat","tea","ate"],["tan","nat"],["bat"]]',
                "is_sample": True,
                "comparison": "unordered",
            },
            {
                "input": '[[""]]',
                "expected_output": '[[""]]',
                "is_sample": True,
                "comparison": "unordered",
            },
            {
                "input": '[["a"]]',
                "expected_output": '[["a"]]',
                "is_hidden": True,
                "comparison": "unordered",
            },
        ],
    },
]
