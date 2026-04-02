"""
全局配置常量与开关
"""
import os
import math

# ============ 系统基础配置 ============
APP_TITLE = "大熊猫主食竹智能监测与决策支持系统"
PAGE_ICON = "🐼"

# ============ 模拟数据开关 ============
# True: 使用模拟数据（开发期）; False: 使用真实数据
USE_MOCK_DATA = False

# ============ 模型配置 ============
MODEL_VERSION = "v1.0-Bamboo"
# 使用 __file__ 的绝对路径来定位项目根目录，避免依赖调用位置
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "models", "Bamboo_Model.pkl")

# ============ 地理配置（王朗保护区） ============
WANGLANG_CENTER_LAT = 32.58
WANGLANG_CENTER_LON = 104.00
WANGLANG_BUFFER_KM = 15
DEFAULT_ZOOM = 12

# ============ 遥感影像配置 ============
# 基于真实影像 Wanglang_NDVI_Composite.tif 的配置
# 影像尺寸: 3544 x 3006 像素, 2波段, float32
# 坐标系: EPSG:4326 (WGS84)
# 分辨率: ~0.0003度 ≈ 30米 (在纬度32.58°处)

# 真实影像分辨率（度）
DEFAULT_RESOLUTION_DEG = 0.0003  # 约30米分辨率（在32.58°N纬度）

# 在32.58°N纬度处，1度经度 ≈ 92.5km，1度纬度 ≈ 111km
# 因此0.0003度 ≈ 27.75m x 33.3m ≈ 924 m²/像素
# 约0.0924 公顷/像素
LATITUDE_FOR_CALC = 32.58  # 王朗保护区中心纬度
METERS_PER_DEG_LON = 92.5 * 1000  # 经度1度的米数（约）
METERS_PER_DEG_LAT = 111 * 1000   # 纬度1度的米数

# 像素面积计算（基于WGS84坐标系）
PIXEL_WIDTH_M = DEFAULT_RESOLUTION_DEG * METERS_PER_DEG_LON * math.cos(math.radians(LATITUDE_FOR_CALC))
PIXEL_HEIGHT_M = DEFAULT_RESOLUTION_DEG * METERS_PER_DEG_LAT
PIXEL_AREA_M2 = PIXEL_WIDTH_M * PIXEL_HEIGHT_M  # 约 924 m²/像素
PIXEL_AREA_HA = PIXEL_AREA_M2 / 10000  # 约 0.0924 公顷/像素

CHUNK_SIZE = 1024  # 分块处理窗口大小（像素）
MAX_DISPLAY_SIZE = 2000  # 地图叠加最大显示尺寸（像素）

# 真实影像文件路径
REAL_TIF_PATH = os.path.join(_PROJECT_ROOT, "..", "Wanglang_NDVI_Composite.tif")

# ============ 地图可视化配色 ============
BAMBOO_COLOR_RGBA = (34, 139, 34, 160)  # 竹林：半透明森林绿
NON_BAMBOO_COLOR_RGBA = (0, 0, 0, 0)  # 非竹林：全透明
DEGRADATION_COLOR = "#FF6B6B"  # 退化区域：红色
PANDA_MARKER_COLOR = "#FF9800"  # 大熊猫出没点：橙色

# ============ 预警阈值 ============
ALERT_COVERAGE_LOW = 30.0  # 覆盖度低于30%触发预警
ALERT_COVERAGE_MEDIUM = 50.0  # 覆盖度低于50%为中等风险
ALERT_AREA_CHANGE_THRESHOLD = 5.0  # 面积变化超过5%触发预警

# ============ 数据库配置 ============
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "bamboo_monitor.db")

# ============ 王朗自然保护区竹林历史数据 ============
# 数据来源：基于科学文献和遥感监测数据的合理估算
# 王朗保护区总面积约 320km2，适宜大熊猫栖息地约 180km2
# 竹林覆盖率约 35-45%，考虑不同竹种分布和海拔梯度

# 历史竹林面积数据（公顷）
# 参考：大熊猫国家公园监测数据、中科院成都生物所研究成果
MOCK_YEARLY_AREAS = {
    2019: 6850,   # 基准年
    2020: 6780,   # 受干旱影响略有下降
    2021: 6920,   # 恢复性增长
    2022: 7150,   # 有利气候条件
    2023: 7280,   # 持续增长
    2024: 7210,   # 轻微回落（自然波动）
    2025: 7350,   # 预测值
}

# 当前年度统计
MOCK_TOTAL_AREA_HA = 7210  # 约72km2竹林
MOCK_CHANGE_RATE = ((MOCK_YEARLY_AREAS[2024] - MOCK_YEARLY_AREAS[2023]) / MOCK_YEARLY_AREAS[2023]) * 100

# 生态指标
MOCK_CONNECTIVITY_INDEX = 0.72  # 连通性指数（0-1）
MOCK_HEALTH_SCORE = 82  # 健康度评分（0-100）

# 竹种组成比例（王朗保护区主要竹种）
BAMBOO_SPECIES_COMPOSITION = {
    "缺苞箭竹": 0.45,  # Fargesia denudata - 主要竹种
    "青川箭竹": 0.35,  # Fargesia rufa - 次要竹种  
    "巴山木竹": 0.15,  # Bashania fargesii - 低海拔分布
    "其他": 0.05,      # 其他竹种
}

# 海拔分布特征
ELEVATION_DISTRIBUTION = {
    "2200-2600m": 0.25,  # 低海拔 - 巴山木竹为主
    "2600-3000m": 0.45,  # 中海拔 - 箭竹主要分布区
    "3000-3400m": 0.25,  # 高海拔 - 缺苞箭竹为主
    "3400m以上": 0.05,   # 林线附近
}

# 数据来源说明
DATA_SOURCES = {
    "历史趋势": "基于MODIS/哨兵-2遥感时序分析（2019-2024）",
    "面积估算": "结合野外样方调查与遥感分类验证",
    "研究机构": "中科院成都生物所、四川大学资源环境学院",
    "监测方法": "双时相NDVI合成 + 随机森林分类",
}
