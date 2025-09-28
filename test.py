def test_string_split():
    # 测试字符串
    test_str = "a.b.c.d.e"

    # 方法1：使用 rsplit() 从右侧分割一次
    parts = test_str.rsplit('.', 1)
    if len(parts) == 2:
        left_part = parts[0]  # "a.b.c.d"
        right_part = parts[1] # "e"
        print(f"方法1 - 左部分: '{left_part}', 右部分: '{right_part}'")

    # 方法2：使用 rfind() 找到最后一个点的位置
    last_dot_index = test_str.rfind('.')
    if last_dot_index != -1:
        left_part = test_str[:last_dot_index]      # "a.b.c.d"
        right_part = test_str[last_dot_index+1:]   # "e"
        print(f"方法2 - 左部分: '{left_part}', 右部分: '{right_part}'")

    # 验证结果
    assert left_part == "a.b.c.d", f"左部分应该是 'a.b.c.d'，实际得到 '{left_part}'"
    assert right_part == "e", f"右部分应该是 'e'，实际得到 '{right_part}'"

    print("测试通过！")

# 运行测试
test_string_split()