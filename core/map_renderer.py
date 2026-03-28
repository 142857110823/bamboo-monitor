"""
地图渲染引擎
负责 folium 地图构建、分类结果的 RGBA 转换、降采样和 ImageOverlay 叠加。
修复审查报告指出的 map_renderer.py:112 参数未验证和 :232 边界检查不足问题。
"""
import logging
import numpy as np
from PIL import Image
import folium
from folium.plugins import HeatMap
from folium.raster_layers import ImageOverlay

from core.config import (
    WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON, DEFAULT_ZOOM,
    BAMBOO_COLOR_RGBA, NON_BAMBOO_COLOR_RGBA, MAX_DISPLAY_SIZE,
)

logger = logging.getLogger(__name__)


def prediction_to_rgba(prediction_map):
    """将分类结果转换为 RGBA 图像数组"""
    if prediction_map is None or prediction_map.size == 0:
        return np.zeros((1, 1, 4), dtype=np.uint8)

    h, w = prediction_map.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    bamboo_mask = prediction_map == 1
    rgba[bamboo_mask] = BAMBOO_COLOR_RGBA
    rgba[~bamboo_mask] = NON_BAMBOO_COLOR_RGBA

    return rgba


def downsample_rgba(rgba, max_size=MAX_DISPLAY_SIZE):
    """对 RGBA 图像降采样以确保浏览器渲染性能"""
    if rgba is None or rgba.size == 0:
        return np.zeros((1, 1, 4), dtype=np.uint8)

    h, w = rgba.shape[:2]

    if h <= max_size and w <= max_size:
        return rgba

    scale = min(max_size / h, max_size / w)
    new_h = max(1, int(h * scale))
    new_w = max(1, int(w * scale))

    img = Image.fromarray(rgba)
    img_resized = img.resize((new_w, new_h), Image.NEAREST)

    return np.array(img_resized)


def _validate_bounds(bounds_wgs84):
    """验证 WGS84 边界元组的合法性"""
    if bounds_wgs84 is None:
        return False
    if not isinstance(bounds_wgs84, (tuple, list)) or len(bounds_wgs84) != 4:
        return False
    try:
        west, south, east, north = [float(x) for x in bounds_wgs84]
    except (TypeError, ValueError):
        return False
    if west >= east or south >= north:
        return False
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return False
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        return False
    return True


def _safe_zoom(lat_range):
    """根据纬度范围安全计算缩放级别"""
    if lat_range <= 0 or not np.isfinite(lat_range):
        return DEFAULT_ZOOM
    try:
        raw = 14 - np.log2(max(lat_range, 0.0001) / 0.01)
        return max(5, min(18, int(raw)))
    except (ValueError, OverflowError):
        return DEFAULT_ZOOM


def create_base_map(center_lat=None, center_lon=None, zoom=None, tiles="OpenStreetMap"):
    """创建基础 folium 地图"""
    lat = center_lat if center_lat is not None else WANGLANG_CENTER_LAT
    lon = center_lon if center_lon is not None else WANGLANG_CENTER_LON
    z = zoom if zoom is not None else DEFAULT_ZOOM

    m = folium.Map(
        location=[lat, lon],
        zoom_start=z,
        tiles=tiles,
        control_scale=True,
    )

    return m


def add_protection_area_marker(m, lat=None, lon=None):
    """在地图上添加保护区中心标记"""
    lat = lat if lat is not None else WANGLANG_CENTER_LAT
    lon = lon if lon is not None else WANGLANG_CENTER_LON

    folium.Marker(
        [lat, lon],
        popup=folium.Popup(
            "<b>王朗自然保护区</b><br>四川省绵阳市平武县<br>大熊猫主食竹核心栖息地",
            max_width=250,
        ),
        tooltip="王朗保护区中心",
        icon=folium.Icon(color="green", icon="tree-conifer", prefix="glyphicon"),
    ).add_to(m)

    return m


def add_prediction_overlay(m, prediction_map, bounds_wgs84):
    """
    将分类结果作为栅格图层叠加到 folium 地图上。
    增加对 prediction_map 和 bounds_wgs84 的验证。
    """
    # 参数验证
    if prediction_map is None or prediction_map.size == 0:
        logger.warning("prediction_map 为空，跳过叠加")
        return m

    if not _validate_bounds(bounds_wgs84):
        logger.warning("bounds_wgs84 无效: %s，跳过叠加", bounds_wgs84)
        return m

    # Step 1: 转 RGBA
    rgba = prediction_to_rgba(prediction_map)

    # Step 2: 降采样
    rgba = downsample_rgba(rgba)

    # Step 3: 解析边界
    west, south, east, north = [float(x) for x in bounds_wgs84]
    bounds = [[south, west], [north, east]]

    # Step 4: 叠加到地图
    try:
        ImageOverlay(
            image=rgba,
            bounds=bounds,
            opacity=0.7,
            name="竹林分类结果",
            interactive=True,
            zindex=1,
        ).add_to(m)
    except Exception as e:
        logger.error("ImageOverlay 叠加失败: %s", e)

    return m


def add_alert_markers(m, alerts):
    """在地图上添加预警标记"""
    if not alerts:
        return m

    severity_colors = {"high": "red", "medium": "orange", "low": "blue"}
    type_icons = {
        "degradation": "exclamation-sign",
        "low_coverage": "warning-sign",
        "fragmentation": "th",
    }

    for alert in alerts:
        lat = alert.get("center_lat")
        lon = alert.get("center_lon")
        if lat is None or lon is None:
            continue
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            continue

        color = severity_colors.get(alert.get("severity", "low"), "blue")
        icon = type_icons.get(alert.get("alert_type", ""), "info-sign")

        alert_type = str(alert.get("alert_type", "未知"))
        severity = str(alert.get("severity", "未知"))
        area = alert.get("affected_area_ha", 0)
        confidence = alert.get("confidence", 0)
        action = str(alert.get("suggested_action", "无"))

        popup_html = (
            "<b>预警类型:</b> {}<br>"
            "<b>严重程度:</b> {}<br>"
            "<b>影响面积:</b> {} 公顷<br>"
            "<b>置信度:</b> {:.0%}<br>"
            "<b>建议:</b> {}"
        ).format(alert_type, severity, area, confidence, action)

        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=str(alert.get("location_desc", "预警区域")),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(m)

    return m


def add_heatmap_layer(m, points, name="竹林密度热力图"):
    """添加热力图图层"""
    if points:
        HeatMap(
            points,
            radius=20,
            blur=15,
            gradient={0.2: "#ffffb2", 0.4: "#a1dab4", 0.6: "#41b6c4", 0.8: "#2c7fb8", 1.0: "#253494"},
            name=name,
        ).add_to(m)

    return m


def build_analysis_map(prediction_map, bounds_wgs84, alerts=None):
    """构建完整的分析结果地图（组合全部图层）"""
    if not _validate_bounds(bounds_wgs84):
        logger.warning("bounds_wgs84 无效，使用默认中心点")
        m = create_base_map()
        m = add_protection_area_marker(m)
        folium.LayerControl().add_to(m)
        return m

    west, south, east, north = [float(x) for x in bounds_wgs84]
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2

    lat_range = north - south
    zoom = _safe_zoom(lat_range)

    m = create_base_map(center_lat, center_lon, zoom)
    m = add_protection_area_marker(m, center_lat, center_lon)

    if prediction_map is not None and prediction_map.size > 0:
        m = add_prediction_overlay(m, prediction_map, bounds_wgs84)

    if alerts:
        m = add_alert_markers(m, alerts)

    folium.LayerControl().add_to(m)

    return m
