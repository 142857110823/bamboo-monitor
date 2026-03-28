"""
模型推理引擎
负责随机森林模型的加载、缓存、分块推理和全图预测编排
"""
import gc
import os
import time
import logging
import numpy as np
import joblib
import streamlit as st

from core.config import MODEL_PATH, MODEL_VERSION, CHUNK_SIZE
from core.geo_processor import compute_chunk_windows, read_chunk_features

logger = logging.getLogger(__name__)


@st.cache_resource
def load_model():
    """
    加载随机森林模型（进程级缓存，所有用户共享同一实例）
    """
    if not os.path.exists(MODEL_PATH):
        from core.mock_generator import generate_mock_model
        return generate_mock_model()

    return joblib.load(MODEL_PATH)


def predict_chunk(model, features, valid_mask):
    """
    对单个块执行模型预测
    """
    prediction = np.zeros(len(valid_mask), dtype=np.int8)

    if np.any(valid_mask):
        valid_features = features[valid_mask]
        valid_pred = model.predict(valid_features)
        prediction[valid_mask] = valid_pred.astype(np.int8)

    return prediction


def predict_full_image(dataset, progress_callback=None):
    """
    全图分块推理编排。
    修复审查报告指出的 model_engine.py:79 边界条件问题：
    - 增加对 dataset 尺寸为 0 的边界检查
    - 增加 window 与 prediction_map 维度匹配的安全校验
    - 增加 gc.collect() 在大影像下的内存回收
    """
    start_time = time.time()

    model = load_model()
    width = dataset.width
    height = dataset.height

    if width == 0 or height == 0:
        logger.warning("影像尺寸为零: width=%d, height=%d", width, height)
        return np.zeros((max(height, 1), max(width, 1)), dtype=np.int8), 0.0

    # 初始化结果数组（int8 节省内存）
    prediction_map = np.zeros((height, width), dtype=np.int8)

    # 计算分块窗口
    windows = compute_chunk_windows(width, height, CHUNK_SIZE)
    total_chunks = len(windows)

    for i, window in enumerate(windows):
        # 读取当前块的特征
        features, valid_mask = read_chunk_features(dataset, window)

        # 执行预测
        pred = predict_chunk(model, features, valid_mask)

        # 安全写入结果数组：显式转换为 int 并做边界校验
        win_h = int(window.height)
        win_w = int(window.width)
        row_start = int(window.row_off)
        col_start = int(window.col_off)

        # 边界校验：防止越界
        row_end = min(row_start + win_h, height)
        col_end = min(col_start + win_w, width)
        actual_h = row_end - row_start
        actual_w = col_end - col_start

        pred_block = pred[:actual_h * actual_w].reshape(actual_h, actual_w)
        prediction_map[row_start:row_end, col_start:col_end] = pred_block

        # 释放中间变量
        del features, valid_mask, pred, pred_block

        # 大影像时定期回收内存
        if total_chunks > 10 and i % 5 == 0:
            gc.collect()

        # 更新进度
        if progress_callback:
            progress_callback(i + 1, total_chunks)

    processing_time = round(time.time() - start_time, 1)

    return prediction_map, processing_time


def get_model_info():
    """获取模型信息"""
    model = load_model()
    info = {
        "version": MODEL_VERSION,
        "type": type(model).__name__,
        "n_features": model.n_features_in_ if hasattr(model, 'n_features_in_') else 2,
    }
    if hasattr(model, "n_estimators"):
        info["n_estimators"] = model.n_estimators
    return info
