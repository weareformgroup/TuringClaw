"""
market_validation.py — 市场验证追踪器

GSM V10 螺旋B（外部校准线）组件
追踪 Agent 对任务的预测（时间/风险/阻塞）与实际结果的偏差，
形成"预测校准曲线"，发现系统性偏差。

数据文件：~/.TuringClaw/cognitive/calibration/market_validation.json

流程：
    1. 任务开始前：record_prediction() 记录预测
    2. 任务完成后：record_actual() 填入实际结果
    3. 自动计算：预测误差、blocker 命中率
    4. 查询：get_calibration_curve() 查看校准曲线和系统性偏差
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_store() -> dict[str, Any]:
    return {
        "validations": [],
        "calibration_curve": {
            "total_predictions": 0,
            "accurate_predictions": 0,
            "accuracy_rate": 0.0,
            "systematic_bias": None,
            "domain_curves": {},
        },
        "meta": {
            "created": _utc_now_iso(),
            "last_updated": _utc_now_iso(),
            "version": "1.0",
        },
    }


class MarketValidationTracker:
    """市场验证追踪器。

    记录 Agent 对任务的预测，在任务完成后对比实际结果，
    计算预测误差和系统性偏差。

    核心概念：
        - prediction_error: 预测与实际的偏差
        - blocker_recall: 预测的阻塞项有多少真的出现了
        - systematic_bias: Agent 是系统性低估还是高估
        - calibration_curve: 按领域分的校准曲线

    目标：预测误差单调下降，systematic_bias 收敛到 0。
    """

    ACCURACY_THRESHOLD: float = 0.2  # 误差 < 20% 算准确

    def __init__(self, cognitive_dir: str | Path | None = None) -> None:
        base = Path(cognitive_dir) if cognitive_dir else Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir: Path = base / "calibration"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path: Path = self.data_dir / "market_validation.json"

    def load(self) -> dict[str, Any]:
        """加载验证数据；文件不存在或损坏时返回空骨架。"""
        if not self.file_path.exists():
            return _default_store()
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "validations" not in data:
                data = _default_store() | data
            return data
        except (json.JSONDecodeError, OSError):
            return _default_store()

    def save(self, data: dict[str, Any]) -> None:
        """持久化验证数据。"""
        data.setdefault("meta", {})["last_updated"] = _utc_now_iso()
        tmp = self.file_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    def record_prediction(
        self,
        task: str,
        time_estimate_hours: list[float],
        risk_level: str = "medium",
        expected_blockers: list[str] | None = None,
        confidence: float = 0.5,
        task_domain: str = "general",
    ) -> dict[str, Any]:
        """任务开始前记录预测。

        Args:
            task: 任务描述。
            time_estimate_hours: 预估时间范围 [下限, 上限]。
            risk_level: 风险等级 low/medium/high。
            expected_blockers: 预期可能遇到的阻塞项列表。
            confidence: 预测置信度 [0, 1]。
            task_domain: 任务领域标签。

        Returns:
            新创建的验证条目（actual 为 None）。
        """
        data = self.load()

        validation = {
            "id": self._next_id(data["validations"]),
            "task": task,
            "task_domain": task_domain,
            "prediction": {
                "time_estimate_hours": time_estimate_hours,
                "risk_level": risk_level,
                "expected_blockers": expected_blockers or [],
                "confidence": confidence,
                "timestamp": _utc_now_iso(),
            },
            "actual": None,
            "prediction_error": None,
            "learning": None,
        }

        data["validations"].append(validation)
        data["calibration_curve"]["total_predictions"] += 1
        self.save(data)
        return validation

    def record_actual(
        self,
        validation_id: str,
        time_hours: float,
        blockers_encountered: list[str] | None = None,
        result: str = "success",
        learning: str | None = None,
    ) -> dict[str, Any] | None:
        """任务完成后填入实际结果，自动计算预测误差。

        Args:
            validation_id: 验证条目 ID。
            time_hours: 实际耗时（小时）。
            blockers_encountered: 实际遇到的阻塞项列表。
            result: 结果 success/partial/failure。
            learning: 从误差中学到的经验。

        Returns:
            更新后的验证条目，找不到返回 None。
        """
        data = self.load()
        target = None
        for v in data["validations"]:
            if v["id"] == validation_id:
                target = v
                break
        if target is None:
            return None

        blockers = blockers_encountered or []
        prediction = target["prediction"]
        pred_time_range = prediction["time_estimate_hours"]
        pred_mid = (pred_time_range[0] + pred_time_range[1]) / 2
        expected_blockers = set(prediction["expected_blockers"])
        actual_blockers = set(blockers)

        # 时间误差（相对中位数预测）
        if pred_mid > 0:
            time_error = abs(time_hours - pred_mid) / pred_mid
        else:
            time_error = 0.0

        # signed error: 正=低估, 负=高估
        signed_error = (time_hours - pred_mid) / pred_mid if pred_mid > 0 else 0.0

        # Blocker 命中率
        if expected_blockers:
            blocker_recall = len(expected_blockers & actual_blockers) / len(expected_blockers)
        else:
            blocker_recall = 1.0 if not actual_blockers else 0.0

        unexpected_blockers = list(actual_blockers - expected_blockers)

        target["actual"] = {
            "time_hours": time_hours,
            "blockers_encountered": blockers,
            "result": result,
            "timestamp": _utc_now_iso(),
        }

        target["prediction_error"] = {
            "time_error": round(time_error, 4),
            "signed_error": round(signed_error, 4),
            "blocker_recall": round(blocker_recall, 4),
            "unexpected_blockers": unexpected_blockers,
            "unexpected_count": len(unexpected_blockers),
        }

        target["learning"] = learning or self._auto_learning(target)

        self._update_curve(data, target)
        self.save(data)
        return target

    def _update_curve(self, data: dict[str, Any], validation: dict[str, Any]) -> None:
        """更新校准曲线。"""
        curve = data["calibration_curve"]
        domain = validation.get("task_domain", "general")
        error = validation["prediction_error"]
        time_error = error["time_error"]
        signed_error = error["signed_error"]

        # 全局统计
        if time_error < self.ACCURACY_THRESHOLD:
            curve["accurate_predictions"] += 1
        total = curve["total_predictions"]
        curve["accuracy_rate"] = round(curve["accurate_predictions"] / total, 4) if total > 0 else 0.0

        # 全局系统性偏差（最近 10 个的均值）
        completed = [v for v in data["validations"] if v["prediction_error"] is not None]
        recent = completed[-10:]
        if recent:
            avg_signed = sum(v["prediction_error"]["signed_error"] for v in recent) / len(recent)
            curve["systematic_bias"] = round(avg_signed, 4)

        # 按领域统计
        domain_curves = curve.setdefault("domain_curves", {})
        if domain not in domain_curves:
            domain_curves[domain] = {
                "predictions": 0,
                "accurate": 0,
                "bias": 0.0,
                "signed_errors": [],
            }

        dc = domain_curves[domain]
        dc["predictions"] += 1
        if time_error < self.ACCURACY_THRESHOLD:
            dc["accurate"] += 1
        dc["signed_errors"].append(signed_error)

        recent_domain_errors = dc["signed_errors"][-10:]
        dc["bias"] = round(sum(recent_domain_errors) / len(recent_domain_errors), 4)

    def _auto_learning(self, validation: dict[str, Any]) -> str:
        """根据预测误差自动生成学习总结。"""
        error = validation["prediction_error"]
        parts = []

        if error["time_error"] < 0.2:
            parts.append("时间预测准确")
        elif error["signed_error"] > 0:
            parts.append(f"低估了时间（误差 {error['time_error']:.0%}）")
        else:
            parts.append(f"高估了时间（误差 {error['time_error']:.0%}）")

        if error["blocker_recall"] >= 0.8:
            parts.append("阻塞项预测准确")
        elif error["unexpected_count"] > 0:
            parts.append(f"有 {error['unexpected_count']} 个未预测到的阻塞项")

        return "；".join(parts)

    def _next_id(self, validations: list[dict[str, Any]]) -> str:
        max_num = 0
        for v in validations:
            try:
                num = int(v["id"].replace("mv_", ""))
                max_num = max(max_num, num)
            except (ValueError, KeyError):
                pass
        return f"mv_{max_num + 1:03d}"

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_calibration_curve(self) -> dict[str, Any]:
        """返回当前校准曲线。"""
        return self.load()["calibration_curve"]

    def get_pending_validations(self) -> list[dict[str, Any]]:
        """返回所有尚未填入实际结果的验证。"""
        return [v for v in self.load()["validations"] if v["actual"] is None]

    def get_completed_validations(self) -> list[dict[str, Any]]:
        """返回所有已完成的验证。"""
        return [v for v in self.load()["validations"] if v["actual"] is not None]

    def get_domain_report(self, domain: str | None = None) -> dict[str, Any]:
        """返回按领域分组的校准报告。

        Args:
            domain: 指定领域，None 返回所有领域。

        Returns:
            领域校准报告字典。
        """
        curve = self.load()["calibration_curve"]
        domain_curves = curve.get("domain_curves", {})

        if domain:
            return domain_curves.get(domain, {})

        report = {}
        for dom, dc in domain_curves.items():
            predictions = dc.get("predictions", 0)
            accurate = dc.get("accurate", 0)
            bias = dc.get("bias", 0.0)

            if bias > 0.2:
                interpretation = "系统性低估时间"
            elif bias < -0.2:
                interpretation = "系统性高估时间"
            else:
                interpretation = "校准良好"

            report[dom] = {
                "accuracy": round(accurate / predictions, 4) if predictions > 0 else 0.0,
                "bias": round(bias, 4),
                "predictions": predictions,
                "interpretation": interpretation,
            }

        return report

    @staticmethod
    def _self_test() -> None:
        """简单自测。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tracker = MarketValidationTracker(cognitive_dir=td)

            # 记录预测
            v1 = tracker.record_prediction(
                task="M4 PyInstaller 打包",
                time_estimate_hours=[4, 6],
                risk_level="medium",
                expected_blockers=["Anaconda冲突", "路径问题"],
                task_domain="packaging",
            )
            assert v1["actual"] is None

            # 填入实际结果（略微超时）
            result = tracker.record_actual(
                validation_id=v1["id"],
                time_hours=6.5,
                blockers_encountered=["Anaconda冲突", "未预期的依赖缺失"],
                result="success",
            )
            assert result is not None
            assert result["prediction_error"] is not None
            assert result["prediction_error"]["blocker_recall"] == 0.5

            # 第二个预测——准确
            v2 = tracker.record_prediction(
                task="配置文件写入",
                time_estimate_hours=[1, 2],
                expected_blockers=["编码问题"],
                task_domain="config",
            )
            tracker.record_actual(
                validation_id=v2["id"],
                time_hours=1.5,
                blockers_encountered=["编码问题"],
                result="success",
            )

            # 第三个预测——低估
            v3 = tracker.record_prediction(
                task="另一个打包任务",
                time_estimate_hours=[2, 3],
                expected_blockers=[],
                task_domain="packaging",
            )
            tracker.record_actual(
                validation_id=v3["id"],
                time_hours=5.0,
                blockers_encountered=["依赖缺失", "权限问题"],
                result="partial",
            )

            curve = tracker.get_calibration_curve()
            assert curve["total_predictions"] == 3

            report = tracker.get_domain_report()
            assert "packaging" in report
            assert "config" in report

            pkg_report = report["packaging"]
            assert pkg_report["bias"] > 0
            assert "低估" in pkg_report["interpretation"]

            print(f"calibration_curve: {json.dumps(curve, ensure_ascii=False, indent=2)}")
            print(f"domain report: {json.dumps(report, ensure_ascii=False, indent=2)}")
            print("[OK] market_validation self-test passed")


if __name__ == "__main__":
    MarketValidationTracker._self_test()
