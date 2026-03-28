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


def generate_report_text(stats, meta, alerts=None):
    """
    生成简易文本报告

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

    distribution = "集中" if coverage > 40 else "较为分散"
    suitability = "适合" if coverage > 30 else "需关注是否满足"

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

三、决策建议
  1. 资源评估: 该区域竹林分布{distribution}，
     {suitability}大熊猫觅食需求。
  2. 巡护建议: 建议重点关注海拔2200-2500米区域。
  3. 风险提示: 冬季高海拔区域可能有积雪，请注意防滑。
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
