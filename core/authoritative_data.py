"""权威数据配置

基于中国科学院成都山地所等权威机构的研究数据
"""

# 王朗自然保护区基础数据
WANG_LANG_DATA = {
    # 总面积（平方公里）
    "total_area_km2": 322.97,
    
    # 主食竹分布数据（基于2026年中科院成都山地所研究）
    "bamboo_data": {
        "total_area_ha": 10000,  # 竹类资源分布面积约一万公顷
        "accuracy": 83,  # 数据精度（%）
        "resolution": 10,  # 分辨率（米）
        "last_update": "2026-03",  # 数据更新时间
        "main_species": "缺苞箭竹",  # 主要主食竹
        "other_species": ["华西箭竹", "团竹"],  # 其他竹种
        "main_distribution": ["大窝荡", "竹根岔", "长白沟"],  # 主要分布区域
        "elevation_range": "2500-3000米",  # 海拔分布
    },
    
    # 植被变化数据（2011-2020年）
    "vegetation_change": {
        "shrub_decrease_km2": 23.17,  # 灌丛减少面积
        "meadow_increase_km2": 20.71,  # 草甸增加面积
        "mixed_forest_increase_km2": 25.55,  # 针阔混交林增加面积
        "coniferous_increase_km2": 8.14,  # 针叶林增加面积
        "broadleaf_decrease_km2": 31.24,  # 常绿阔叶林减少面积
    },
    
    # 核心监测指标基准值
    "kpi_baseline": {
        "reserve_area_km2": 322.97,  # 王朗自然保护区面积（平方公里）
        "bamboo_monitoring_accuracy": 83,  # 主食竹监测精度（%）
        "bamboo_coverage_ratio": 35,  # 竹林占比（%）
        "bamboo_elevation_range": "2500-3000米",  # 主食竹海拔分布范围
    },
    
    # 预警数据
    "alert_data": {
        "total_alerts": 2,  # 总预警数
        "high_risk_alerts": 1,  # 高风险预警数
    },
    
    # 数据来源
    "data_sources": [
        "中国科学院成都山地灾害与环境研究所（2026）",
        "四川农业大学学报（2022）",
        "大熊猫国家公园管理局",
        "王朗自然保护区官方资料",
    ],
}

# 年度趋势数据（2019-2025）
YEARLY_TREND_DATA = [
    {"year": 2019, "area_km2": 93.59, "data_type": "基准反推值"},
    {"year": 2020, "area_km2": 95.99, "data_type": "遥感实测基准值"},
    {"year": 2021, "area_km2": 97.81, "data_type": "合规推演值"},
    {"year": 2022, "area_km2": 99.67, "data_type": "合规推演值"},
    {"year": 2023, "area_km2": 101.56, "data_type": "合规推演值"},
    {"year": 2024, "area_km2": 103.49, "data_type": "高分辨率基准推演值"},
    {"year": 2025, "area_km2": 105.46, "data_type": "趋势预测值"},
]

# 预警数据
alerts_data = [
    {
        "alert_id": "ALT-2026-001",
        "alert_type": "degradation",
        "severity": "high",
        "location_desc": "大窝荡区域",
        "affected_area_ha": 12.5,
        "confidence": 0.92,
        "suggested_action": "建议开展人工干预，促进竹林恢复",
        "created_at": "2026-03-15"
    },
    {
        "alert_id": "ALT-2026-002",
        "alert_type": "low_coverage",
        "severity": "medium",
        "location_desc": "竹根岔区域",
        "affected_area_ha": 8.3,
        "confidence": 0.85,
        "suggested_action": "加强监测，定期评估",
        "created_at": "2026-03-10"
    }
]
