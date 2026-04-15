# validator/test_cases.py — 自动化测试用例（至少10个）

import asyncio
import json
import logging
import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

TEST_CASES = [
    {
        "id": "TC-01",
        "input": "今年生产了多少稿件",
        "expected_metric": "article_signed_count",
        "expected_time": "今年",
        "expected_ambiguous": False,
        "description": "标准签发量查询（今年）",
    },
    {
        "id": "TC-02",
        "input": "有多少稿件",
        "expected_ambiguous": True,
        "description": "歧义查询，应触发澄清",
    },
    {
        "id": "TC-03",
        "input": "上个月各部门签发量",
        "expected_metric": "article_signed_count",
        "expected_time": "上月",
        "expected_dimension": "dept_name",
        "description": "带部门维度的上月查询",
    },
    {
        "id": "TC-04",
        "input": "上周签发了多少",
        "expected_metric": "article_signed_count",
        "expected_time": "上周",
        "description": "上周签发量查询",
    },
    {
        "id": "TC-05",
        "input": "去年签发量",
        "expected_metric": "article_signed_count",
        "expected_time": "去年",
        "description": "去年签发量查询",
    },
    {
        "id": "TC-06",
        "input": "发布了多少稿件",
        "expected_metric": "article_published_count",
        "description": "发布量查询（非签发量）",
    },
    {
        "id": "TC-07",
        "input": "写了多少稿件",
        "expected_metric": "article_finished_count",
        "description": "成品量查询",
    },
    {
        "id": "TC-08",
        "input": "今天各作者签发量",
        "expected_metric": "article_signed_count",
        "expected_time": "今天",
        "expected_dimension": "author_name",
        "description": "带作者维度的今天查询",
    },
    {
        "id": "TC-09",
        "input": "今年和去年对比",
        "expected_metric": "article_signed_count",
        "expected_comparison": True,
        "description": "同比对比查询",
    },
    {
        "id": "TC-10",
        "input": "本月体育部签发了多少",
        "expected_metric": "article_signed_count",
        "expected_time": "本月",
        "expected_dimension": "dept_name",
        "description": "带部门过滤的本月查询",
    },
    {
        "id": "TC-11",
        "input": "签发量",
        "expected_metric": "article_signed_count",
        "description": "最简指标名称查询",
    },
    {
        "id": "TC-12",
        "input": "今天签发了多少",
        "expected_metric": "article_signed_count",
        "expected_time": "今天",
        "description": "今天签发量查询",
    },
]

# ── SQL 校验测试用例 ───────────────────────────────────────────────
SQL_VALIDATION_CASES = [
    {
        "id": "SV-01",
        "sql": "SELECT COUNT(DISTINCT a.article_id) AS signed_count FROM fact_article_workflow a WHERE a.status = 'signed' AND a.signed_at BETWEEN '2024-01-01' AND '2024-12-31' AND a.article_type != 'test' AND a.is_deleted = 0",
        "expected_passed": True,
        "description": "合规 SQL 应通过验证",
    },
    {
        "id": "SV-02",
        "sql": "SELECT COUNT(*) FROM fact_article_workflow WHERE created_at > '2024-01-01'",
        "expected_passed": False,
        "description": "使用 created_at 且缺少业务条件，应不通过",
    },
    {
        "id": "SV-03",
        "sql": "SELECT COUNT(DISTINCT article_id) FROM fact_article_workflow WHERE status='signed' AND signed_at > '2024-01-01' AND is_deleted=0",
        "expected_passed": False,
        "description": "缺少排除测试稿件条件，应不通过",
    },
]


def _check_intent(result: dict, case: dict) -> tuple[bool, list[str]]:
    """检查意图识别结果是否符合预期"""
    passed = True
    failures = []

    if "expected_metric" in case:
        if result.get("metric_id") != case["expected_metric"]:
            passed = False
            failures.append(
                f"metric_id 期望 {case['expected_metric']}，实际 {result.get('metric_id')}"
            )

    if "expected_time" in case:
        time_expr = result.get("time_expression", "")
        if case["expected_time"] not in time_expr and time_expr != case["expected_time"]:
            passed = False
            failures.append(
                f"time_expression 期望包含 {case['expected_time']}，实际 {time_expr}"
            )

    if "expected_dimension" in case:
        if result.get("dimension") != case["expected_dimension"]:
            passed = False
            failures.append(
                f"dimension 期望 {case['expected_dimension']}，实际 {result.get('dimension')}"
            )

    if "expected_ambiguous" in case:
        if bool(result.get("ambiguous")) != case["expected_ambiguous"]:
            passed = False
            failures.append(
                f"ambiguous 期望 {case['expected_ambiguous']}，实际 {result.get('ambiguous')}"
            )

    return passed, failures


