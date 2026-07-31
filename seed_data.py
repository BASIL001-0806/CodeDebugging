from models import init_db, User, Question, TestCase
from config import DATABASE_PATH, ADMIN_NAME, ADMIN_YEAR, ADMIN_DEPT

def seed():
    print(f"Database: {DATABASE_PATH}")
    init_db()

    try:
        User.find_or_create(ADMIN_NAME, ADMIN_YEAR, ADMIN_DEPT, is_admin=1)
        print(f"Admin ready: {ADMIN_NAME} / {ADMIN_YEAR} / {ADMIN_DEPT}")
    except Exception as e:
        print(f"Admin setup issue: {e}")

    try:
        User.find_or_create('Alice', '2nd', 'CSE')
        print("Participant 'Alice' ready")
    except Exception:
        print("Participant 'Alice' already exists")

    try:
        User.find_or_create('Bob', '1st', 'ECE')
        print("Participant 'Bob' ready")
    except Exception:
        print("Participant 'Bob' already exists")

    questions = [
        {
            'title': 'Two Sum',
            'difficulty': 'Easy',
            'description': 'Given an array of integers nums and an integer target, return indices of the two numbers that add up to target. You may assume that each input has exactly one solution, and you may not use the same element twice.',
            'input_format': 'First line contains integer N (size of array). Second line contains N space-separated integers. Third line contains the target integer.',
            'output_format': 'Print two space-separated integers representing the indices of the two numbers (0-indexed).',
            'constraints': '2 ≤ N ≤ 10^4\n-10^9 ≤ nums[i] ≤ 10^9\n-10^9 ≤ target ≤ 10^9',
            'sample_input': '4\n2 7 11 15\n9',
            'sample_output': '0 1',
            'explanation': 'Because nums[0] + nums[1] == 9, we return [0, 1].',
            'notes': 'The answer is guaranteed to be unique.',
            'order_num': 1,
            'test_cases': [
                ('3\n3 2 4\n6', '1 2'),
                ('2\n3 3\n6', '0 1'),
                ('5\n1 2 3 4 5\n9', '3 4'),
                ('4\n-1 -2 -3 -4\n-3', '0 1'),
                ('6\n0 4 3 0\n0', '0 3'),
                ('3\n100 200 300\n500', '1 2'),
            ]
        },
        {
            'title': 'Reverse String',
            'difficulty': 'Easy',
            'description': 'Write a function that reverses a string. The input string is given as an array of characters. Do not allocate extra space for another array; you must do this by modifying the input array in-place with O(1) extra memory.',
            'input_format': 'A single line containing a string.',
            'output_format': 'Print the reversed string.',
            'constraints': '1 ≤ len(s) ≤ 10^5\ns consists of printable ASCII characters.',
            'sample_input': 'hello',
            'sample_output': 'olleh',
            'explanation': 'Reverse of "hello" is "olleh".',
            'notes': '',
            'order_num': 2,
            'test_cases': [
                ('world', 'dlrow'),
                ('python', 'nohtyp'),
                ('a', 'a'),
                ('racecar', 'racecar'),
                ('12345', '54321'),
                ('!@#$%', '%$#@!'),
            ]
        },
        {
            'title': 'Fibonacci Number',
            'difficulty': 'Medium',
            'description': 'The Fibonacci numbers, commonly denoted F(n), form a sequence called the Fibonacci sequence such that each number is the sum of the two preceding ones, starting from 0 and 1. That is: F(0) = 0, F(1) = 1, and F(n) = F(n-1) + F(n-2) for n > 1. Given n, calculate F(n).',
            'input_format': 'A single integer n.',
            'output_format': 'Print the nth Fibonacci number.',
            'constraints': '0 ≤ n ≤ 30',
            'sample_input': '10',
            'sample_output': '55',
            'explanation': 'F(10) = 55',
            'notes': 'Try to solve it with recursion first, then optimize.',
            'order_num': 3,
            'test_cases': [
                ('0', '0'),
                ('1', '1'),
                ('5', '5'),
                ('15', '610'),
                ('20', '6765'),
                ('25', '75025'),
            ]
        },
        {
            'title': 'Palindrome Check',
            'difficulty': 'Easy',
            'description': 'Given a string s, determine if it is a palindrome, considering only alphanumeric characters and ignoring cases.',
            'input_format': 'A single line containing a string.',
            'output_format': 'Print "true" if the string is a palindrome, otherwise print "false".',
            'constraints': '1 ≤ len(s) ≤ 10^5',
            'sample_input': 'A man a plan a canal Panama',
            'sample_output': 'true',
            'explanation': 'After removing non-alphanumeric characters and converting to lowercase, "amanaplanacanalpanama" is a palindrome.',
            'notes': '',
            'order_num': 4,
            'test_cases': [
                ('race a car', 'false'),
                ('', 'true'),
                ('12321', 'true'),
                ('hello', 'false'),
                ('Was it a car or a cat I saw', 'true'),
                ('No lemon no melon', 'true'),
            ]
        },
        {
            'title': 'Maximum Subarray',
            'difficulty': 'Medium',
            'description': 'Given an integer array nums, find the contiguous subarray (containing at least one number) which has the largest sum and return its sum.',
            'input_format': 'First line contains integer N. Second line contains N space-separated integers.',
            'output_format': 'Print the maximum subarray sum.',
            'constraints': '1 ≤ N ≤ 10^5\n-10^4 ≤ nums[i] ≤ 10^4',
            'sample_input': '9\n-2 1 -3 4 -1 2 1 -5 4',
            'sample_output': '6',
            'explanation': 'The subarray [4,-1,2,1] has the largest sum = 6.',
            'notes': 'Try to implement Kadane\'s algorithm for O(N) solution.',
            'order_num': 5,
            'test_cases': [
                ('1\n1', '1'),
                ('5\n-1 -2 -3 -4 -5', '-1'),
                ('4\n5 4 -1 7', '15'),
                ('1\n-10000', '-10000'),
                ('6\n2 -1 2 3 4 -5', '10'),
                ('5\n1 2 3 4 5', '15'),
            ]
        },
        {
            'title': 'Valid Parentheses',
            'difficulty': 'Easy',
            'description': 'Given a string s containing just the characters "(", ")", "{", "}", "[" and "]", determine if the input string is valid. An input string is valid if: (1) Open brackets must be closed by the same type of brackets. (2) Open brackets must be closed in the correct order.',
            'input_format': 'A single line containing a string of brackets.',
            'output_format': 'Print "true" if valid, otherwise "false".',
            'constraints': '1 ≤ len(s) ≤ 10^4\ns consists of brackets only: ()[]{}',
            'sample_input': '()[]{}',
            'sample_output': 'true',
            'explanation': 'All brackets are properly matched and closed in order.',
            'notes': '',
            'order_num': 6,
            'test_cases': [
                ('(]', 'false'),
                ('([)]', 'false'),
                ('{[]}', 'true'),
                ('(', 'false'),
                ('', 'true'),
                ('((()))', 'true'),
            ]
        },
    ]

    existing_titles = {q['title'] for q in Question.get_all()}

    for q_data in questions:
        if q_data['title'] in existing_titles:
            print(f"Skipping existing question: {q_data['title']} (already present)")
            continue
        test_cases = q_data.pop('test_cases')
        qid = Question.create(**q_data)
        print(f"Created question: {q_data['title']} (ID: {qid})")
        for tc_input, tc_output in test_cases:
            TestCase.create(qid, tc_input, tc_output, is_hidden=1)
        print(f"  Added {len(test_cases)} hidden test cases")

    print("\nSeed complete!")
    print("----------------------------")
    print(f"Admin access:   {ADMIN_NAME} / {ADMIN_YEAR} / {ADMIN_DEPT}")
    print("Sample user:    Alice / 2nd / CSE")

if __name__ == '__main__':
    seed()
