"""
数据导出引擎
支持分类结果TIF、统计CSV/Excel、简易报告导出
"""
import io
import gc
import numpy as np
import pandas as pd
from datetime import datetime


def export_prediction_tif(prediction_map, meta, chunk_size=1024):
    """
    将分类结果导出为 GeoTIFF 格式。
    支持分块写入以避免大图OOM问题。

    Args:
        prediction_map: np.ndarray (H, W), 0/1
        meta: dict, 包含地理元数据
        chunk_size: 分块大小，0表示不分块

    Returns:
        bytes: TIF文件二进制内容
    """
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.windows import Window

    h, w = prediction_map.shape
    bounds = meta.get("bounds_utm") or meta.get("bounds_wgs84")

    if bounds:
        transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], w, h)
    else:
        transform = meta.get("transform")

    crs = meta.get("crs_original", meta.get("crs", "EPSG:32648"))

    buffer = io.BytesIO()
    
    # GeoTIFF block size must be multiple of 16
    # 计算合法的块大小
    def _make_block_size(size):
        if size < 16:
            return None  # 小图像不使用tiled模式
        return min(512, (size // 16) * 16)
    
    block_w = _make_block_size(w)
    block_h = _make_block_size(h)
    
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "width": w,
        "height": h,
        "count": 1,
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
    }
    
    # 仅在图像足够大时添加tiled参数
    if block_w and block_h:
        profile["tiled"] = True
        profile["blockxsize"] = block_w
        profile["blockysize"] = block_h

    # 对于大影像(>50MB预估输出)，使用分块写入
    estimated_size_mb = h * w / 1024 / 1024
    use_chunked = chunk_size > 0 and estimated_size_mb > 50

    with rasterio.open(buffer, "w", **profile) as dst:
        if use_chunked:
            # 分块写入避免内存峰值
            for row_off in range(0, h, chunk_size):
                for col_off in range(0, w, chunk_size):
                    win_h = min(chunk_size, h - row_off)
                    win_w = min(chunk_size, w - col_off)
                    block = prediction_map[row_off:row_off + win_h, col_off:col_off + win_w]
                    dst.write(block.astype(np.uint8), 1, window=Window(col_off, row_off, win_w, win_h))
                # 每行块后回收内存
                gc.collect()
        else:
            dst.write(prediction_map.astype(np.uint8), 1)

    buffer.seek(0)
    return buffer.getvalue()


def export_prediction_jpg(prediction_map, meta, dpi=150):
    """
    将分类结果导出为 JPG 图片（带图例和标注）。

    Args:
        prediction_map: np.ndarray (H, W), 0/1
        meta: dict, 包含地理元数据
        dpi: 输出分辨率

    Returns:
        bytes: JPG 文件二进制内容
    """
    from PIL import Image

    h, w = prediction_map.shape

    # 创建 RGB 图像: 竹林=绿色, 非竹林=浅灰
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    bamboo_mask = prediction_map == 1
    rgb[bamboo_mask] = [34, 139, 34]       # 森林绿
    rgb[~bamboo_mask] = [230, 230, 230]    # 浅灰

    # 降采样到合理尺寸（最大 3000px）
    max_dim = 3000
    if h > max_dim or w > max_dim:
        scale = min(max_dim / h, max_dim / w)
        new_h = max(1, int(h * scale))
        new_w = max(1, int(w * scale))
        img = Image.fromarray(rgb).resize((new_w, new_h), Image.NEAREST)
    else:
        img = Image.fromarray(rgb)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    return buffer.getvalue()


def export_statistics_csv(stats, meta, alerts=None):
    """
    导出统计数据为CSV

    Args:
        stats: dict, 统计信息
        meta: dict, 元数据
        alerts: list, 预警列表

    Returns:
        str: CSV内容字符串
    """
    width = meta.get("width", 0)
    height = meta.get("height", 0)

    data = {
        "分析时间": [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ""],
        "影像文件": [meta.get("filename", "未知"), ""],
        "影像尺寸": [f"{width} x {height}", "像素"],
        "空间分辨率": [meta.get("resolution_m", 10), "米"],
        "坐标系": [meta.get("crs_original", meta.get("crs", "未知")), ""],
        "竹林面积": [stats.get("bamboo_area_ha", 0), "公顷"],
        "竹林覆盖度": [stats.get("coverage_pct", 0), "%"],
        "竹林像素数": [stats.get("bamboo_pixels", 0), "个"],
        "总有效像素": [stats.get("total_pixels", 0), "个"],
    }

    df = pd.DataFrame([
        {"指标": k, "数值": v[0], "单位": v[1]} for k, v in data.items()
    ])

    # 如果有预警数据，追加预警表
    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")

    if alerts:
        output.write("\n\n预警信息\n")
        alert_df = pd.DataFrame(alerts)
        cols = ["alert_type", "severity", "location_desc", "affected_area_ha",
                "confidence", "suggested_action"]
        available_cols = [c for c in cols if c in alert_df.columns]
        if available_cols:
            alert_df[available_cols].to_csv(output, index=False, encoding="utf-8-sig")

    return output.getvalue()


def export_statistics_excel(stats, meta, alerts=None):
    """
    导出统计数据为Excel

    Returns:
        bytes: Excel文件二进制内容
    """
    buffer = io.BytesIO()

    width = meta.get("width", 0)
    height = meta.get("height", 0)

    data = {
        "指标": ["分析时间", "影像文件", "影像尺寸", "空间分辨率", "坐标系",
                 "竹林面积", "竹林覆盖度", "竹林像素数", "总有效像素"],
        "数值": [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            meta.get("filename", "未知"),
            f"{width} x {height}",
            meta.get("resolution_m", 10),
            meta.get("crs_original", meta.get("crs", "未知")),
            stats.get("bamboo_area_ha", 0),
            stats.get("coverage_pct", 0),
            stats.get("bamboo_pixels", 0),
            stats.get("total_pixels", 0),
        ],
        "单位": ["", "", "像素", "米", "", "公顷", "%", "个", "个"],
    }

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name="分析结果", index=False)

        if alerts:
            alert_df = pd.DataFrame(alerts)
            cols = ["alert_type", "severity", "location_desc", "affected_area_ha",
                    "confidence", "suggested_action", "created_at"]
            available_cols = [c for c in cols if c in alert_df.columns]
            if available_cols:
                alert_df[available_cols].to_excel(writer, sheet_name="预警信息", index=False)

    buffer.seek(0)
    return buffer.getvalue()