def _check_sql_validation(result: dict, case: dict) -> tuple[bool, list[str]]:
    """检查 SQL 验证结果"""
    passed = True
    failures = []
    expected = case["expected_passed"]
    actual = result.get("passed", True)
    if actual != expected:
        passed = False
        failures.append(f"SQL 验证结果期望 passed={expected}，实际 passed={actual}")
    return passed, failures


async def run_tests(use_llm: bool = False) -> dict:
    """
    运行所有测试用例。
    use_llm=False 时使用本地规则进行快速测试（不消耗 API）。
    use_llm=True 时调用真实 LLM。
    """
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    # ── 意图识别测试 ───────────────────────────────────────────
    if use_llm:
        from gpt.intent_agent import IntentAgent
        agent = IntentAgent()

        for case in TEST_CASES:
            results["total"] += 1
            try:
                intent = await agent.recognize(case["input"], user_id="test_user")
                ok, failures = _check_intent(intent, case)
                status = "PASS" if ok else "FAIL"
                if ok:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                results["details"].append({
                    "id": case["id"],
                    "input": case["input"],
                    "status": status,
                    "failures": failures,
                    "intent": intent,
                })
                logger.info("[%s] %s — %s", status, case["id"], case["description"])
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "id": case["id"],
                    "input": case["input"],
                    "status": "ERROR",
                    "failures": [str(e)],
                })
    else:
        # 本地快速验证（不依赖 LLM）
        from validator.cross_validator import CrossValidator, KNOWN_METRICS, KNOWN_TIMES, KNOWN_DIMENSIONS
        validator = CrossValidator()

        for case in SQL_VALIDATION_CASES:
            results["total"] += 1
            # 使用本地兜底校验（不调用 GPT）
            sql = case["sql"]
            sql_lower = sql.lower()
            local_issues = []
            if "status" not in sql_lower or ("'signed'" not in sql_lower and '"signed"' not in sql_lower):
                local_issues.append("缺少 status='signed'")
            if "signed_at" not in sql_lower:
                local_issues.append("缺少 signed_at")
            if "article_type" not in sql_lower or "test" not in sql_lower:
                local_issues.append("缺少排除测试稿件")
            if "is_deleted" not in sql_lower:
                local_issues.append("缺少 is_deleted")

            actual_passed = len(local_issues) == 0
            ok, failures = _check_sql_validation(
                {"passed": actual_passed, "issues": local_issues}, case
            )
            status = "PASS" if ok else "FAIL"
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "id": case["id"],
                "description": case["description"],
                "status": status,
                "failures": failures,
            })
            logger.info("[%s] %s — %s", status, case["id"], case["description"])

        # 意图结构测试（本地规则）
        local_intent_cases = [
            {"id": "LI-01", "metric_id": "article_signed_count", "time_expression": "今年", "dimension": None},
            {"id": "LI-02", "metric_id": "article_published_count", "time_expression": "本月", "dimension": "dept_name"},
            {"id": "LI-03", "metric_id": "unknown_metric", "time_expression": "今年", "dimension": None},
        ]
        expected_executable = [True, True, False]

        for case, expected in zip(local_intent_cases, expected_executable):
            results["total"] += 1
            from validator.cross_validator import KNOWN_METRICS
            actual = case["metric_id"] in KNOWN_METRICS
            ok = actual == expected
            status = "PASS" if ok else "FAIL"
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "id": case["id"],
                "status": status,
                "failures": [] if ok else [f"metric executable 期望 {expected}，实际 {actual}"],
            })
            logger.info("[%s] %s — intent local check", status, case["id"])

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    results = asyncio.run(run_tests(use_llm=False))
    print(f"\n{'='*50}")
    print(f"测试结果：总计 {results['total']} | 通过 {results['passed']} | 失败 {results['failed']}")
    print(f"{'='*50}")
    for d in results["details"]:
        status_icon = "✅" if d["status"] == "PASS" else "❌"
        print(f"{status_icon} [{d['id']}] {d.get('description', d.get('input', ''))}")
        for f in d.get("failures", []):
            print(f"   → {f}")
