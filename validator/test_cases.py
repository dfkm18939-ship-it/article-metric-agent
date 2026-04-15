# validator/test_cases.py
# 职责：自动化测试用例（12个场景）
# 无 LLM 调用，纯数据定义

"""
测试用例定义：
每个用例包含：
  - id: 用例编号
  - name: 用例名称
  - input: 用户查询字符串
  - expected_metric_id: 期望匹配的指标 ID
  - expected_time: 期望解析的时间表达式
  - expected_dimension: 期望解析的维度
  - expect_clarify: 是否期望触发澄清
  - description: 用例说明
"""

TEST_CASES = [
    {
        "id": 1,
        "name": "明确查询今年签发量",
        "input": "今年签发了多少稿件",
        "expected_metric_id": "article_signed_count",
        "expected_time": "今年",
        "expected_dimension": None,
        "expect_clarify": False,
        "description": "最标准的查询，意图明确，无歧义",
    },
    {
        "id": 2,
        "name": "模糊查询有多少稿件",
        "input": "有多少稿件",
        "expected_metric_id": "article_signed_count",
        "expected_time": "今年",
        "expected_dimension": None,
        "expect_clarify": True,
        "description": "高歧义问题，应触发澄清",
    },
    {
        "id": 3,
        "name": "带部门维度查询签发量",
        "input": "各部门签发量是多少",
        "expected_metric_id": "article_signed_count",
        "expected_time": "今年",
        "expected_dimension": "部门",
        "expect_clarify": False,
        "description": "含维度，应按部门分组",
    },
    {
        "id": 4,
        "name": "时间-上周",
        "input": "上周签发了多少篇",
        "expected_metric_id": "article_signed_count",
        "expected_time": "上周",
        "expected_dimension": None,
        "expect_clarify": False,
        "description": "上周时间范围查询",
    },
    {
        "id": 5,
        "name": "时间-上月",
        "input": "上个月签发量",
        "expected_metric_id": "article_signed_count",
        "expected_time": "上月",
        "expected_dimension": None,
        "expect_clarify": False,
        "description": "上月时间范围查询",
    },
    {
        "id": 6,
        "name": "时间-去年",
        "input": "去年一共签发了多少稿件",
        "expected_metric_id": "article_signed_count",
        "expected_time": "去年",
        "expected_dimension": None,
        "expect_clarify": False,
        "description": "去年全年查询",
    },
    {
        "id": 7,
        "name": "歧义触发-生产了多少",
        "input": "生产了多少",
        "expected_metric_id": "article_signed_count",
        "expected_time": "今年",
        "expected_dimension": None,
        "expect_clarify": True,
        "description": "高歧义，生产量可能是签发量或成品量",
    },
    {
        "id": 8,
        "name": "歧义触发-发布了多少",
        "input": "发布了多少篇文章",
        "expected_metric_id": "article_published_count",
        "expected_time": "今年",
        "expected_dimension": None,
        "expect_clarify": True,
        "description": "发布量跳转，可能是 published 而非 signed",
    },
    {
        "id": 9,
        "name": "歧义触发-写了多少",
        "input": "编辑写了多少篇",
        "expected_metric_id": "article_finished_count",
        "expected_time": "今年",
        "expected_dimension": None,
        "expect_clarify": True,
        "description": "写了多少 → 成品量，需要澄清",
    },
    {
        "id": 10,
        "name": "追问场景-和去年比呢",
        "input": "和去年比呢",
        "expected_metric_id": "article_signed_count",
        "expected_time": "去年",
        "expected_dimension": None,
        "expect_clarify": False,
        "description": "追问场景，需上下文记忆支持，时间切换为去年",
    },
    {
        "id": 11,
        "name": "异常场景-数据为空",
        "input": "明天的签发量",
        "expected_metric_id": "article_signed_count",
        "expected_time": "今天",
        "expected_dimension": None,
        "expect_clarify": False,
        "description": "未来时间查询，数据应为空，触发异常检测",
    },
    {
        "id": 12,
        "name": "权限场景-普通编辑查自己",
        "input": "我这个月签发了多少",
        "expected_metric_id": "article_signed_count",
        "expected_time": "本月",
        "expected_dimension": "作者",
        "expect_clarify": False,
        "description": "普通编辑角色只能查询自己，SQL 应加 author_name 过滤",
    },
]


def run_local_tests() -> None:
    """本地快速验证 SQLGenerator 时间解析逻辑（无 LLM 调用）"""
    from claude.sql_generator import SQLGenerator

    gen = SQLGenerator.__new__(SQLGenerator)  # 跳过 __init__ 中的 LLM 初始化

    time_cases = [
        ("今天", lambda s, e: s == e),
        ("昨天", lambda s, e: s == e and s != str(__import__("datetime").date.today())),
        ("本月", lambda s, e: s.endswith("-01")),
        ("上月", lambda s, e: s.endswith("-01")),
        ("今年", lambda s, e: s.endswith("-01-01")),
        ("去年", lambda s, e: s.endswith("-01-01") and e.endswith("-12-31")),
    ]

    print("=== 时间解析测试 ===")
    all_pass = True
    for expr, check in time_cases:
        result = SQLGenerator._parse_time(expr)
        passed = check(result["start"], result["end"])
        status = "✅" if passed else "❌"
        print(f"{status} {expr}: {result}")
        if not passed:
            all_pass = False

    print(f"\n{'所有测试通过' if all_pass else '存在失败用例'}")
    return all_pass


if __name__ == "__main__":
    run_local_tests()
    print("\n=== 测试用例列表 ===")
    for tc in TEST_CASES:
        flag = "🔄" if tc["expect_clarify"] else "✅"
        print(f"[{tc['id']:02d}] {flag} {tc['name']}: {tc['input']!r}")
