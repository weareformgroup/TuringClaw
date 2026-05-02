#!/usr/bin/env python3
"""
TuringClaw 隐私路由测试用例
测试三级隐私路由机制 (S1/S2/S3)

运行方式:
    python test_privacy_router.py
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, "C:/Users/Administrator/TuringClaw/gui")
from privacy_router import PrivacyDetector, Desensitizer, PrivacyRouter

# ─────────────────────────────────────────────
# 测试用例定义
# ─────────────────────────────────────────────

TEST_CASES = [
    # S1 级别 - 正常数据，无敏感信息
    {
        "name": "S1-001: 普通问题",
        "input": "什么是人工智能？请介绍一下。",
        "expected_level": "S1",
        "expected_hits": [],
    },
    {
        "name": "S1-002: 代码问题",
        "input": "如何用 Python 写一个快速排序算法？",
        "expected_level": "S1",
        "expected_hits": [],
    },
    {
        "name": "S1-003: 创意写作",
        "input": "写一篇关于春天的诗歌",
        "expected_level": "S1",
        "expected_hits": [],
    },
    
    # S2 级别 - 敏感数据，需脱敏
    {
        "name": "S2-001: 手机号",
        "input": "我的手机号是 13812345678，请帮我查一下套餐。",
        "expected_level": "S2",
        "expected_hits": ["cn_phone"],
    },
    {
        "name": "S2-002: 身份证号",
        "input": "身份证号 110101199001011234 需要核实。",
        "expected_level": "S2",
        "expected_hits": ["cn_idcard"],
    },
    {
        "name": "S2-003: 银行卡号",
        "input": "银行卡 6222021234567890123 转账记录查询。",
        "expected_level": "S2",
        "expected_hits": ["bank_card"],
    },
    {
        "name": "S2-004: 电子邮箱",
        "input": "我的邮箱是 zhangsan@example.com，请发确认邮件。",
        "expected_level": "S2",
        "expected_hits": ["email"],
    },
    {
        "name": "S2-005: 内网IP",
        "input": "服务器地址 192.168.1.100 无法访问。",
        "expected_level": "S2",
        "expected_hits": ["ipv4_private"],
    },
    {
        "name": "S2-006: 姓名键值对",
        "input": "姓名：张三，请帮我查询订单。",
        "expected_level": "S2",
        "expected_hits": ["cn_name_kv"],
    },
    {
        "name": "S2-007: 多个敏感信息",
        "input": "我叫张三，手机 13912345678，身份证 310101199001011234。",
        "expected_level": "S2",
        "expected_hits": ["cn_phone", "cn_idcard"],
    },
    
    # S3 级别 - 高度敏感，强制本地
    {
        "name": "S3-001: 密码键值对",
        "input": "我的密码是 MyP@ssw0rd123，请帮我记住。",
        "expected_level": "S3",
        "expected_hits": ["password_kv"],
    },
    {
        "name": "S3-002: API Key",
        "input": "api_key=sk-1234567890abcdef 请帮我验证这个key。",
        "expected_level": "S3",
        "expected_hits": ["api_key_kv"],
    },
    {
        "name": "S3-003: 私钥",
        "input": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...",
        "expected_level": "S3",
        "expected_hits": ["private_key"],
    },
    {
        "name": "S3-004: 信用卡号",
        "input": "信用卡 4532123456789012 需要扣款。",
        "expected_level": "S3",
        "expected_hits": ["credit_card"],
    },
    {
        "name": "S3-005: 医疗敏感词",
        "input": "病人的病历显示HIV阳性，需要特殊处理。",
        "expected_level": "S3",
        "expected_hits": ["medical_kw"],
    },
    {
        "name": "S3-006: 密码中文",
        "input": "密码：Admin@123 请帮我修改。",
        "expected_level": "S3",
        "expected_hits": ["password_kv"],
    },
]


def run_tests():
    """运行所有测试用例"""
    detector = PrivacyDetector()
    desensitizer = Desensitizer()
    router = PrivacyRouter()
    
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("TuringClaw 隐私路由测试报告")
    print("=" * 60)
    print()
    
    for tc in TEST_CASES:
        name = tc["name"]
        input_text = tc["input"]
        expected_level = tc["expected_level"]
        expected_hits = tc["expected_hits"]
        
        # 执行检测
        result = detector.detect(input_text)
        route = router.route(input_text)
        
        # 判断是否通过
        level_ok = result.level == expected_level
        hits_ok = all(any(h in hit for hit in result.hits) for h in expected_hits)
        passed_test = level_ok and hits_ok
        
        status = "✅ PASS" if passed_test else "❌ FAIL"
        if passed_test:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | {name}")
        print(f"       输入: {input_text[:40]}{'...' if len(input_text) > 40 else ''}")
        print(f"       预期: {expected_level}, 实际: {result.level}")
        if result.hits:
            print(f"       命中: {result.hits}")
        if result.level == "S2":
            desen = desensitizer.desensitize(input_text)
            print(f"       脱敏: {desen.sanitized[:50]}{'...' if len(desen.sanitized) > 50 else ''}")
        print()
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