def generate_intelligent_evaluation(stats, meta, alerts=None):
    """
    生成智能评价性语句

    Returns:
        dict: 包含各类评价语句的字典
    """
    bamboo_area = stats.get("bamboo_area_ha", 0)
    coverage = stats.get("coverage_pct", 0)
    bamboo_pixels = stats.get("bamboo_pixels", 0)
    total_pixels = stats.get("total_pixels", 0)

    # 预警统计
    alert_count = len(alerts) if alerts else 0
    high_risk_count = sum(1 for a in alerts if a.get("severity") == "high") if alerts else 0
    medium_risk_count = sum(1 for a in alerts if a.get("severity") == "medium") if alerts else 0

    evaluations = {
        "overall_assessment": "",
        "resource_quality": "",
        "ecological_health": "",
        "management_suggestions": "",
        "risk_warnings": "",
        "future_outlook": ""
    }

    # 1. 总体评价
    if coverage >= 50:
        evaluations["overall_assessment"] = "🟢 优秀：该区域竹林覆盖度较高，竹林资源充足，为大熊猫提供了良好的栖息环境和食物来源。"
    elif coverage >= 30:
        evaluations["overall_assessment"] = "🟡 良好：该区域竹林覆盖度适中，基本满足大熊猫的觅食需求，建议持续监测。"
    elif coverage >= 15:
        evaluations["overall_assessment"] = "🟠 一般：该区域竹林覆盖度偏低，可能无法完全满足大熊猫的觅食需求，需关注竹林恢复情况。"
    else:
        evaluations["overall_assessment"] = "🔴 较差：该区域竹林覆盖度严重不足，大熊猫栖息环境堪忧，建议立即采取保护措施。"

    # 2. 资源质量评价
    if bamboo_area >= 5000:
        evaluations["resource_quality"] = "该区域竹林资源丰富，竹林面积超过5000公顷，为大熊猫提供了充足的食物来源和栖息空间。"
    elif bamboo_area >= 2000:
        evaluations["resource_quality"] = "该区域竹林资源较为丰富，竹林面积在2000-5000公顷之间，能够支持一定数量的大熊猫种群。"
    elif bamboo_area >= 500:
        evaluations["resource_quality"] = "该区域竹林资源一般，竹林面积在500-2000公顷之间，建议加强竹林保护和恢复工作。"
    else:
        evaluations["resource_quality"] = "该区域竹林资源匮乏，竹林面积不足500公顷，难以支撑大熊猫的长期生存需求。"

    # 3. 生态健康评价
    if alert_count == 0:
        evaluations["ecological_health"] = "✅ 生态健康状况良好，未发现明显的竹林退化或异常区域，生态系统稳定。"
    elif high_risk_count == 0:
        evaluations["ecological_health"] = f"⚠️ 生态健康状况一般，发现{alert_count}处中等风险区域，建议关注这些区域的动态变化。"
    else:
        evaluations["ecological_health"] = f"🚨 生态健康状况堪忧，发现{high_risk_count}处高风险区域和{medium_risk_count}处中等风险区域，需要立即采取保护措施。"

    # 4. 管理建议
    if coverage >= 40 and alert_count == 0:
        evaluations["management_suggestions"] = """建议采取以下管理措施：
  1. 维持现状：当前竹林资源状况良好，继续保持现有的保护措施。
  2. 定期监测：建议每季度进行一次遥感监测，及时发现潜在问题。
  3. 巡护优化：重点巡护竹林密集区域，确保大熊猫活动安全。"""
    elif coverage >= 20:
        evaluations["management_suggestions"] = """建议采取以下管理措施：
  1. 加强保护：增加巡护频次，防止人为破坏竹林资源。
  2. 恢复工程：在竹林稀疏区域开展人工补植，提高竹林覆盖率。
  3. 动态监测：建议每月进行一次遥感监测，密切关注竹林变化。"""
    else:
        evaluations["management_suggestions"] = """建议采取以下紧急措施：
  1. 立即干预：启动紧急保护预案，限制人类活动对竹林的影响。
  2. 大规模恢复：开展大规模竹林补植工程，优先恢复关键区域。
  3. 密集监测：建议每周进行一次遥感监测，实时掌握竹林动态。
  4. 科研支持：邀请林业专家进行现场调研，制定科学的恢复方案。"""

    # 5. 风险提示
    risk_factors = []
    if coverage < 20:
        risk_factors.append("竹林覆盖度严重不足，可能导致大熊猫食物短缺")
    if high_risk_count > 0:
        risk_factors.append(f"存在{high_risk_count}处高风险区域，可能威胁大熊猫安全")
    if bamboo_area < 1000:
        risk_factors.append("竹林面积过小，难以支撑大熊猫种群的长期生存")

    if risk_factors:
        evaluations["risk_warnings"] = "⚠️ 主要风险：\n  " + "\n  ".join([f"{i+1}. {risk}" for i, risk in enumerate(risk_factors)])
    else:
        evaluations["risk_warnings"] = "✅ 当前未发现明显风险因素，但仍需保持警惕，持续监测。"

    # 6. 未来展望
    if coverage >= 40 and alert_count == 0:
        evaluations["future_outlook"] = "基于当前良好的竹林资源状况，预计该区域能够持续为大熊猫提供优质的栖息环境。建议继续加强保护，确保生态系统的长期稳定。"
    elif coverage >= 20:
        evaluations["future_outlook"] = "通过加强保护和恢复措施，预计该区域竹林资源将逐步改善。建议制定3-5年的恢复计划，逐步提高竹林覆盖度。"
    else:
        evaluations["future_outlook"] = "当前竹林资源状况令人担忧，需要立即采取强有力的保护措施。如果不及时干预，该区域可能不再适合大熊猫栖息。建议启动紧急保护预案，争取在2-3年内显著改善竹林状况。"

    return evaluations


