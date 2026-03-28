"""
预警规则引擎
基于分类结果自动识别异常区域，生成预警和巡护建议。
修复审查报告指出的 alert_engine.py:93 bounds_wgs84 未验证问题。
"""
import logging
import numpy as np
import uuid
from datetime import datetime

from core.config import (
    ALERT_COVERAGE_LOW, ALERT_COVERAGE_MEDIUM,
    ALERT_AREA_CHANGE_THRESHOLD,
    WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON,
)

logger = logging.getLogger(__name__)


def _validate_bounds(bounds_wgs84):
    """验证 WGS84 边界的合法性"""
    if bounds_wgs84 is None:
        return False
    if not isinstance(bounds_wgs84, (tuple, list)) or len(bounds_wgs84) != 4:
        return False
    west, south, east, north = bounds_wgs84
    # 基本合理性检查：经度 [-180, 180]，纬度 [-90, 90]
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return False
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        return False
    if west >= east or south >= north:
        return False
    return True


def analyze_regions(prediction_map, bounds_wgs84, pixel_area_ha, grid_size=5):
    """
    将分类结果划分为网格区域并逐区域分析
    """
    if not _validate_bounds(bounds_wgs84):
        logger.warning("bounds_wgs84 无效: %s，使用默认边界", bounds_wgs84)
        # 使用王朗保护区附近的默认边界
        bounds_wgs84 = (
            WANGLANG_CENTER_LON - 0.025,
            WANGLANG_CENTER_LAT - 0.022,
            WANGLANG_CENTER_LON + 0.025,
            WANGLANG_CENTER_LAT + 0.022,
        )

    h, w = prediction_map.shape
    west, south, east, north = bounds_wgs84

    block_h = max(1, h // grid_size)
    block_w = max(1, w // grid_size)

    lat_step = (north - south) / grid_size
    lon_step = (east - west) / grid_size

    regions = []
    direction_names = [
        ["西北", "北偏西", "正北", "北偏东", "东北"],
        ["西偏北", "中北偏西", "中北", "中北偏东", "东偏北"],
        ["正西", "中西", "中心", "中东", "正东"],
        ["西偏南", "中南偏西", "中南", "中南偏东", "东偏南"],
        ["西南", "南偏西", "正南", "南偏东", "东南"],
    ]

    for row in range(grid_size):
        for col in range(grid_size):
            r_start = row * block_h
            r_end = r_start + block_h if row < grid_size - 1 else h
            c_start = col * block_w
            c_end = c_start + block_w if col < grid_size - 1 else w

            block = prediction_map[r_start:r_end, c_start:c_end]
            total = block.size
            if total == 0:
                continue
            bamboo = int(np.sum(block == 1))
            coverage = bamboo / total * 100
            area_ha = round(bamboo * pixel_area_ha, 2)

            center_lat = north - (row + 0.5) * lat_step
            center_lon = west + (col + 0.5) * lon_step

            name_row = min(row, len(direction_names) - 1)
            name_col = min(col, len(direction_names[0]) - 1)
            location = direction_names[name_row][name_col] + "区域"

            regions.append({
                "location_desc": location,
                "center_lat": round(center_lat, 6),
                "center_lon": round(center_lon, 6),
                "bamboo_pixels": bamboo,
                "total_pixels": total,
                "coverage_pct": round(coverage, 1),
                "bamboo_area_ha": area_ha,
            })

    return regions


def generate_alerts(prediction_map, bounds_wgs84, pixel_area_ha, record_id=None):
    """
    基于分类结果生成预警列表。
    增加 bounds_wgs84 验证和 scipy 可选依赖的安全处理。
    """
    regions = analyze_regions(prediction_map, bounds_wgs84, pixel_area_ha)
    alerts = []

    for region in regions:
        coverage = region["coverage_pct"]
        alert = None

        if coverage < ALERT_COVERAGE_LOW:
            alert = {
                "id": str(uuid.uuid4()),
                "record_id": record_id,
                "alert_type": "low_coverage",
                "severity": "high",
                "location_desc": region["location_desc"],
                "center_lat": region["center_lat"],
                "center_lon": region["center_lon"],
                "affected_area_ha": region["bamboo_area_ha"],
                "confidence": round(min(0.95, 0.7 + (ALERT_COVERAGE_LOW - coverage) / 100), 2),
                "suggested_action": "该区域竹林覆盖率仅{:.1f}%，建议立即派员实地核查，重点排查退化原因".format(coverage),
                "created_at": datetime.now().isoformat(),
            }
        elif coverage < ALERT_COVERAGE_MEDIUM:
            alert = {
                "id": str(uuid.uuid4()),
                "record_id": record_id,
                "alert_type": "degradation",
                "severity": "medium",
                "location_desc": region["location_desc"],
                "center_lat": region["center_lat"],
                "center_lon": region["center_lon"],
                "affected_area_ha": region["bamboo_area_ha"],
                "confidence": round(0.6 + (ALERT_COVERAGE_MEDIUM - coverage) / 200, 2),
                "suggested_action": "该区域竹林覆盖率为{:.1f}%，建议加强定期监测频次，纳入下次巡护路线".format(coverage),
                "created_at": datetime.now().isoformat(),
            }

        if alert:
            alerts.append(alert)

    # 碎片化检测（scipy 为可选依赖）
    total_size = prediction_map.size
    if total_size > 0:
        overall_coverage = np.sum(prediction_map == 1) / total_size * 100
        if overall_coverage > 20:
            try:
                from scipy import ndimage
                labeled, n_patches = ndimage.label(prediction_map == 1)
                del labeled  # 立即释放大数组
                if n_patches > 50:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "record_id": record_id,
                        "alert_type": "fragmentation",
                        "severity": "medium",
                        "location_desc": "全域",
                        "center_lat": WANGLANG_CENTER_LAT,
                        "center_lon": WANGLANG_CENTER_LON,
                        "affected_area_ha": round(np.sum(prediction_map == 1) * pixel_area_ha, 2),
                        "confidence": 0.70,
                        "suggested_action": "检测到{}个独立竹林斑块，碎片化程度较高，建议关注生态廊道连通性".format(n_patches),
                        "created_at": datetime.now().isoformat(),
                    })
            except ImportError:
                logger.info("scipy 不可用，跳过碎片化检测")
            except Exception as e:
                logger.warning("碎片化检测失败: %s", e)

    # 按严重程度排序
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

    return alerts
