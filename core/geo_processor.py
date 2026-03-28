"""
GeoTIFF 处理引擎
负责 TIF 文件的内存流读取、分块窗口计算、坐标转换、元数据提取
适配真实影像 Wanglang_NDVI_Composite.tif (WGS84坐标系)
"""
import gc
import logging
import numpy as np
from io import BytesIO
import math

import rasterio
from rasterio.crs import CRS
from rasterio.windows import Window
from rasterio.warp import transform_bounds

from core.config import (
    CHUNK_SIZE, PIXEL_AREA_HA, 
    METERS_PER_DEG_LON, METERS_PER_DEG_LAT
)

logger = logging.getLogger(__name__)


class TifReader:
    """
    GeoTIFF 读取器，使用上下文管理器确保资源正确释放。
    """

    def __init__(self, uploaded_file):
        self._file_bytes = BytesIO(uploaded_file.read())
        self._dataset = None
        self.meta = None
        self.filename = getattr(uploaded_file, "name", "unknown.tif")
        self.file_size_mb = round(len(self._file_bytes.getvalue()) / (1024 * 1024), 1)

    def __enter__(self):
        self._dataset = rasterio.open(self._file_bytes)
        self.meta = extract_metadata(self._dataset)
        self.meta["filename"] = self.filename
        self.meta["file_size_mb"] = self.file_size_mb
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dataset is not None:
            try:
                self._dataset.close()
            except Exception:
                pass
            self._dataset = None
        self._file_bytes = None
        return False

    @property
    def dataset(self):
        if self._dataset is None:
            raise RuntimeError("TifReader 尚未打开，请在 with 块内使用")
        return self._dataset


def read_tif_from_upload(uploaded_file):
    """
    向后兼容的快捷函数。
    注意：调用方 **必须** 在使用完毕后调用 dataset.close()。
    推荐改用 TifReader 上下文管理器。
    """
    file_bytes = BytesIO(uploaded_file.read())
    dataset = rasterio.open(file_bytes)

    meta = extract_metadata(dataset)
    meta["filename"] = getattr(uploaded_file, "name", "unknown.tif")
    meta["file_size_mb"] = round(len(file_bytes.getvalue()) / (1024 * 1024), 1)

    return {
        "dataset": dataset,
        "file_bytes": file_bytes,
        "meta": meta,
    }


def extract_metadata(dataset):
    """
    从 rasterio dataset 提取元数据
    适配 WGS84 (EPSG:4326) 坐标系的真实影像
    """
    width = dataset.width
    height = dataset.height
    bounds = dataset.bounds
    transform = dataset.transform

    # 标准化 CRS 为字符串
    crs_str = "unknown"
    crs_obj = dataset.crs
    if crs_obj is not None:
        try:
            crs_str = crs_obj.to_string()
        except Exception:
            crs_str = str(crs_obj)

    # 判断是否已经是WGS84坐标系
    is_wgs84 = crs_str and ("EPSG:4326" in crs_str or "WGS84" in crs_str or "4326" in crs_str)

    # 计算像素分辨率
    if transform and transform.a != 0:
        res_x = abs(transform.a)
        res_y = abs(transform.e)
        
        if is_wgs84:
            # WGS84坐标系：分辨率是度，需要转换为米
            # 在影像中心纬度处计算
            center_lat = (bounds.top + bounds.bottom) / 2
            res_x_m = res_x * METERS_PER_DEG_LON * math.cos(math.radians(center_lat))
            res_y_m = res_y * METERS_PER_DEG_LAT
            resolution_m = (res_x_m + res_y_m) / 2
            # WGS84坐标系直接使用原边界
            bounds_wgs84 = (bounds.left, bounds.bottom, bounds.right, bounds.top)
        else:
            # UTM或其他投影坐标系：分辨率已经是米
            resolution_m = (res_x + res_y) / 2
            # 需要转换到WGS84
            bounds_wgs84 = None
            if crs_obj is not None:
                try:
                    dst_crs = CRS.from_epsg(4326)
                    bounds_wgs84 = transform_bounds(
                        crs_obj, dst_crs,
                        bounds.left, bounds.bottom, bounds.right, bounds.top
                    )
                except Exception as e:
                    logger.warning("CRS 坐标转换失败: %s", e)
    else:
        resolution_m = 30  # 默认30米
        bounds_wgs84 = (bounds.left, bounds.bottom, bounds.right, bounds.top) if is_wgs84 else None

    # 计算像素面积（公顷）
    pixel_area_ha = (resolution_m ** 2) / 10000

    return {
        "width": width,
        "height": height,
        "count": dataset.count,
        "crs_original": crs_str,
        "resolution_m": round(resolution_m, 2),
        "bounds_native": (bounds.left, bounds.bottom, bounds.right, bounds.top),
        "bounds_wgs84": bounds_wgs84,
        "transform": transform,
        "pixel_area_ha": pixel_area_ha,
        "is_wgs84": is_wgs84,
    }


def compute_chunk_windows(width, height, chunk_size=CHUNK_SIZE):
    """
    计算分块窗口列表
    """
    windows = []
    n_cols = math.ceil(width / chunk_size)
    n_rows = math.ceil(height / chunk_size)

    for row_idx in range(n_rows):
        for col_idx in range(n_cols):
            col_off = col_idx * chunk_size
            row_off = row_idx * chunk_size
            win_width = min(chunk_size, width - col_off)
            win_height = min(chunk_size, height - row_off)
            windows.append(Window(col_off, row_off, win_width, win_height))

    return windows


def read_chunk_features(dataset, window):
    """
    从指定窗口读取双波段特征数据。
    处理 NaN 值和 NoData。
    """
    band1 = dataset.read(1, window=window).astype(np.float32)  # 夏季 NDVI
    band2 = dataset.read(2, window=window).astype(np.float32)  # 冬季 NDVI

    # 检测 NoData（NaN 或极端值）
    nodata = dataset.nodata
    if nodata is not None:
        valid_mask = (band1 != nodata) & (band2 != nodata) & np.isfinite(band1) & np.isfinite(band2)
    else:
        # 真实影像可能有NaN值，使用isfinite检测
        valid_mask = np.isfinite(band1) & np.isfinite(band2)

    summer_flat = band1.flatten()
    winter_flat = band2.flatten()
    valid_flat = valid_mask.flatten()

    features = np.column_stack([summer_flat, winter_flat])

    # 及时释放中间变量
    del band1, band2, summer_flat, winter_flat, valid_mask

    return features, valid_flat


def compute_statistics(prediction_map, pixel_area_ha):
    """
    基于分类结果计算统计指标。
    """
    total_pixels = int(prediction_map.size)
    bamboo_pixels = int(np.sum(prediction_map == 1))
    non_bamboo_pixels = int(np.sum(prediction_map == 0))

    # 有效像素 = 竹林 + 非竹林（排除可能的异常值）
    valid_pixels = bamboo_pixels + non_bamboo_pixels
    if valid_pixels == 0:
        valid_pixels = total_pixels

    bamboo_area_ha = round(bamboo_pixels * pixel_area_ha, 2)
    coverage_pct = round(bamboo_pixels / valid_pixels * 100, 1) if valid_pixels > 0 else 0.0

    return {
        "bamboo_pixels": bamboo_pixels,
        "total_pixels": valid_pixels,
        "bamboo_area_ha": bamboo_area_ha,
        "coverage_pct": coverage_pct,
    }