def generate_report_text(stats, meta, alerts=None):
    """
    生成智能评价文本报告

    Returns:
        str: 报告内容
    """
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    filename = meta.get("filename", "未知")
    width = meta.get("width", 0)
    height = meta.get("height", 0)
    resolution = meta.get("resolution_m", 10)
    crs = meta.get("crs_original", meta.get("crs", "未知"))
    bamboo_area = stats.get("bamboo_area_ha", 0)
    coverage = stats.get("coverage_pct", 0)
    bamboo_pixels = stats.get("bamboo_pixels", 0)
    total_pixels = stats.get("total_pixels", 0)

    # 生成智能评价
    evaluations = generate_intelligent_evaluation(stats, meta, alerts)

    report = f"""
=====================================
  大熊猫主食竹监测分析报告
=====================================

报告生成时间: {now}
分析区域: 王朗自然保护区

一、影像数据信息
  - 文件名: {filename}
  - 影像尺寸: {width} x {height} 像素
  - 空间分辨率: {resolution}米
  - 坐标系: {crs}

二、分析结果
  - 预估竹林面积: {bamboo_area:,.2f} 公顷
  - 竹林覆盖度: {coverage:.1f}%
  - 竹林像素数: {bamboo_pixels:,}
  - 有效像素总数: {total_pixels:,}

三、智能评价

【总体评价】
{evaluations['overall_assessment']}

【资源质量评价】
{evaluations['resource_quality']}

【生态健康评价】
{evaluations['ecological_health']}

【管理建议】
{evaluations['management_suggestions']}

【风险提示】
{evaluations['risk_warnings']}

【未来展望】
{evaluations['future_outlook']}
"""

    if alerts:
        report += "\n四、预警信息\n"
        severity_map = {"high": "高", "medium": "中", "low": "低"}
        for i, alert in enumerate(alerts, 1):
            alert_type = alert.get("alert_type", "未知")
            severity = severity_map.get(alert.get("severity", "low"), "未知")
            location = alert.get("location_desc", "未知")
            area = alert.get("affected_area_ha", 0)
            action = alert.get("suggested_action", "无")
            report += f"""
  预警{i}:
    - 类型: {alert_type}
    - 严重程度: {severity}
    - 位置: {location}
    - 影响面积: {area} 公顷
    - 建议操作: {action}
"""

    report += """
=====================================
  报告生成: 大熊猫主食竹智能监测系统
=====================================
"""
    return report
