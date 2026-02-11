"""
5G CQI关联性能分析系统 - 网络制式对比版
支持N41和N28网络制式左右对比展示
"""

import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Tuple

# 页面配置
st.set_page_config(
    page_title="5G CQI关联性能分析系统 - 网络制式对比",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E90FF;
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        padding: 10px 0;
        border-bottom: 2px solid #1E90FF;
        margin-bottom: 20px;
    }
    .network-type-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 15px;
    }
    .n41-header {
        background: linear-gradient(135deg, #1E90FF 0%, #4169E1 100%);
    }
    .n28-header {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    .highlight {
        background-color: #f0f8ff;
        padding: 15px;
        border-left: 4px solid #1E90FF;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    .comparison-divider {
        border-left: 3px dashed #ccc;
        height: 100%;
    }
    /* 标签页字体样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        font-size: 18px !important;
        font-weight: 700 !important;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E90FF !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


class CQI分析器:
    """CQI数据分析类"""

    def __init__(self, 文件路径: str):
        self.文件路径 = 文件路径
        self.原始数据 = None
        self.清洗后数据 = None

    def 读取数据(self) -> bool:
        try:
            self.原始数据 = pd.read_excel(self.文件路径)
            return True
        except Exception as e:
            st.error(f"读取文件失败: {e}")
            return False

    def 清洗数据(self) -> bool:
        # 列名映射：处理新旧Excel列名差异
        self.列名映射 = {
            '小区MR覆盖平均电平(dBm)': '小区MR覆盖平均电平'
        }
        # 重命名列
        for 新列名, 标准列名 in self.列名映射.items():
            if 新列名 in self.原始数据.columns:
                self.原始数据 = self.原始数据.rename(columns={新列名: 标准列名})
        
        关键列 = [
            'CQI优良率',
            '下行用户平均速率(MBPS)',
            '上行用户平均速率(MBPS)',
            '小区MR覆盖平均电平',
            '小区MR覆盖平均SINR',
            '小区MR覆盖平均TA',
            '小区上行平均干扰电平'
        ]
        if '网络制式' in self.原始数据.columns:
            关键列.append('网络制式')
        self.清洗后数据 = self.原始数据.dropna(subset=关键列)
        
        # 计算覆盖系数（如果原始数据中有相关列）
        if '覆盖系数' in self.清洗后数据.columns:
            # 覆盖系数已存在，确保数值有效
            self.清洗后数据['覆盖系数'] = pd.to_numeric(self.清洗后数据['覆盖系数'], errors='coerce')
        elif '方向角站间距（米）' in self.清洗后数据.columns and '小区MR覆盖平均TA' in self.清洗后数据.columns:
            # 计算覆盖系数 = TA / 站间距
            站间距 = pd.to_numeric(self.清洗后数据['方向角站间距（米）'], errors='coerce')
            TA = pd.to_numeric(self.清洗后数据['小区MR覆盖平均TA'], errors='coerce')
            self.清洗后数据['覆盖系数'] = TA / 站间距
        
        return True

    def 按网络制式分组(self) -> Dict:
        """按网络制式(n41/n28)分组数据"""
        if '网络制式' not in self.清洗后数据.columns:
            return {'全部': self.清洗后数据}

        分组结果 = {}
        for 制式 in self.清洗后数据['网络制式'].unique():
            分组结果[制式] = self.清洗后数据[self.清洗后数据['网络制式'] == 制式]
        return 分组结果

    def 判断相关性强度(self, 相关系数: float) -> str:
        if 相关系数 < 0.1:
            return "极弱"
        elif 相关系数 < 0.3:
            return "弱"
        elif 相关系数 < 0.5:
            return "中等"
        elif 相关系数 < 0.7:
            return "强"
        else:
            return "极强"

    def 计算相关性_按制式(self, 字段1: str, 字段2: str, 数据子集: pd.DataFrame = None) -> Dict:
        if 数据子集 is None:
            数据子集 = self.清洗后数据
        
        # 删除包含NaN的行，确保数据有效
        有效数据 = 数据子集[[字段1, 字段2]].dropna()
        
        # 检查有效数据量是否足够（至少需要3个样本）
        if len(有效数据) < 3:
            return {"相关系数": None, "P值": None}
        
        try:
            相关系数, p值 = stats.pearsonr(有效数据[字段1], 有效数据[字段2])
            return {"相关系数": 相关系数, "P值": p值}
        except Exception:
            return {"相关系数": None, "P值": None}

    def 分析CQI对速率影响_按制式(self) -> Dict:
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            结果[制式] = {}
            for 速率列 in ['下行用户平均速率(MBPS)', '上行用户平均速率(MBPS)']:
                相关性 = self.计算相关性_按制式('CQI优良率', 速率列, 数据)
                相关性['显著性'] = '显著' if 相关性['P值'] < 0.05 else '不显著'
                相关性['强度'] = self.判断相关性强度(abs(相关性['相关系数']))
                结果[制式][速率列] = 相关性
        return 结果

    def CQI分位数速率分析_按制式(self, 分位数: int = 5) -> Dict:
        """将CQI按分位数分组，计算每个分位数组的平均速率"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        
        for 制式, 数据 in 分组数据.items():
            if 'CQI优良率' not in 数据.columns:
                continue
                
            # 移除NaN
            有效数据 = 数据[['CQI优良率', '下行用户平均速率(MBPS)', '上行用户平均速率(MBPS)']].dropna()
            if len(有效数据) < 10:
                continue
            
            # 创建CQI分位数
            有效数据['CQI分位数'] = pd.qcut(有效数据['CQI优良率'], q=分位数, labels=[f"{i*20}-{(i+1)*20}%" for i in range(分位数)], duplicates='drop')
            
            # 按分位数分组计算平均速率
            分位数统计 = 有效数据.groupby('CQI分位数').agg({
                'CQI优良率': 'mean',
                '下行用户平均速率(MBPS)': 'mean',
                '上行用户平均速率(MBPS)': 'mean'
            }).reset_index()
            
            # 添加样本数
            样本数 = 有效数据.groupby('CQI分位数').size().to_dict()
            分位数统计['样本数'] = 分位数统计['CQI分位数'].map(样本数)
            
            # 计算速率提升率（相对于最低分位数）
            if len(分位数统计) > 1:
                基准下行 = 分位数统计.iloc[0]['下行用户平均速率(MBPS)']
                基准上行 = 分位数统计.iloc[0]['上行用户平均速率(MBPS)']
                分位数统计['下行提升率(%)'] = ((分位数统计['下行用户平均速率(MBPS)'] - 基准下行) / 基准下行 * 100).round(2)
                分位数统计['上行提升率(%)'] = ((分位数统计['上行用户平均速率(MBPS)'] - 基准上行) / 基准上行 * 100).round(2)
            
            结果[制式] = 分位数统计
            
        return 结果

    def 速率分布对比_按制式(self) -> Dict:
        """对比不同CQI等级的速率分布"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        
        for 制式, 数据 in 分组数据.items():
            if 'CQI优良率' not in 数据.columns:
                continue
            
            # 创建CQI等级（低<60%, 中60-85%, 高>85%）
            有效数据 = 数据[['CQI优良率', '下行用户平均速率(MBPS)', '上行用户平均速率(MBPS)']].dropna()
            if len(有效数据) < 10:
                continue
            
            有效数据['CQI等级'] = pd.cut(
                有效数据['CQI优良率'],
                bins=[0, 60, 85, 100],
                labels=['低CQI(<60%)', '中CQI(60-85%)', '高CQI(>85%)']
            )
            
            # 按等级统计
            统计结果 = 有效数据.groupby('CQI等级').agg({
                '下行用户平均速率(MBPS)': ['mean', 'std', 'min', 'max'],
                '上行用户平均速率(MBPS)': ['mean', 'std', 'min', 'max'],
                'CQI优良率': 'count'
            }).reset_index()
            
            统计结果.columns = ['CQI等级', '下行均值', '下行标准差', '下行最小值', '下行最大值',
                                 '上行均值', '上行标准差', '上行最小值', '上行最大值', '样本数']
            
            结果[制式] = 统计结果
            
        return 结果

    def 分析影响CQI的指标_按制式(self) -> Dict:
        影响指标 = [
            '小区MR覆盖平均电平',
            '小区MR覆盖平均SINR',
            '小区MR覆盖平均TA',
            '小区上行平均干扰电平',
            '上行PRB平均利用率',
            '下行PRB平均利用率',
            '覆盖系数',  # ⭐新增
            '重叠覆盖采样点比例(%)'  # ⭐新增
        ]
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            结果列表 = []
            for 指标 in 影响指标:
                if 指标 in 数据.columns:
                    相关性 = self.计算相关性_按制式('CQI优良率', 指标, 数据)
                    相关性['显著性'] = '显著' if 相关性['P值'] < 0.05 else '不显著'
                    相关性['强度'] = self.判断相关性强度(abs(相关性['相关系数']))
                    结果列表.append({**{"指标": 指标}, **相关性})
            结果[制式] = sorted(结果列表, key=lambda x: abs(x["相关系数"]), reverse=True)
        return 结果

    def 计算相关性矩阵_按制式(self, 列名列表: List[str]) -> Dict:
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            结果[制式] = 数据[列名列表].corr()
        return 结果

    def 获取统计摘要_按制式(self) -> Dict:
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            结果[制式] = {
                '数据量': len(数据),
                '平均CQI': 数据['CQI优良率'].mean(),
                'CQI标准差': 数据['CQI优良率'].std(),
                '平均下行速率': 数据['下行用户平均速率(MBPS)'].mean(),
                '下行速率标准差': 数据['下行用户平均速率(MBPS)'].std(),
                '平均上行速率': 数据['上行用户平均速率(MBPS)'].mean(),
                '上行速率标准差': 数据['上行用户平均速率(MBPS)'].std()
            }
            # 添加覆盖系数统计
            if '覆盖系数' in 数据.columns:
                结果[制式]['平均覆盖系数'] = 数据['覆盖系数'].mean()
                结果[制式]['覆盖系数标准差'] = 数据['覆盖系数'].std()
            # 添加重叠覆盖统计
            if '重叠覆盖采样点比例(%)' in 数据.columns:
                结果[制式]['平均重叠覆盖'] = 数据['重叠覆盖采样点比例(%)'].mean()
                结果[制式]['重叠覆盖标准差'] = 数据['重叠覆盖采样点比例(%)'].std()
        return 结果

    def 按覆盖区域分组统计(self) -> Dict:
        """按覆盖区域（城市/农村/县城）分组统计"""
        if '覆盖区域' not in self.清洗后数据.columns:
            return {}
        结果 = {}
        for 区域 in self.清洗后数据['覆盖区域'].unique():
            区域数据 = self.清洗后数据[self.清洗后数据['覆盖区域'] == 区域]
            结果[区域] = {
                '数据量': len(区域数据),
                '平均CQI': 区域数据['CQI优良率'].mean(),
                'CQI标准差': 区域数据['CQI优良率'].std(),
                '平均下行速率': 区域数据['下行用户平均速率(MBPS)'].mean(),
                '平均上行速率': 区域数据['上行用户平均速率(MBPS)'].mean(),
                '平均重叠覆盖': 区域数据['重叠覆盖采样点比例(%)'].mean() if '重叠覆盖采样点比例(%)' in 区域数据.columns else None,
                '平均覆盖系数': 区域数据['覆盖系数'].mean() if '覆盖系数' in 区域数据.columns else None
            }
        return 结果

    def 按制式和覆盖区域分组统计(self) -> Dict:
        """按网络制式和覆盖区域交叉分组统计"""
        if '覆盖区域' not in self.清洗后数据.columns or '网络制式' not in self.清洗后数据.columns:
            return {}
        
        结果 = {}
        分组数据 = self.按网络制式分组()
        
        for 制式, 制式数据 in 分组数据.items():
            结果[制式] = {}
            for 区域 in 制式数据['覆盖区域'].unique():
                区域数据 = 制式数据[制式数据['覆盖区域'] == 区域]
                结果[制式][区域] = {
                    '数据量': len(区域数据),
                    '平均CQI': 区域数据['CQI优良率'].mean(),
                    '平均下行速率': 区域数据['下行用户平均速率(MBPS)'].mean(),
                    '平均上行速率': 区域数据['上行用户平均速率(MBPS)'].mean(),
                    '平均重叠覆盖': 区域数据['重叠覆盖采样点比例(%)'].mean() if '重叠覆盖采样点比例(%)' in 区域数据.columns else None,
                    '平均覆盖系数': 区域数据['覆盖系数'].mean() if '覆盖系数' in 区域数据.columns else None
                }
        return 结果

    def CQI速率拐点分析_按制式(self, 分段数: int = 10) -> Dict:
        """分析CQI与速率关系的拐点
        
        思路：
        1. 将CQI优良率划分为多个区间（如每5%或10%一个区间）
        2. 计算每个区间的平均速率
        3. 找出速率增长斜率变化最大的点（拐点）
        4. 拐点代表：超过此CQI值后，速率提升效果开始显著变化
        
        返回：每个制式的区间分析和拐点信息
        """
        分组数据 = self.按网络制式分组()
        结果 = {}
        
        for 制式, 数据 in 分组数据.items():
            if len(数据) < 分段数 * 5:  # 确保每个区间有足够样本
                continue
                
            # 将CQI优良率划分为等频区间（保证每个区间样本量均衡）
            try:
                数据['CQI区间'] = pd.qcut(数据['CQI优良率'], q=分段数, duplicates='drop')
            except:
                continue
            
            # 计算每个区间的统计信息
            区间统计 = 数据.groupby('CQI区间').agg({
                'CQI优良率': ['mean', 'min', 'max', 'count'],
                '下行用户平均速率(MBPS)': ['mean', 'std'],
                '小区MR覆盖平均电平': 'mean',
                '小区MR覆盖平均SINR': 'mean'
            }).reset_index()
            
            # 展平列名
            区间统计.columns = ['CQI区间', 'CQI均值', 'CQI最小值', 'CQI最大值', '样本数', 
                             '平均速率', '速率标准差', '平均覆盖电平', '平均SINR']
            
            # 计算速率增长率（相对于前一个区间）
            区间统计['速率增长(Mbps)'] = 区间统计['平均速率'].diff()
            区间统计['速率增长率(%)'] = (区间统计['平均速率'].pct_change() * 100)
            
            # 找出拐点：速率增长斜率变化最大的点
            if len(区间统计) > 2:
                # 计算二阶导数（斜率变化）
                区间统计['斜率变化'] = 区间统计['速率增长(Mbps)'].diff()
                # 拐点：斜率变化最大的正向点
                拐点索引 = 区间统计['斜率变化'].idxmax()
                拐点数据 = 区间统计.loc[拐点索引]
                
                # 标记拐点
                区间统计['是否拐点'] = False
                区间统计.loc[拐点索引, '是否拐点'] = True
            else:
                拐点数据 = None
            
            # 找出关键阈值点
            # 1. 速率提升开始显著的点（增长率>10%）
            显著提升点 = 区间统计[区间统计['速率增长率(%)'] > 10]
            
            # 2. 速率趋于平稳的点（增长率<5%）
            平稳点 = 区间统计[区间统计['速率增长率(%)'] < 5]
            
            结果[制式] = {
                '区间统计': 区间统计,
                '拐点': 拐点数据,
                '显著提升点': 显著提升点,
                '平稳点': 平稳点
            }
        
        return 结果

    def 贡献度分析_按制式(self) -> Dict:
        """按网络制式分析各指标对CQI的贡献度"""
        影响指标 = [
            '小区MR覆盖平均电平',
            '小区MR覆盖平均SINR',
            '小区MR覆盖平均TA',
            '小区上行平均干扰电平',
            '上行PRB平均利用率',
            '下行PRB平均利用率',
            '覆盖系数',  # ⭐新增
            '重叠覆盖采样点比例(%)'  # ⭐新增
        ]
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            贡献度列表 = []
            for 指标 in 影响指标:
                if 指标 in 数据.columns:
                    # 删除包含NaN的行
                    有效数据 = 数据[[指标, 'CQI优良率']].dropna()
                    
                    # 检查有效数据量是否足够
                    if len(有效数据) < 3:
                        贡献度列表.append({
                            '指标': 指标,
                            '相关系数': None,
                            '贡献度(%)': 0
                        })
                        continue
                    
                    try:
                        相关系数, _ = stats.pearsonr(有效数据[指标], 有效数据['CQI优良率'])
                        贡献度 = abs(相关系数) * 100
                        贡献度列表.append({
                            '指标': 指标,
                            '相关系数': 相关系数,
                            '贡献度(%)': 贡献度
                        })
                    except Exception:
                        贡献度列表.append({
                            '指标': 指标,
                            '相关系数': None,
                            '贡献度(%)': 0
                        })
            
            # 过滤掉贡献度为0的项再排序
            贡献度列表 = [x for x in 贡献度列表 if x['贡献度(%)'] > 0]
            贡献度列表.sort(key=lambda x: x['贡献度(%)'], reverse=True)
            
            总贡献度 = sum(x['贡献度(%)'] for x in 贡献度列表)
            累积贡献度 = 0
            for 项 in 贡献度列表:
                累积贡献度 += 项['贡献度(%)']
                项['累积贡献度(%)'] = 累积贡献度 / 总贡献度 * 100 if 总贡献度 > 0 else 0
            结果[制式] = {'贡献度列表': 贡献度列表, '总贡献度': 总贡献度}
        return 结果

    def 按CQI分组分析_按制式(self, 分组数: int = 5) -> Dict:
        """按网络制式进行CQI分组分析"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            分组标签 = [f'第{i+1}组' for i in range(分组数)]
            数据副本 = 数据.copy()
            数据副本['CQI分组'] = pd.qcut(数据副本['CQI优良率'], q=分组数, labels=分组标签, duplicates='drop')
            分析列 = [
                '下行用户平均速率(MBPS)',
                '上行用户平均速率(MBPS)',
                '小区MR覆盖平均电平',
                '小区MR覆盖平均SINR',
                '小区MR覆盖平均TA',
                '小区上行平均干扰电平'
            ]
            # 动态添加可选列（如果数据中存在）
            if '覆盖系数' in 数据副本.columns:
                分析列.append('覆盖系数')
            if '重叠覆盖采样点比例(%)' in 数据副本.columns:
                分析列.append('重叠覆盖采样点比例(%)')
            结果[制式] = 数据副本.groupby('CQI分组')[分析列].agg(['mean', 'std', 'count'])
        return 结果

    # ==================== 多维度交叉分析方法 ====================
    
    def 三维散点图分析_按制式(self) -> Dict:
        """三维散点图分析：覆盖×SINR×CQI/速率"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            # 准备三维数据
            三维数据 = 数据[['小区MR覆盖平均电平', '小区MR覆盖平均SINR', 'CQI优良率', 
                           '下行用户平均速率(MBPS)', '上行用户平均速率(MBPS)']].dropna()
            结果[制式] = 三维数据
        return 结果
    
    def 四象限分析_按制式(self, 覆盖阈值: float = -90, SINR阈值: float = 15) -> Dict:
        """四象限分析：覆盖×SINR矩阵"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            象限统计 = []
            
            # 定义四个象限
            # 覆盖电平是负数，数值越大（越接近0）信号越好
            # 好覆盖 = 覆盖电平 > 阈值（信号强）
            # 差覆盖 = 覆盖电平 <= 阈值（信号弱）
            象限定义 = [
                ('象限1: 好覆盖+好SINR', 覆盖阈值, float('inf'), SINR阈值, float('inf')),
                ('象限2: 差覆盖+好SINR', -float('inf'), 覆盖阈值, SINR阈值, float('inf')),
                ('象限3: 好覆盖+差SINR', 覆盖阈值, float('inf'), -float('inf'), SINR阈值),
                ('象限4: 差覆盖+差SINR', -float('inf'), 覆盖阈值, -float('inf'), SINR阈值)
            ]
            
            for 象限名, 覆盖下限, 覆盖上限, SINR下限, SINR上限 in 象限定义:
                象限数据 = 数据[
                    (数据['小区MR覆盖平均电平'] > 覆盖下限) & 
                    (数据['小区MR覆盖平均电平'] <= 覆盖上限) &
                    (数据['小区MR覆盖平均SINR'] > SINR下限) & 
                    (数据['小区MR覆盖平均SINR'] <= SINR上限)
                ]
                
                if len(象限数据) > 0:
                    象限统计.append({
                        '象限': 象限名,
                        '样本数': len(象限数据),
                        '占比(%)': len(象限数据) / len(数据) * 100,
                        '平均CQI': 象限数据['CQI优良率'].mean(),
                        '平均下行速率': 象限数据['下行用户平均速率(MBPS)'].mean(),
                        '平均覆盖电平': 象限数据['小区MR覆盖平均电平'].mean(),
                        '平均SINR': 象限数据['小区MR覆盖平均SINR'].mean()
                    })
            
            结果[制式] = pd.DataFrame(象限统计)
        return 结果
    
    def CQI不达标根因分析_按制式(self, CQI阈值: Dict = None) -> Dict:
        """CQI不达标根因分析 - 支持分制式设置阈值"""
        if CQI阈值 is None:
            CQI阈值 = {'n41': 85, 'n28': 85}  # 默认阈值
        
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            # 获取该制式的阈值，默认为85
            阈值 = CQI阈值.get(制式, 85)
            
            # 筛选CQI不达标的小区
            不达标数据 = 数据[数据['CQI优良率'] < 阈值]
            达标数据 = 数据[数据['CQI优良率'] >= 阈值]
            
            if len(不达标数据) == 0:
                结果[制式] = {'根因统计': pd.DataFrame(), '不达标比例': 0, 'CQI阈值': 阈值}
                continue
            
            # 根因分类
            根因统计 = []
            
            # 1. 覆盖问题（覆盖电平 < -95dBm）
            覆盖问题数 = len(不达标数据[不达标数据['小区MR覆盖平均电平'] < -95])
            
            # 2. 干扰问题（SINR < 10）
            干扰问题数 = len(不达标数据[不达标数据['小区MR覆盖平均SINR'] < 10])
            
            # 3. ⭐ 修改为：越区覆盖问题（覆盖系数 > 0.65）
            越区覆盖问题数 = 0
            if '覆盖系数' in 不达标数据.columns:
                越区覆盖问题数 = len(不达标数据[不达标数据['覆盖系数'] > 0.65])
            
            # 4. 综合问题（覆盖差 + 干扰高）
            综合问题数 = len(不达标数据[
                (不达标数据['小区MR覆盖平均电平'] < -95) & 
                (不达标数据['小区MR覆盖平均SINR'] < 10)
            ])
            
            # 5. ⭐ 修改为：重叠覆盖问题（重叠覆盖采样点比例 ≥ 15%，高干扰）
            重叠覆盖问题数 = 0
            if '重叠覆盖采样点比例(%)' in 不达标数据.columns:
                重叠覆盖问题数 = len(不达标数据[不达标数据['重叠覆盖采样点比例(%)'] >= 15])
            
            根因统计 = [
                {'根因类型': '覆盖问题(电平<-95dBm)', '小区数': 覆盖问题数, 
                 '占比(%)': 覆盖问题数/len(不达标数据)*100},
                {'根因类型': '干扰问题(SINR<10)', '小区数': 干扰问题数, 
                 '占比(%)': 干扰问题数/len(不达标数据)*100},
                {'根因类型': '越区覆盖(覆盖系数>0.65)', '小区数': 越区覆盖问题数, 
                 '占比(%)': 越区覆盖问题数/len(不达标数据)*100},
                {'根因类型': '覆盖+干扰综合问题', '小区数': 综合问题数, 
                 '占比(%)': 综合问题数/len(不达标数据)*100},
                {'根因类型': '重叠覆盖问题(比例≥15%)', '小区数': 重叠覆盖问题数, 
                 '占比(%)': 重叠覆盖问题数/len(不达标数据)*100}
            ]
            
            不达标比例 = len(不达标数据) / len(数据) * 100
            
            结果[制式] = {
                '根因统计': pd.DataFrame(根因统计),
                '不达标比例': 不达标比例,
                '不达标小区数': len(不达标数据),
                '总小区数': len(数据),
                'CQI阈值': 阈值
            }
        return 结果

    # ==================== 覆盖系数相关分析方法 ====================
    
    def 覆盖系数统计_按制式(self) -> Dict:
        """按网络制式统计覆盖系数分布"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            if '覆盖系数' not in 数据.columns:
                continue
                
            覆盖系数数据 = 数据['覆盖系数'].dropna()
            
            # 覆盖系数分级（调整为3档）
            覆盖近 = len(覆盖系数数据[覆盖系数数据 < 0.3])
            覆盖适中 = len(覆盖系数数据[(覆盖系数数据 >= 0.3) & (覆盖系数数据 <= 0.65)])
            越区覆盖 = len(覆盖系数数据[覆盖系数数据 > 0.65])
            
            结果[制式] = {
                '样本数': len(覆盖系数数据),
                '平均值': 覆盖系数数据.mean(),
                '标准差': 覆盖系数数据.std(),
                '最小值': 覆盖系数数据.min(),
                '最大值': 覆盖系数数据.max(),
                '中位数': 覆盖系数数据.median(),
                '覆盖较近(<0.3)': 覆盖近,
                '覆盖适中(0.3-0.65)': 覆盖适中,
                '越区覆盖(>0.65)': 越区覆盖,
                '覆盖系数数据': 覆盖系数数据
            }
        return 结果
    
    def 覆盖系数与CQI相关性_按制式(self) -> Dict:
        """分析覆盖系数与CQI及其他指标的相关性"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            if '覆盖系数' not in 数据.columns:
                continue
                
            分析指标 = ['CQI优良率', '下行用户平均速率(MBPS)', '上行用户平均速率(MBPS)',
                      '小区MR覆盖平均电平', '小区MR覆盖平均SINR']
            
            相关性列表 = []
            for 指标 in 分析指标:
                if 指标 in 数据.columns:
                    有效数据 = 数据[['覆盖系数', 指标]].dropna()
                    if len(有效数据) > 10:
                        相关系数, p值 = stats.pearsonr(有效数据['覆盖系数'], 有效数据[指标])
                        相关性列表.append({
                            '指标': 指标,
                            '相关系数': 相关系数,
                            'P值': p值,
                            '显著性': '显著' if p值 < 0.05 else '不显著',
                            '强度': self.判断相关性强度(abs(相关系数))
                        })
            
            结果[制式] = sorted(相关性列表, key=lambda x: abs(x['相关系数']), reverse=True)
        return 结果
    
    def 多维度分层分析_按制式(self, 维度: str = '覆盖系数', 分档阈值: List[float] = None) -> Dict:
        """通用多维度分层分析 - 支持覆盖系数、TA、覆盖电平分档
        
        参数:
            维度: '覆盖系数' | 'TA' | '覆盖电平'
            分档阈值: 分档阈值列表，None则使用默认值
        """
        分组数据 = self.按网络制式分组()
        结果 = {}
        
        for 制式, 数据 in 分组数据.items():
            分档结果 = []
            
            if 维度 == '覆盖系数':
                if '覆盖系数' not in 数据.columns:
                    continue
                字段名 = '覆盖系数'
                阈值 = 分档阈值 if 分档阈值 else [0.3, 0.7, 1.0, 2.0]
                档位定义 = [
                    ('近覆盖(<0.3)', 0, 阈值[0]),
                    ('适中覆盖(0.3-0.7)', 阈值[0], 阈值[1]),
                    ('较远覆盖(0.7-1.0)', 阈值[1], 阈值[2]),
                    ('轻微越区(1.0-2.0)', 阈值[2], 阈值[3]),
                    ('严重越区(>2.0)', 阈值[3], float('inf'))
                ]
                
            elif 维度 == 'TA':
                if '小区MR覆盖平均TA' not in 数据.columns:
                    continue
                字段名 = '小区MR覆盖平均TA'
                阈值 = 分档阈值 if 分档阈值 else [300, 600, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
                档位定义 = [
                    ('0-300米', 0, 阈值[0]),
                    ('300-600米', 阈值[0], 阈值[1]),
                    ('600-1000米', 阈值[1], 阈值[2]),
                    ('1000-1500米', 阈值[2], 阈值[3]),
                    ('1500-2000米', 阈值[3], 阈值[4]),
                    ('2000-2500米', 阈值[4], 阈值[5]),
                    ('2500-3000米', 阈值[5], 阈值[6]),
                    ('3000-3500米', 阈值[6], 阈值[7]),
                    ('3500-4000米', 阈值[7], 阈值[8]),
                    ('4000米以上', 阈值[8], float('inf'))
                ]
                
            elif 维度 == '覆盖电平':
                if '小区MR覆盖平均电平' not in 数据.columns:
                    continue
                字段名 = '小区MR覆盖平均电平'
                阈值 = 分档阈值 if 分档阈值 else [-95, -85]
                档位定义 = [
                    ('弱覆盖(<-95dBm)', -float('inf'), 阈值[0]),
                    ('中等覆盖(-95~-85dBm)', 阈值[0], 阈值[1]),
                    ('好覆盖(>-85dBm)', 阈值[1], float('inf'))
                ]
            else:
                continue
            
            # 执行分档统计
            for 档位名, 下限, 上限 in 档位定义:
                档位数据 = 数据[(数据[字段名] > 下限) & (数据[字段名] <= 上限)]
                if len(档位数据) > 5:
                    行 = {
                        '档位': 档位名,
                        '样本数': len(档位数据),
                        '平均CQI': 档位数据['CQI优良率'].mean(),
                        '平均下行速率': 档位数据['下行用户平均速率(MBPS)'].mean(),
                        '平均上行速率': 档位数据['上行用户平均速率(MBPS)'].mean(),
                        '平均覆盖电平': 档位数据['小区MR覆盖平均电平'].mean(),
                        '平均SINR': 档位数据['小区MR覆盖平均SINR'].mean()
                    }
                    
                    # 维度特定统计
                    if 维度 == '覆盖系数':
                        行['平均TA'] = 档位数据['小区MR覆盖平均TA'].mean()
                        # ⭐ 新增：计算覆盖和SINR与CQI的相关性
                        行['覆盖_CQI相关性'] = self._计算相关性(档位数据, '小区MR覆盖平均电平', 'CQI优良率')
                        行['SINR_CQI相关性'] = self._计算相关性(档位数据, '小区MR覆盖平均SINR', 'CQI优良率')
                    elif 维度 == 'TA':
                        行['覆盖_CQI相关性'] = self._计算相关性(档位数据, '小区MR覆盖平均电平', 'CQI优良率')
                        行['SINR_CQI相关性'] = self._计算相关性(档位数据, '小区MR覆盖平均SINR', 'CQI优良率')
                    elif 维度 == '覆盖电平':
                        行['SINR_CQI相关系数'] = self._计算相关性(档位数据, '小区MR覆盖平均SINR', 'CQI优良率')
                    
                    分档结果.append(行)
            
            结果[制式] = pd.DataFrame(分档结果)
        
        return 结果
    
    def _计算相关性(self, 数据: pd.DataFrame, 字段1: str, 字段2: str) -> float:
        """辅助方法：计算两个字段的相关系数"""
        try:
            有效数据 = 数据[[字段1, 字段2]].dropna()
            if len(有效数据) > 10:
                corr, _ = stats.pearsonr(有效数据[字段1], 有效数据[字段2])
                return corr
        except Exception:
            pass
        return None
    
    def 覆盖系数四象限分析_按制式(self, 覆盖系数阈值: float = 0.7, 覆盖电平阈值: float = -90) -> Dict:
        """四象限分析：覆盖系数×覆盖电平矩阵"""
        分组数据 = self.按网络制式分组()
        结果 = {}
        for 制式, 数据 in 分组数据.items():
            if '覆盖系数' not in 数据.columns:
                continue
                
            象限统计 = []
            
            # 定义四个象限
            象限定义 = [
                ('象限1: 好覆盖+合理覆盖距离', 覆盖电平阈值, float('inf'), 0, 覆盖系数阈值),
                ('象限2: 差覆盖+合理覆盖距离', -float('inf'), 覆盖电平阈值, 0, 覆盖系数阈值),
                ('象限3: 好覆盖+过远覆盖距离', 覆盖电平阈值, float('inf'), 覆盖系数阈值, float('inf')),
                ('象限4: 差覆盖+过远覆盖距离', -float('inf'), 覆盖电平阈值, 覆盖系数阈值, float('inf'))
            ]
            
            for 象限名, 电平下限, 电平上限, 系数下限, 系数上限 in 象限定义:
                象限数据 = 数据[
                    (数据['小区MR覆盖平均电平'] > 电平下限) & 
                    (数据['小区MR覆盖平均电平'] <= 电平上限) &
                    (数据['覆盖系数'] > 系数下限) & 
                    (数据['覆盖系数'] <= 系数上限)
                ]
                
                if len(象限数据) > 0:
                    象限统计.append({
                        '象限': 象限名,
                        '样本数': len(象限数据),
                        '占比(%)': len(象限数据) / len(数据) * 100,
                        '平均CQI': 象限数据['CQI优良率'].mean(),
                        '平均下行速率': 象限数据['下行用户平均速率(MBPS)'].mean(),
                        '平均覆盖电平': 象限数据['小区MR覆盖平均电平'].mean(),
                        '平均覆盖系数': 象限数据['覆盖系数'].mean(),
                        '平均SINR': 象限数据['小区MR覆盖平均SINR'].mean()
                    })
            
            结果[制式] = pd.DataFrame(象限统计)
        return 结果


def 生成综合报告(分析器: CQI分析器) -> str:
    """生成综合分析报告，汇总各页面关键洞察"""
    from datetime import datetime
    
    报告 = []
    报告.append("=" * 60)
    报告.append("📊 5G CQI关联性能分析 - 综合报告")
    报告.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    报告.append("=" * 60)
    报告.append("")
    
    # 1. 概览统计
    统计摘要 = 分析器.获取统计摘要_按制式()
    if 'n41' in 统计摘要 and 'n28' in 统计摘要:
        n41 = 统计摘要['n41']
        n28 = 统计摘要['n28']
        报告.append("【一、概览对比】")
        报告.append(f"  N41: CQI优良率 {n41['平均CQI']:.2f}%, 下行速率 {n41['平均下行速率']:.2f} Mbps, 小区数 {n41['数据量']:,}")
        报告.append(f"  N28: CQI优良率 {n28['平均CQI']:.2f}%, 下行速率 {n28['平均下行速率']:.2f} Mbps, 小区数 {n28['数据量']:,}")
        报告.append(f"  CQI差异: {abs(n41['平均CQI'] - n28['平均CQI']):.2f}% ({'N41更优' if n41['平均CQI'] > n28['平均CQI'] else 'N28更优'})")
        报告.append("")
    
    # 2. 相关性分析 - 影响CQI的主要因素
    try:
        影响结果 = 分析器.分析影响CQI的指标_按制式()
        报告.append("【二、影响CQI的主要因素】")
        for 制式 in ['n41', 'n28']:
            if 制式 in 影响结果:
                有效因素 = [x for x in 影响结果[制式] if x['相关系数'] is not None][:3]
                if 有效因素:
                    报告.append(f"  {制式.upper()} TOP3:")
                    for i, f in enumerate(有效因素, 1):
                        报告.append(f"    {i}. {f['指标']}: r={f['相关系数']:.3f} ({f['显著性']})")
        报告.append("")
    except:
        pass
    
    # 3. 贡献度分析
    try:
        贡献度结果 = 分析器.贡献度分析_按制式()
        报告.append("【三、指标贡献度排名】")
        for 制式 in ['n41', 'n28']:
            if 制式 in 贡献度结果 and len(贡献度结果[制式]['贡献度列表']) > 0:
                top3 = 贡献度结果[制式]['贡献度列表'][:3]
                报告.append(f"  {制式.upper()}:")
                for i, item in enumerate(top3, 1):
                    报告.append(f"    {i}. {item['指标']}: {item['贡献度(%)']:.1f}% (累积: {item['累积贡献度(%)']:.1f}%)")
        报告.append("")
    except:
        pass
    
    # 4. 覆盖系数分析
    try:
        覆盖系数统计 = 分析器.覆盖系数统计_按制式()
        if len(覆盖系数统计) > 0:
            报告.append("【四、覆盖系数分析】")
            for 制式 in ['n41', 'n28']:
                if 制式 in 覆盖系数统计:
                    数据 = 覆盖系数统计[制式]
                    越区占比 = 数据['越区覆盖(>0.65)'] / 数据['样本数'] * 100
                    报告.append(f"  {制式.upper()}: 均值={数据['平均值']:.3f}, 越区覆盖占比={越区占比:.1f}%")
            报告.append("")
    except:
        pass
    
    # 5. 四象限分析洞察
    try:
        四象限结果 = 分析器.四象限分析_按制式(-90, 15)
        if len(四象限结果) > 0:
            报告.append("【五、四象限分析（覆盖×SINR）】")
            for 制式 in ['n41', 'n28']:
                if 制式 in 四象限结果 and len(四象限结果[制式]) > 0:
                    # 找出占比最大的象限
                    最大象限 = 四象限结果[制式].loc[四象限结果[制式]['占比(%)'].idxmax()]
                    报告.append(f"  {制式.upper()}: 主要问题区域为'{最大象限['象限']}'，占比{最大象限['占比(%)']:.1f}%，平均CQI={最大象限['平均CQI']:.2f}%")
            报告.append("")
    except:
        pass
    
    # 6. 优化建议
    报告.append("【六、优化建议摘要】")
    if 'n41' in 统计摘要 and 'n28' in 统计摘要:
        n41 = 统计摘要['n41']
        n28 = 统计摘要['n28']
        if n41['平均CQI'] > n28['平均CQI']:
            报告.append("  • N28的CQI表现相对较差，建议优先优化N28网络")
        else:
            报告.append("  • N41的CQI表现相对较差，建议优先优化N41网络")
        报告.append("  • 关注贡献度最高的指标，集中资源进行针对性优化")
        报告.append("  • 结合四象限分析，优先处理'差覆盖+差SINR'区域")
    
    报告.append("")
    报告.append("=" * 60)
    报告.append("报告生成完成 | 详细分析请查看各标签页")
    报告.append("=" * 60)
    
    return "\n".join(报告)


def 渲染制式对比概览(分析器: CQI分析器):
    """渲染概览页面的网络制式对比"""
    st.markdown("""
    <div class="highlight">
    <b>🏠 数据概览说明：</b><br>
    对比N41和N28两种网络制式的整体性能表现，提供快速了解网络现状的入口。<br><br>
    <b>📊 展示内容：</b><br>
    • <b>关键指标对比</b>：样本数、CQI优良率、上下行速率等核心KPI<br>
    • <b>覆盖区域分析</b>：按城市/农村/县城维度对比网络质量<br>
    • <b>CQI分布</b>：CQI优良率的分布直方图对比<br>
    • <b>综合报告</b>：一键生成包含全部分析内容的综合报告<br>
    <br>
    <b>💡 使用建议：</b>先通过概览页面了解整体情况，再深入具体标签页进行详细分析
    </div>
    """, unsafe_allow_html=True)
    
    统计摘要 = 分析器.获取统计摘要_按制式()

    # 检查是否有网络制式分组
    if len(统计摘要) == 1 and '全部' in 统计摘要:
        st.warning("⚠️ 数据中未找到'网络制式'列，无法进行对比分析")
        return
    
    # ⭐ 新增：一键生成综合报告按钮
    col_title, col_button = st.columns([3, 1])
    with col_title:
        st.markdown('<p class="sub-header">📈 关键指标对比</p>', unsafe_allow_html=True)
    with col_button:
        if st.button("📋 一键生成综合报告", type="primary", use_container_width=True):
            with st.spinner('正在生成综合报告...'):
                综合报告 = 生成综合报告(分析器)
                st.session_state['综合报告'] = 综合报告
                st.success("✅ 综合报告已生成！")
    
    # 显示综合报告（如果有）
    if '综合报告' in st.session_state:
        with st.expander("📋 查看综合报告", expanded=True):
            st.text_area("综合报告内容", st.session_state['综合报告'], height=500)
            
            # 下载按钮
            st.download_button(
                label="📥 下载报告(.txt)",
                data=st.session_state['综合报告'],
                file_name=f"CQI综合报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        st.markdown("---")

    # 左右对比布局
    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])

    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 网络制式</div>', unsafe_allow_html=True)
        if 'n41' in 统计摘要:
            数据 = 统计摘要['n41']
            st.metric("数据量", f"{数据['数据量']:,}")
            st.metric("平均CQI优良率", f"{数据['平均CQI']:.2f}%", f"±{数据['CQI标准差']:.2f}")
            st.metric("平均下行速率", f"{数据['平均下行速率']:.2f} Mbps", f"±{数据['下行速率标准差']:.2f}")
            st.metric("平均上行速率", f"{数据['平均上行速率']:.2f} Mbps", f"±{数据['上行速率标准差']:.2f}")
            # ⭐ 新增：覆盖系数和重叠覆盖
            if '平均覆盖系数' in 数据:
                st.metric("平均覆盖系数", f"{数据['平均覆盖系数']:.3f}", f"±{数据['覆盖系数标准差']:.3f}")
            if '平均重叠覆盖' in 数据:
                st.metric("平均重叠覆盖", f"{数据['平均重叠覆盖']:.2f}%", f"±{数据['重叠覆盖标准差']:.2f}")

    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 网络制式</div>', unsafe_allow_html=True)
        if 'n28' in 统计摘要:
            数据 = 统计摘要['n28']
            st.metric("数据量", f"{数据['数据量']:,}")
            st.metric("平均CQI优良率", f"{数据['平均CQI']:.2f}%", f"±{数据['CQI标准差']:.2f}")
            st.metric("平均下行速率", f"{数据['平均下行速率']:.2f} Mbps", f"±{数据['下行速率标准差']:.2f}")
            st.metric("平均上行速率", f"{数据['平均上行速率']:.2f} Mbps", f"±{数据['上行速率标准差']:.2f}")
            # ⭐ 新增：覆盖系数和重叠覆盖
            if '平均覆盖系数' in 数据:
                st.metric("平均覆盖系数", f"{数据['平均覆盖系数']:.3f}", f"±{数据['覆盖系数标准差']:.3f}")
            if '平均重叠覆盖' in 数据:
                st.metric("平均重叠覆盖", f"{数据['平均重叠覆盖']:.2f}%", f"±{数据['重叠覆盖标准差']:.2f}")

    # 标准差说明
    st.markdown("""
    <div style="background-color: #e8f4f8; padding: 12px 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #17a2b8;">
        <b>📊 关于"±数值"的说明（离散程度/标准差）：</b><br><br>
        指标卡片中显示的 <b>"↗ ±X.XX"</b> 表示该指标的<b>标准差</b>，反映数据的离散程度（波动范围）。<br><br>
        <b>• 标准差小</b>（如N41的±4.11）：数据集中在平均值附近，网络质量<b>稳定均匀</b><br>
        <b>• 标准差大</b>（如N28的±7.70）：数据分散，有的很高有的很低，网络质量<b>参差不齐</b><br><br>
        <b>实际意义</b>：N28的标准差大于N41，说明N28网络中小区性能差异大，存在"好区"和"差区"的明显分化，需要重点优化性能较差的小区以提升整体均匀性。
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ⭐ 新增：覆盖区域分类分析（按制式分开展示）
    st.markdown('<p class="sub-header">📍 覆盖区域分类分析（城市/农村/县城）- 按网络制式</p>', unsafe_allow_html=True)
    
    区域统计 = 分析器.按制式和覆盖区域分组统计()
    if 区域统计:
        col_n41_area, col_n28_area = st.columns(2)
        
        with col_n41_area:
            st.markdown('<div class="network-type-header n41-header">📡 N41 - 覆盖区域分布</div>', unsafe_allow_html=True)
            if 'n41' in 区域统计:
                # 创建N41区域数据表
                n41区域数据 = []
                for 区域, 统计 in 区域统计['n41'].items():
                    n41区域数据.append({
                        '覆盖区域': 区域,
                        '小区数': f"{统计['数据量']:,}",
                        'CQI': f"{统计['平均CQI']:.2f}%",
                        '下行速率': f"{统计['平均下行速率']:.2f}",
                        '上行速率': f"{统计['平均上行速率']:.2f}",
                        '重叠覆盖': f"{统计['平均重叠覆盖']:.2f}%" if 统计['平均重叠覆盖'] is not None else '-',
                        '覆盖系数': f"{统计['平均覆盖系数']:.3f}" if 统计['平均覆盖系数'] is not None else '-'
                    })
                n41区域df = pd.DataFrame(n41区域数据)
                st.dataframe(n41区域df, use_container_width=True, hide_index=True)
                
                # N41各区域CQI对比柱状图
                fig_n41_bar = px.bar(
                    n41区域df, x='覆盖区域', y=[float(x.replace('%', '')) for x in n41区域df['CQI']],
                    title="N41各区域CQI优良率对比",
                    labels={'y': 'CQI优良率(%)'},
                    color='覆盖区域',
                    color_discrete_sequence=['#1E90FF', '#4169E1', '#6495ED']
                )
                fig_n41_bar.update_layout(template="plotly_white", height=300, showlegend=False)
                st.plotly_chart(fig_n41_bar, use_container_width=True)
            else:
                st.info("N41无覆盖区域数据")
        
        with col_n28_area:
            st.markdown('<div class="network-type-header n28-header">📡 N28 - 覆盖区域分布</div>', unsafe_allow_html=True)
            if 'n28' in 区域统计:
                # 创建N28区域数据表
                n28区域数据 = []
                for 区域, 统计 in 区域统计['n28'].items():
                    n28区域数据.append({
                        '覆盖区域': 区域,
                        '小区数': f"{统计['数据量']:,}",
                        'CQI': f"{统计['平均CQI']:.2f}%",
                        '下行速率': f"{统计['平均下行速率']:.2f}",
                        '上行速率': f"{统计['平均上行速率']:.2f}",
                        '重叠覆盖': f"{统计['平均重叠覆盖']:.2f}%" if 统计['平均重叠覆盖'] is not None else '-',
                        '覆盖系数': f"{统计['平均覆盖系数']:.3f}" if 统计['平均覆盖系数'] is not None else '-'
                    })
                n28区域df = pd.DataFrame(n28区域数据)
                st.dataframe(n28区域df, use_container_width=True, hide_index=True)
                
                # N28各区域CQI对比柱状图
                fig_n28_bar = px.bar(
                    n28区域df, x='覆盖区域', y=[float(x.replace('%', '')) for x in n28区域df['CQI']],
                    title="N28各区域CQI优良率对比",
                    labels={'y': 'CQI优良率(%)'},
                    color='覆盖区域',
                    color_discrete_sequence=['#FF6B6B', '#FF8E53', '#FFA07A']
                )
                fig_n28_bar.update_layout(template="plotly_white", height=300, showlegend=False)
                st.plotly_chart(fig_n28_bar, use_container_width=True)
            else:
                st.info("N28无覆盖区域数据")
    else:
        st.info("ℹ️ 数据中未找到'覆盖区域'列，无法进行分类分析")

    st.markdown("---")

    # CQI分布对比
    st.markdown('<p class="sub-header">📈 CQI优良率分布对比</p>', unsafe_allow_html=True)

    col_hist1, col_hist2 = st.columns(2)

    分组数据 = 分析器.按网络制式分组()

    with col_hist1:
        if 'n41' in 分组数据:
            fig_n41 = px.histogram(
                分组数据['n41'],
                x="CQI优良率",
                nbins=50,
                color_discrete_sequence=['#1E90FF'],
                title="N41 - CQI优良率分布"
            )
            fig_n41.update_layout(template="plotly_white", height=400)
            st.plotly_chart(fig_n41, use_container_width=True)

    with col_hist2:
        if 'n28' in 分组数据:
            fig_n28 = px.histogram(
                分组数据['n28'],
                x="CQI优良率",
                nbins=50,
                color_discrete_sequence=['#FF6B6B'],
                title="N28 - CQI优良率分布"
            )
            fig_n28.update_layout(template="plotly_white", height=400)
            st.plotly_chart(fig_n28, use_container_width=True)

    # 分析总结
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 分析总结</p>', unsafe_allow_html=True)

    if 'n41' in 统计摘要 and 'n28' in 统计摘要:
        n41 = 统计摘要['n41']
        n28 = 统计摘要['n28']

        cqi_diff = n41['平均CQI'] - n28['平均CQI']
        下行_diff = n41['平均下行速率'] - n28['平均下行速率']
        上行_diff = n41['平均上行速率'] - n28['平均上行速率']

        总结内容 = f"""
        <div class="highlight">
        <b>📊 概览分析总结</b><br><br>
        <b>1. CQI优良率对比：</b><br>
        • N41平均CQI优良率为 <b>{n41['平均CQI']:.2f}%</b>，N28为 <b>{n28['平均CQI']:.2f}%</b><br>
        • 两者差异：<b>{abs(cqi_diff):.2f}%</b>，{'N41优于N28' if cqi_diff > 0 else 'N28优于N41'}<br><br>

        <b>2. 下行速率对比：</b><br>
        • N41平均下行速率为 <b>{n41['平均下行速率']:.2f} Mbps</b>，N28为 <b>{n28['平均下行速率']:.2f} Mbps</b><br>
        • 两者差异：<b>{abs(下行_diff):.2f} Mbps</b>，{'N41优于N28' if 下行_diff > 0 else 'N28优于N41'}<br><br>

        <b>3. 上行速率对比：</b><br>
        • N41平均上行速率为 <b>{n41['平均上行速率']:.2f} Mbps</b>，N28为 <b>{n28['平均上行速率']:.2f} Mbps</b><br>
        • 两者差异：<b>{abs(上行_diff):.2f} Mbps</b>，{'N41优于N28' if 上行_diff > 0 else 'N28优于N41'}<br><br>

        <b>4. 整体评估：</b><br>
        • {'N41在各项指标上均优于N28，网络性能更优' if cqi_diff > 0 and 下行_diff > 0 and 上行_diff > 0 else 'N28在某些指标上表现更好，需要进一步分析优化'}<br>
        • N41数据量：{n41['数据量']:,}条，N28数据量：{n28['数据量']:,}条
        </div>
        """
        st.markdown(总结内容, unsafe_allow_html=True)


def 安全生成散点图(数据: pd.DataFrame, x轴: str, y轴: str, 颜色: str, 标题: str, 配色: str = "Blues") -> go.Figure:
    """安全生成散点图，处理可能的错误"""
    try:
        if 数据 is None or len(数据) == 0:
            return None
        # 检查必要的列是否存在
        必要列 = [x轴, y轴, 颜色]
        缺失列 = [列 for 列 in 必要列 if 列 not in 数据.columns]
        if 缺失列:
            return None

        # 确保数据类型正确
        temp_data = 数据[必要列].copy()
        for 列 in 必要列:
            temp_data[列] = pd.to_numeric(temp_data[列], errors='coerce')

        # 删除NaN
        temp_data = temp_data.dropna()
        if len(temp_data) == 0:
            return None

        # 采样
        样本数 = min(3000, len(temp_data))
        样本数据 = temp_data.sample(样本数) if 样本数 > 0 else temp_data

        # 计算轴范围（留10%边距）
        x_min, x_max = 样本数据[x轴].min(), 样本数据[x轴].max()
        y_min, y_max = 样本数据[y轴].min(), 样本数据[y轴].max()
        x_range = [x_min - (x_max - x_min) * 0.1, x_max + (x_max - x_min) * 0.1]
        y_range = [y_min - (y_max - y_min) * 0.1, y_max + (y_max - y_min) * 0.1]

        # 计算颜色范围
        color_min, color_max = 样本数据[颜色].min(), 样本数据[颜色].max()
        color_range = [color_min - (color_max - color_min) * 0.05, color_max + (color_max - color_min) * 0.05]

        fig = go.Figure()

        # 添加散点
        fig.add_trace(go.Scatter(
            x=样本数据[x轴],
            y=样本数据[y轴],
            mode='markers',
            marker=dict(
                size=6,
                color=样本数据[颜色],
                colorscale=配色,
                opacity=0.6,
                cmin=color_range[0],
                cmax=color_range[1],
                colorbar=dict(title=颜色, thickness=15)
            ),
            hovertemplate=f'{x轴}: %{{x:.2f}}<br>{y轴}: %{{y:.2f}}<br>{颜色}: %{{marker.color:.2f}}<extra></extra>'
        ))

        # 添加趋势线
        try:
            from scipy import stats
            valid_data = temp_data[[x轴, y轴]].dropna()
            if len(valid_data) > 2:
                slope, intercept, r_value, p_value, std_err = stats.linregress(valid_data[x轴], valid_data[y轴])
                x_line = np.array([valid_data[x轴].min(), valid_data[x轴].max()])
                y_line = slope * x_line + intercept
                fig.add_trace(go.Scatter(
                    x=x_line,
                    y=y_line,
                    mode='lines',
                    line=dict(color='red', width=2, dash='dash'),
                    name=f'趋势线 (R={r_value:.3f})',
                    hovertemplate=f'R²={r_value**2:.3f}<br>斜率={slope:.3f}<extra></extra>'
                ))
        except:
            pass

        fig.update_layout(
            title=dict(text=标题, font=dict(size=16)),
            template='plotly_white',
            height=420,
            margin=dict(l=60, r=30, t=50, b=50),
            xaxis=dict(
                title=x轴,
                range=x_range,
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            yaxis=dict(
                title=y轴,
                range=y_range,
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            hovermode='closest'
        )

        return fig
    except Exception as e:
        return None


def 渲染制式对比速率影响(分析器: CQI分析器):
    """渲染CQI对速率影响的网络制式对比"""
    速率影响 = 分析器.分析CQI对速率影响_按制式()

    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])

    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - CQI对速率影响</div>', unsafe_allow_html=True)
        if 'n41' in 速率影响:
            for 速率, 结果 in 速率影响['n41'].items():
                with st.container():
                    st.markdown(f"**{速率}**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("相关系数", f"{结果['相关系数']:.4f}")
                    with col_b:
                        st.metric("P值", f"{结果['P值']:.2e}", 结果['显著性'])
                    st.write(f"强度: {结果['强度']}")
                    st.markdown("---")

    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - CQI对速率影响</div>', unsafe_allow_html=True)
        if 'n28' in 速率影响:
            for 速率, 结果 in 速率影响['n28'].items():
                with st.container():
                    st.markdown(f"**{速率}**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("相关系数", f"{结果['相关系数']:.4f}")
                    with col_b:
                        st.metric("P值", f"{结果['P值']:.2e}", 结果['显著性'])
                    st.write(f"强度: {结果['强度']}")
                    st.markdown("---")

    # ========== 新增：CQI分位数速率分析 ==========
    st.markdown("---")
    st.markdown('<p class="sub-header">📊 CQI分位数速率分析</p>', unsafe_allow_html=True)
    st.info("💡 **说明**：将CQI按分位数（0-20%, 20-40%, 40-60%, 60-80%, 80-100%）分组，观察不同CQI区间的速率变化趋势")

    分位数数据 = 分析器.CQI分位数速率分析_按制式(分位数=5)

    if 分位数数据:
        col_n41_分位数, col_n28_分位数 = st.columns(2)
        
        with col_n41_分位数:
            if 'n41' in 分位数数据:
                st.markdown('<div class="network-type-header n41-header">📡 N41 - 分位数分析</div>', unsafe_allow_html=True)
                df_n41 = 分位数数据['n41']
                # 创建图表
                fig_n41 = go.Figure()
                fig_n41.add_trace(go.Scatter(
                    x=df_n41['CQI优良率'],
                    y=df_n41['下行用户平均速率(MBPS)'],
                    mode='lines+markers',
                    name='下行速率',
                    line=dict(color='blue', width=3),
                    marker=dict(size=10)
                ))
                fig_n41.add_trace(go.Scatter(
                    x=df_n41['CQI优良率'],
                    y=df_n41['上行用户平均速率(MBPS)'],
                    mode='lines+markers',
                    name='上行速率',
                    line=dict(color='orange', width=3),
                    marker=dict(size=10)
                ))
                fig_n41.update_layout(
                    title="N41 - CQI分位数 vs 速率趋势",
                    xaxis_title="CQI优良率 (%)",
                    yaxis_title="速率 (Mbps)",
                    template='plotly_white',
                    height=400,
                    hovermode='x unified'
                )
                st.plotly_chart(fig_n41, use_container_width=True)
                
                # 数据表
                with st.expander("查看详细数据"):
                    st.dataframe(df_n41, use_container_width=True)
            else:
                st.info("N41数据不可用")
        
        with col_n28_分位数:
            if 'n28' in 分位数数据:
                st.markdown('<div class="network-type-header n28-header">📡 N28 - 分位数分析</div>', unsafe_allow_html=True)
                df_n28 = 分位数数据['n28']
                # 创建图表
                fig_n28 = go.Figure()
                fig_n28.add_trace(go.Scatter(
                    x=df_n28['CQI优良率'],
                    y=df_n28['下行用户平均速率(MBPS)'],
                    mode='lines+markers',
                    name='下行速率',
                    line=dict(color='red', width=3),
                    marker=dict(size=10)
                ))
                fig_n28.add_trace(go.Scatter(
                    x=df_n28['CQI优良率'],
                    y=df_n28['上行用户平均速率(MBPS)'],
                    mode='lines+markers',
                    name='上行速率',
                    line=dict(color='green', width=3),
                    marker=dict(size=10)
                ))
                fig_n28.update_layout(
                    title="N28 - CQI分位数 vs 速率趋势",
                    xaxis_title="CQI优良率 (%)",
                    yaxis_title="速率 (Mbps)",
                    template='plotly_white',
                    height=400,
                    hovermode='x unified'
                )
                st.plotly_chart(fig_n28, use_container_width=True)
                
                # 数据表
                with st.expander("查看详细数据"):
                    st.dataframe(df_n28, use_container_width=True)
            else:
                st.info("N28数据不可用")

    # ========== 新增：速率分布对比分析 ==========
    st.markdown("---")
    st.markdown('<p class="sub-header">📈 不同CQI等级的速率分布</p>', unsafe_allow_html=True)
    st.info("💡 **说明**：按CQI等级（低<60%、中60-85%、高>85%）分组，对比不同等级的速率分布情况")

    分布数据 = 分析器.速率分布对比_按制式()

    if 分布数据:
        col_n41_分布, col_n28_分布 = st.columns(2)
        
        with col_n41_分布:
            if 'n41' in 分布数据:
                st.markdown('<div class="network-type-header n41-header">📡 N41 - 速率分布</div>', unsafe_allow_html=True)
                df_分布_n41 = 分布数据['n41']
                
                # 简化显示的数据表
                显示数据 = df_分布_n41[['CQI等级', '样本数', '下行均值', '下行最大值', '上行均值', '上行最大值']].copy()
                显示数据.columns = ['CQI等级', '样本数', '下行均值(Mbps)', '下行最大值(Mbps)', '上行均值(Mbps)', '上行最大值(Mbps)']
                st.dataframe(显示数据, use_container_width=True, hide_index=True)
                
                # 创建柱状图对比
                fig_分布_n41 = go.Figure()
                fig_分布_n41.add_trace(go.Bar(
                    x=df_分布_n41['CQI等级'],
                    y=df_分布_n41['下行均值'],
                    name='下行均值',
                    marker_color='blue',
                    error_y=dict(type='data', array=df_分布_n41['下行标准差'])
                ))
                fig_分布_n41.add_trace(go.Bar(
                    x=df_分布_n41['CQI等级'],
                    y=df_分布_n41['上行均值'],
                    name='上行均值',
                    marker_color='orange',
                    error_y=dict(type='data', array=df_分布_n41['上行标准差'])
                ))
                fig_分布_n41.update_layout(
                    title="N41 - 不同CQI等级的速率对比（误差线为标准差）",
                    barmode='group',
                    xaxis_title="CQI等级",
                    yaxis_title="速率 (Mbps)",
                    template='plotly_white',
                    height=400
                )
                st.plotly_chart(fig_分布_n41, use_container_width=True)
            else:
                st.info("N41数据不可用")
        
        with col_n28_分布:
            if 'n28' in 分布数据:
                st.markdown('<div class="network-type-header n28-header">📡 N28 - 速率分布</div>', unsafe_allow_html=True)
                df_分布_n28 = 分布数据['n28']
                
                # 简化显示的数据表
                显示数据 = df_分布_n28[['CQI等级', '样本数', '下行均值', '下行最大值', '上行均值', '上行最大值']].copy()
                显示数据.columns = ['CQI等级', '样本数', '下行均值(Mbps)', '下行最大值(Mbps)', '上行均值(Mbps)', '上行最大值(Mbps)']
                st.dataframe(显示数据, use_container_width=True, hide_index=True)
                
                # 创建柱状图对比
                fig_分布_n28 = go.Figure()
                fig_分布_n28.add_trace(go.Bar(
                    x=df_分布_n28['CQI等级'],
                    y=df_分布_n28['下行均值'],
                    name='下行均值',
                    marker_color='red',
                    error_y=dict(type='data', array=df_分布_n28['下行标准差'])
                ))
                fig_分布_n28.add_trace(go.Bar(
                    x=df_分布_n28['CQI等级'],
                    y=df_分布_n28['上行均值'],
                    name='上行均值',
                    marker_color='green',
                    error_y=dict(type='data', array=df_分布_n28['上行标准差'])
                ))
                fig_分布_n28.update_layout(
                    title="N28 - 不同CQI等级的速率对比（误差线为标准差）",
                    barmode='group',
                    xaxis_title="CQI等级",
                    yaxis_title="速率 (Mbps)",
                    template='plotly_white',
                    height=400
                )
                st.plotly_chart(fig_分布_n28, use_container_width=True)
            else:
                st.info("N28数据不可用")

    # ========== 分析总结（放在最后）==========
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 CQI对速率影响 - 综合分析总结</p>', unsafe_allow_html=True)

    总结内容 = "<div class='highlight'>"
    
    # 1. CQI与速率相关性分析
    if 'n41' in 速率影响 and 'n28' in 速率影响:
        总结内容 += "<b>📊 1. CQI与速率相关性对比</b><br>"
        for 速率 in 速率影响['n41'].keys():
            if 速率 in 速率影响['n28']:
                n41_r = 速率影响['n41'][速率]['相关系数']
                n28_r = 速率影响['n28'][速率]['相关系数']
                n41_sig = 速率影响['n41'][速率]['显著性']
                n28_sig = 速率影响['n28'][速率]['显著性']
                总结内容 += f"• {速率}: N41相关系数={n41_r:.4f}({n41_sig}), N28相关系数={n28_r:.4f}({n28_sig})<br>"
        
        # 找出相关性最强的指标
        n41最强 = max(速率影响['n41'].items(), key=lambda x: abs(x[1]['相关系数']))
        n28最强 = max(速率影响['n28'].items(), key=lambda x: abs(x[1]['相关系数']))
        总结内容 += f"<br>• N41与CQI相关性最强: {n41最强[0]} (r={n41最强[1]['相关系数']:.4f})<br>"
        总结内容 += f"• N28与CQI相关性最强: {n28最强[0]} (r={n28最强[1]['相关系数']:.4f})<br>"
        总结内容 += "<br>"
    
    # 2. CQI分位数速率趋势分析
    if 分位数数据 and ('n41' in 分位数数据 or 'n28' in 分位数数据):
        总结内容 += "<b>📈 2. CQI分位数速率趋势</b><br>"
        if 'n41' in 分位数数据:
            df_n41 = 分位数数据['n41']
            起始下行 = df_n41['下行用户平均速率(MBPS)'].iloc[0]
            结束下行 = df_n41['下行用户平均速率(MBPS)'].iloc[-1]
            提升率 = ((结束下行 - 起始下行) / 起始下行 * 100) if 起始下行 > 0 else 0
            总结内容 += f"• N41: CQI从低到高，下行速率从{起始下行:.2f} Mbps提升至{结束下行:.2f} Mbps (提升{提升率:.1f}%)<br>"
        if 'n28' in 分位数数据:
            df_n28 = 分位数数据['n28']
            起始下行 = df_n28['下行用户平均速率(MBPS)'].iloc[0]
            结束下行 = df_n28['下行用户平均速率(MBPS)'].iloc[-1]
            提升率 = ((结束下行 - 起始下行) / 起始下行 * 100) if 起始下行 > 0 else 0
            总结内容 += f"• N28: CQI从低到高，下行速率从{起始下行:.2f} Mbps提升至{结束下行:.2f} Mbps (提升{提升率:.1f}%)<br>"
        总结内容 += "<br>"
    
    # 3. 不同CQI等级速率分布
    if 分布数据 and ('n41' in 分布数据 or 'n28' in 分布数据):
        总结内容 += "<b>📉 3. 不同CQI等级速率分布特征</b><br>"
        if 'n41' in 分布数据:
            df_n41 = 分布数据['n41']
            高CQI = df_n41[df_n41['CQI等级'] == '高(>85%)']
            低CQI = df_n41[df_n41['CQI等级'] == '低(<60%)']
            if len(高CQI) > 0 and len(低CQI) > 0:
                倍数 = 高CQI['下行均值'].iloc[0] / 低CQI['下行均值'].iloc[0] if 低CQI['下行均值'].iloc[0] > 0 else 0
                总结内容 += f"• N41: 高CQI vs 低CQI下行速率比约为 {倍数:.1f}:1<br>"
        if 'n28' in 分布数据:
            df_n28 = 分布数据['n28']
            高CQI = df_n28[df_n28['CQI等级'] == '高(>85%)']
            低CQI = df_n28[df_n28['CQI等级'] == '低(<60%)']
            if len(高CQI) > 0 and len(低CQI) > 0:
                倍数 = 高CQI['下行均值'].iloc[0] / 低CQI['下行均值'].iloc[0] if 低CQI['下行均值'].iloc[0] > 0 else 0
                总结内容 += f"• N28: 高CQI vs 低CQI下行速率比约为 {倍数:.1f}:1<br>"
        总结内容 += "<br>"
    
    # 4. 优化建议
    总结内容 += "<b>💡 4. 优化建议</b><br>"
    总结内容 += "• 优先提升低CQI小区的覆盖质量和SINR<br>"
    总结内容 += "• 关注CQI与速率不匹配的小区，排查干扰或配置问题<br>"
    总结内容 += "• 根据CQI-速率相关性制定分层次优化策略<br>"
    总结内容 += "• 高CQI但低速率小区需重点排查网络拥塞或参数配置"
    
    总结内容 += "</div>"
    st.markdown(总结内容, unsafe_allow_html=True)

def 渲染制式对比影响因素(分析器: CQI分析器):
    """渲染影响CQI因素的网络制式对比"""
    st.markdown("""
    <div class="highlight">
    <b>🎯 影响CQI的因素分析说明：</b><br>
    通过相关性分析，识别影响CQI优良率的关键网络指标，明确优化方向。<br><br>
    <b>📊 分析方法：</b><br>
    • <b>皮尔逊相关系数</b>：衡量各指标与CQI的线性相关程度，范围-1到+1<br>
    • <b>相关性强度</b>：|r|>0.7为强相关，0.3-0.7为中等相关，<0.3为弱相关<br>
    • <b>显著性检验</b>：P值<0.05表示相关性具有统计显著性<br>
    <br>
    <b>📈 分析指标：</b><br>
    • 覆盖类：覆盖电平、覆盖系数、重叠覆盖比例<br>
    • 干扰类：SINR、上行干扰电平<br>
    • 资源类：PRB利用率、TA（距离）<br>
    <br>
    <b>💡 应用价值：</b>找出对CQI影响最大的因素，优先投入优化资源
    </div>
    """, unsafe_allow_html=True)
    
    影响结果 = 分析器.分析影响CQI的指标_按制式()

    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])

    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 影响因素排序</div>', unsafe_allow_html=True)
        if 'n41' in 影响结果:
            图表数据 = pd.DataFrame(影响结果['n41'])
            fig_n41 = px.bar(
                图表数据,
                x="相关系数",
                y="指标",
                orientation='h',
                color="相关系数",
                color_continuous_scale="Blues",
                title="N41 - 影响CQI的因素",
                text_auto=".3f"
            )
            fig_n41.update_layout(template="plotly_white", yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_n41, use_container_width=True)

    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 影响因素排序</div>', unsafe_allow_html=True)
        if 'n28' in 影响结果:
            图表数据 = pd.DataFrame(影响结果['n28'])
            fig_n28 = px.bar(
                图表数据,
                x="相关系数",
                y="指标",
                orientation='h',
                color="相关系数",
                color_continuous_scale="Reds",
                title="N28 - 影响CQI的因素",
                text_auto=".3f"
            )
            fig_n28.update_layout(template="plotly_white", yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_n28, use_container_width=True)

    st.markdown("---")

    # 详细对比表
    st.markdown('<p class="sub-header">📊 影响因素详细对比</p>', unsafe_allow_html=True)

    if 'n41' in 影响结果 and 'n28' in 影响结果:
        对比数据 = []
        for i, (n41结果, n28结果) in enumerate(zip(影响结果['n41'], 影响结果['n28'])):
            # 处理None值的情况
            n41系数 = n41结果['相关系数']
            n28系数 = n28结果['相关系数']
            
            # 计算差异，处理None值
            if n41系数 is not None and n28系数 is not None:
                差异值 = abs(n41系数 - n28系数)
            else:
                差异值 = None
            
            对比数据.append({
                '指标': n41结果['指标'],
                'N41相关系数': n41系数,
                'N41显著性': n41结果['显著性'] if n41系数 is not None else '数据不足',
                'N28相关系数': n28系数,
                'N28显著性': n28结果['显著性'] if n28系数 is not None else '数据不足',
                '差异': 差异值
            })

        对比df = pd.DataFrame(对比数据)
        
        # 自定义格式化函数，处理None值
        def 格式化相关系数(val):
            if val is None:
                return '-'
            return f"{val:.4f}"
        
        st.dataframe(
            对比df.style.format({
                'N41相关系数': 格式化相关系数,
                'N28相关系数': 格式化相关系数,
                '差异': lambda x: '-' if x is None else f"{x:.4f}"
            }).background_gradient(subset=['差异'], cmap='YlOrRd'),
            use_container_width=True
        )

    # 分析总结
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 分析总结</p>', unsafe_allow_html=True)

    if 'n41' in 影响结果 and 'n28' in 影响结果:
        总结内容 = "<div class='highlight'><b>📊 影响CQI的因素分析总结</b><br><br>"

        # 获取前3个最重要因素（过滤掉相关系数为None的）
        n41_top3 = [x for x in 影响结果['n41'][:5] if x['相关系数'] is not None][:3]
        n28_top3 = [x for x in 影响结果['n28'][:5] if x['相关系数'] is not None][:3]

        总结内容 += "<b>1. N41网络制式TOP 3影响因素：</b><br>"
        if n41_top3:
            for i, item in enumerate(n41_top3, 1):
                总结内容 += f"• 第{i}位: {item['指标']} (相关系数={item['相关系数']:.4f}, {item['显著性']})<br>"
        else:
            总结内容 += "• 没有足够的有效数据进行分析<br>"

        总结内容 += "<br><b>2. N28网络制式TOP 3影响因素：</b><br>"
        if n28_top3:
            for i, item in enumerate(n28_top3, 1):
                总结内容 += f"• 第{i}位: {item['指标']} (相关系数={item['相关系数']:.4f}, {item['显著性']})<br>"
        else:
            总结内容 += "• 没有足够的有效数据进行分析<br>"

        # 计算共同因素
        n41_factors = set([item['指标'] for item in 影响结果['n41'][:5] if item['相关系数'] is not None])
        n28_factors = set([item['指标'] for item in 影响结果['n28'][:5] if item['相关系数'] is not None])
        共同因素 = n41_factors & n28_factors

        总结内容 += "<br><b>3. 共同重要因素：</b><br>"
        if 共同因素:
            for factor in 共同因素:
                总结内容 += f"• {factor}<br>"
        else:
            总结内容 += "• 无共同的重要因素，两种制式的优化重点不同<br>"

        总结内容 += "<br><b>4. 优化建议：</b><br>"
        if n41_top3:
            总结内容 += f"• N41应重点优化: {n41_top3[0]['指标']}<br>"
        if n28_top3:
            总结内容 += f"• N28应重点优化: {n28_top3[0]['指标']}<br>"
        总结内容 += "• 针对不同网络制式制定差异化的CQI优化策略"

        总结内容 += "</div>"
        st.markdown(总结内容, unsafe_allow_html=True)


def 渲染制式对比相关性矩阵(分析器: CQI分析器):
    """渲染相关性可视化的网络制式对比（包含散点图和相关性矩阵）"""
    st.markdown("""
    <div class="highlight">
    <b>🔗 相关性可视化分析说明：</b><br>
    通过散点图和相关性矩阵，全面展示各网络指标间的相关关系。<br><br>
    <b>📊 可视化组件：</b><br>
    • <b>散点图</b>：展示两个指标的具体数据分布和趋势，直观识别异常值和聚集模式<br>
    • <b>相关性矩阵热力图</b>：展示所有指标间的相关性强度，颜色越深表示相关性越强<br>
    <br>
    <b>📈 相关系数解读：</b><br>
    • <b>+1</b>：完全正相关（一个指标增加，另一个必然增加）<br>
    • <b>-1</b>：完全负相关（一个指标增加，另一个必然减少）<br>
    • <b>0</b>：无线性相关<br>
    • <b>绝对值>0.7</b>：强相关 | <b>0.3-0.7</b>：中等相关 | <b><0.3</b>：弱相关<br>
    <br>
    <b>💡 应用场景：</b>识别指标间隐藏的关系，如覆盖电平与CQI的关联、SINR与速率的关联等
    </div>
    """, unsafe_allow_html=True)
    
    列名列表 = [
        'CQI优良率',
        '下行用户平均速率(MBPS)',
        '上行用户平均速率(MBPS)',
        '小区MR覆盖平均电平',
        '小区MR覆盖平均SINR',
        '小区MR覆盖平均TA',
        '小区上行平均干扰电平',
        '重叠覆盖采样点比例(%)',  # ⭐新增
        '覆盖系数'  # ⭐新增
    ]

    简短列名 = {
        'CQI优良率': 'CQI',
        '下行用户平均速率(MBPS)': '下行速率',
        '上行用户平均速率(MBPS)': '上行速率',
        '小区MR覆盖平均电平': '覆盖电平',
        '小区MR覆盖平均SINR': 'SINR',
        '小区MR覆盖平均TA': 'TA',
        '小区上行平均干扰电平': '干扰电平',
        '重叠覆盖采样点比例(%)': '重叠覆盖',  # ⭐新增
        '覆盖系数': '覆盖系数'  # ⭐新增
    }

    相关性矩阵 = 分析器.计算相关性矩阵_按制式(列名列表)

    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])

    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 相关性可视化</div>', unsafe_allow_html=True)
        if 'n41' in 相关性矩阵:
            矩阵 = 相关性矩阵['n41'].copy()
            矩阵.index = [简短列名.get(x, x) for x in 矩阵.index]
            矩阵.columns = [简短列名.get(x, x) for x in 矩阵.columns]

            fig_n41 = go.Figure(data=go.Heatmap(
                z=矩阵.values,
                x=矩阵.columns,
                y=矩阵.index,
                colorscale='Blues',
                zmid=0,
                text=np.round(矩阵.values, 2),
                texttemplate='%{text}',
                textfont={"size": 10}
            ))
            fig_n41.update_layout(template="plotly_white", height=500)
            st.plotly_chart(fig_n41, use_container_width=True)

    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 相关性可视化</div>', unsafe_allow_html=True)
        if 'n28' in 相关性矩阵:
            矩阵 = 相关性矩阵['n28'].copy()
            矩阵.index = [简短列名.get(x, x) for x in 矩阵.index]
            矩阵.columns = [简短列名.get(x, x) for x in 矩阵.columns]

            fig_n28 = go.Figure(data=go.Heatmap(
                z=矩阵.values,
                x=矩阵.columns,
                y=矩阵.index,
                colorscale='Reds',
                zmid=0,
                text=np.round(矩阵.values, 2),
                texttemplate='%{text}',
                textfont={"size": 10}
            ))
            fig_n28.update_layout(template="plotly_white", height=500)
            st.plotly_chart(fig_n28, use_container_width=True)

    # ========== 散点图对比 ==========
    st.markdown("---")
    st.markdown('<p class="sub-header">📈 关键指标散点图对比</p>', unsafe_allow_html=True)
    
    st.info("""
    💡 **提示**：散点图展示关键指标对之间的数据分布关系
    • 趋势线虚线表示拟合趋势，R值表示相关强度
    • 颜色深浅代表第三维指标的值（通常为SINR或CQI）
    • 新增：覆盖系数和重叠覆盖采样点比例与其他指标的关系分析
    """)
    
    分组数据 = 分析器.按网络制式分组()
    
    # 定义散点图配置（精选5个关键关系）
    散点图配置 = [
        ("📊 CQI优良率 vs 下行用户平均速率", "CQI优良率", "下行用户平均速率(MBPS)", "小区MR覆盖平均SINR"),
        ("📊 CQI优良率 vs 上行用户平均速率", "CQI优良率", "上行用户平均速率(MBPS)", "小区MR覆盖平均SINR"),
        ("📡 SINR vs 下行用户平均速率", "小区MR覆盖平均SINR", "下行用户平均速率(MBPS)", "CQI优良率"),
        ("📶 覆盖电平 vs CQI优良率", "小区MR覆盖平均电平", "CQI优良率", "小区MR覆盖平均SINR"),
        ("📍 TA vs CQI优良率", "小区MR覆盖平均TA", "CQI优良率", "小区MR覆盖平均SINR"),
    ]
    
    # 动态添加覆盖系数和重叠覆盖的散点图（如果数据中存在）
    if 'n41' in 分组数据 and '覆盖系数' in 分组数据['n41'].columns:
        散点图配置.extend([
            ("📐 覆盖系数 vs CQI优良率", "覆盖系数", "CQI优良率", "小区MR覆盖平均SINR"),
            ("📐 覆盖系数 vs 下行用户平均速率", "覆盖系数", "下行用户平均速率(MBPS)", "CQI优良率"),
        ])
    if 'n41' in 分组数据 and '重叠覆盖采样点比例(%)' in 分组数据['n41'].columns:
        散点图配置.extend([
            ("🔀 重叠覆盖比例 vs CQI优良率", "重叠覆盖采样点比例(%)", "CQI优良率", "小区MR覆盖平均SINR"),
            ("🔀 重叠覆盖比例 vs SINR", "重叠覆盖采样点比例(%)", "小区MR覆盖平均SINR", "CQI优良率"),
        ])
    
    for 标题, x轴, y轴, 颜色 in 散点图配置:
        st.markdown(f"**{标题}**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**N41**")
            if 'n41' in 分组数据:
                fig = 安全生成散点图(分组数据['n41'], x轴, y轴, 颜色, f"N41 - {标题}", "Blues")
                if fig:
                    # 计算相关性并生成一句话总结
                    temp_data = 分组数据['n41'][[x轴, y轴]].dropna()
                    if len(temp_data) > 10:
                        corr = temp_data[x轴].corr(temp_data[y轴])
                        trend = "正相关" if corr > 0 else "负相关"
                        strength = "强" if abs(corr) > 0.6 else ("中等" if abs(corr) > 0.3 else "弱")
                        st.info(f"📊 N41: {x轴}与{y轴}呈{strength}{trend}(r={corr:.3f})")
                    st.plotly_chart(fig, use_container_width=True, key=f"n41_{标题}_{x轴}_{y轴}")
                else:
                    st.info("数据不足，无法生成图表")
            else:
                st.info("N41数据不可用")
        
        with col2:
            st.markdown("**N28**")
            if 'n28' in 分组数据:
                配色 = "Viridis" if "SINR" in 标题 else "Reds"
                fig = 安全生成散点图(分组数据['n28'], x轴, y轴, 颜色, f"N28 - {标题}", 配色)
                if fig:
                    # 计算相关性并生成一句话总结
                    temp_data = 分组数据['n28'][[x轴, y轴]].dropna()
                    if len(temp_data) > 10:
                        corr = temp_data[x轴].corr(temp_data[y轴])
                        trend = "正相关" if corr > 0 else "负相关"
                        strength = "强" if abs(corr) > 0.6 else ("中等" if abs(corr) > 0.3 else "弱")
                        st.info(f"📊 N28: {x轴}与{y轴}呈{strength}{trend}(r={corr:.3f})")
                    st.plotly_chart(fig, use_container_width=True, key=f"n28_{标题}_{x轴}_{y轴}")
                else:
                    st.info("数据不足，无法生成图表")
            else:
                st.info("N28数据不可用")

    # 分析总结
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 相关性可视化分析总结</p>', unsafe_allow_html=True)

    if 'n41' in 相关性矩阵 and 'n28' in 相关性矩阵:
        总结内容 = "<div class='highlight'><b>📊 相关性可视化分析总结</b><br><br>"

        # 获取CQI与其他指标的相关性
        n41_matrix = 相关性矩阵['n41']
        n28_matrix = 相关性矩阵['n28']

        if 'CQI优良率' in n41_matrix.index and 'CQI优良率' in n28_matrix.index:
            cqi_corr_n41 = n41_matrix.loc['CQI优良率'].drop('CQI优良率')
            cqi_corr_n28 = n28_matrix.loc['CQI优良率'].drop('CQI优良率')

            总结内容 += "<b>1. CQI与各指标相关性排序（N41）：</b><br>"
            n41_sorted = cqi_corr_n41.abs().sort_values(ascending=False)
            for i, (idx, val) in enumerate(n41_sorted.head(4).items(), 1):
                总结内容 += f"• 第{i}位: {简短列名.get(idx, idx)} (r={cqi_corr_n41[idx]:.3f})<br>"

            总结内容 += "<br><b>2. CQI与各指标相关性排序（N28）：</b><br>"
            n28_sorted = cqi_corr_n28.abs().sort_values(ascending=False)
            for i, (idx, val) in enumerate(n28_sorted.head(4).items(), 1):
                总结内容 += f"• 第{i}位: {简短列名.get(idx, idx)} (r={cqi_corr_n28[idx]:.3f})<br>"

            # 找出相关性差异最大的指标
            diff = (cqi_corr_n41 - cqi_corr_n28).abs()
            if len(diff) > 0:
                max_diff_idx = diff.idxmax()
                总结内容 += f"<br><b>3. 相关性差异最大的指标：</b><br>"
                总结内容 += f"• {简短列名.get(max_diff_idx, max_diff_idx)}: N41(r={cqi_corr_n41[max_diff_idx]:.3f}) vs N28(r={cqi_corr_n28[max_diff_idx]:.3f})<br>"

        总结内容 += "<br><b>4. 关键发现：</b><br>"
        总结内容 += "• 从热力图可直观看出各指标间的相关性强度<br>"
        总结内容 += "• 深色区域表示强正相关，浅色区域表示弱相关或负相关<br>"
        总结内容 += "• 对角线始终为1（自身相关性）"

        总结内容 += "</div>"
        st.markdown(总结内容, unsafe_allow_html=True)


def 渲染制式对比拐点分析(分析器: CQI分析器):
    """渲染CQI-速率拐点分析"""
    st.markdown("""
    <div class="highlight">
    <b>📈 CQI-速率拐点分析：</b><br>
    将CQI优良率划分为多个区间，分析每个区间的平均速率变化，找出速率增长的<b>拐点</b>。<br>
    <b>拐点含义：</b>超过此CQI值后，速率提升效果发生显著变化（可能开始加速或趋于平稳）。
    </div>
    """, unsafe_allow_html=True)

    分段数 = st.slider("选择CQI区间数量", 5, 15, 10, key="inflection_slider")

    with st.spinner('正在分析拐点...'):
        拐点分析结果 = 分析器.CQI速率拐点分析_按制式(分段数)

    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])

    # N41分析
    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 拐点分析</div>', unsafe_allow_html=True)
        if 'n41' in 拐点分析结果:
            区间统计 = 拐点分析结果['n41']['区间统计']
            拐点 = 拐点分析结果['n41']['拐点']
            
            # 显示拐点信息
            if 拐点 is not None:
                st.success(f"🎯 **拐点CQI值：{拐点['CQI均值']:.1f}%**\n\n"
                          f"• 拐点前平均速率：{区间统计.loc[拐点.name-1, '平均速率']:.2f} Mbps\n"
                          f"• 拐点后平均速率：{拐点['平均速率']:.2f} Mbps\n"
                          f"• 速率跃升：{拐点['速率增长(Mbps)']:.2f} Mbps ({拐点['速率增长率(%)']:.1f}%)\n"
                          f"• 该区间样本数：{拐点['样本数']:.0f}")
            
            # 显示区间统计表
            显示列 = ['CQI均值', 'CQI最小值', 'CQI最大值', '样本数', '平均速率', '速率增长(Mbps)', '速率增长率(%)']
            
            # 如果有拐点，在表格中标记
            if 拐点 is not None:
                st.info(f"🎯 拐点位于第 {拐点.name + 1} 行 (CQI均值: {拐点['CQI均值']:.1f}%)")
            
            st.dataframe(
                区间统计[显示列].style.format({
                    'CQI均值': '{:.1f}%',
                    'CQI最小值': '{:.1f}%',
                    'CQI最大值': '{:.1f}%',
                    '平均速率': '{:.2f}',
                    '速率增长(Mbps)': '{:.2f}',
                    '速率增长率(%)': '{:.1f}%'
                }),
                use_container_width=True
            )
            
            # 绘制拐点图
            fig_n41 = go.Figure()
            fig_n41.add_trace(go.Scatter(
                x=区间统计['CQI均值'],
                y=区间统计['平均速率'],
                mode='lines+markers',
                name='平均速率',
                line=dict(color='#1E90FF', width=2),
                marker=dict(size=8)
            ))
            
            # 标记拐点
            if 拐点 is not None:
                fig_n41.add_trace(go.Scatter(
                    x=[拐点['CQI均值']],
                    y=[拐点['平均速率']],
                    mode='markers',
                    name='拐点',
                    marker=dict(color='red', size=15, symbol='star')
                ))
            
            fig_n41.update_layout(
                title='N41 - CQI与速率关系曲线',
                xaxis_title='CQI优良率 (%)',
                yaxis_title='平均下行速率 (Mbps)',
                template='plotly_white',
                height=400,
                showlegend=True
            )
            st.plotly_chart(fig_n41, use_container_width=True)
        else:
            st.warning("N41数据不满足拐点分析条件")

    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    # N28分析
    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 拐点分析</div>', unsafe_allow_html=True)
        if 'n28' in 拐点分析结果:
            区间统计 = 拐点分析结果['n28']['区间统计']
            拐点 = 拐点分析结果['n28']['拐点']
            
            # 显示拐点信息
            if 拐点 is not None:
                st.success(f"🎯 **拐点CQI值：{拐点['CQI均值']:.1f}%**\n\n"
                          f"• 拐点前平均速率：{区间统计.loc[拐点.name-1, '平均速率']:.2f} Mbps\n"
                          f"• 拐点后平均速率：{拐点['平均速率']:.2f} Mbps\n"
                          f"• 速率跃升：{拐点['速率增长(Mbps)']:.2f} Mbps ({拐点['速率增长率(%)']:.1f}%)\n"
                          f"• 该区间样本数：{拐点['样本数']:.0f}")
            
            # 显示区间统计表
            显示列 = ['CQI均值', 'CQI最小值', 'CQI最大值', '样本数', '平均速率', '速率增长(Mbps)', '速率增长率(%)']
            
            # 如果有拐点，在表格中标记
            if 拐点 is not None:
                st.info(f"🎯 拐点位于第 {拐点.name + 1} 行 (CQI均值: {拐点['CQI均值']:.1f}%)")
            
            st.dataframe(
                区间统计[显示列].style.format({
                    'CQI均值': '{:.1f}%',
                    'CQI最小值': '{:.1f}%',
                    'CQI最大值': '{:.1f}%',
                    '平均速率': '{:.2f}',
                    '速率增长(Mbps)': '{:.2f}',
                    '速率增长率(%)': '{:.1f}%'
                }),
                use_container_width=True
            )
            
            # 绘制拐点图
            fig_n28 = go.Figure()
            fig_n28.add_trace(go.Scatter(
                x=区间统计['CQI均值'],
                y=区间统计['平均速率'],
                mode='lines+markers',
                name='平均速率',
                line=dict(color='#FF6B6B', width=2),
                marker=dict(size=8)
            ))
            
            # 标记拐点
            if 拐点 is not None:
                fig_n28.add_trace(go.Scatter(
                    x=[拐点['CQI均值']],
                    y=[拐点['平均速率']],
                    mode='markers',
                    name='拐点',
                    marker=dict(color='red', size=15, symbol='star')
                ))
            
            fig_n28.update_layout(
                title='N28 - CQI与速率关系曲线',
                xaxis_title='CQI优良率 (%)',
                yaxis_title='平均下行速率 (Mbps)',
                template='plotly_white',
                height=400,
                showlegend=True
            )
            st.plotly_chart(fig_n28, use_container_width=True)
        else:
            st.warning("N28数据不满足拐点分析条件")

    # 对比总结
    n41有数据 = 'n41' in 拐点分析结果
    n28有数据 = 'n28' in 拐点分析结果
    
    if n41有数据 or n28有数据:
        总结内容 = "<div class='success-box'><b>💡 拐点分析对比结论：</b><br>"
        
        if n41有数据 and 拐点分析结果['n41']['拐点'] is not None:
            拐点_n41 = 拐点分析结果['n41']['拐点']
            区间统计_n41 = 拐点分析结果['n41']['区间统计']
            总结内容 += f"<b>📡 N41拐点</b>：CQI均值为<strong>{拐点_n41['CQI均值']:.1f}%</strong>时，速率发生显著变化<br>"
            总结内容 += f"&nbsp;&nbsp;• 拐点前速率：{区间统计_n41.loc[拐点_n41.name-1, '平均速率']:.2f} Mbps<br>"
            总结内容 += f"&nbsp;&nbsp;• 拐点后速率：{拐点_n41['平均速率']:.2f} Mbps<br>"
            总结内容 += f"&nbsp;&nbsp;• 速率跃升：{拐点_n41['速率增长(Mbps)']:.2f} Mbps ({拐点_n41['速率增长率(%)']:.1f}%)<br><br>"
        elif n41有数据:
            总结内容 += "<b>📡 N41</b>：未找到明显拐点<br><br>"
        
        if n28有数据 and 拐点分析结果['n28']['拐点'] is not None:
            拐点_n28 = 拐点分析结果['n28']['拐点']
            区间统计_n28 = 拐点分析结果['n28']['区间统计']
            总结内容 += f"<b>📡 N28拐点</b>：CQI均值为<strong>{拐点_n28['CQI均值']:.1f}%</strong>时，速率发生显著变化<br>"
            总结内容 += f"&nbsp;&nbsp;• 拐点前速率：{区间统计_n28.loc[拐点_n28.name-1, '平均速率']:.2f} Mbps<br>"
            总结内容 += f"&nbsp;&nbsp;• 拐点后速率：{拐点_n28['平均速率']:.2f} Mbps<br>"
            总结内容 += f"&nbsp;&nbsp;• 速率跃升：{拐点_n28['速率增长(Mbps)']:.2f} Mbps ({拐点_n28['速率增长率(%)']:.1f}%)<br><br>"
        elif n28有数据:
            总结内容 += "<b>📡 N28</b>：未找到明显拐点<br><br>"
        
        if n41有数据 and n28有数据 and 拐点分析结果['n41']['拐点'] is not None and 拐点分析结果['n28']['拐点'] is not None:
            拐点_n41 = 拐点分析结果['n41']['拐点']
            拐点_n28 = 拐点分析结果['n28']['拐点']
            对比结论 = "N41" if 拐点_n41['速率增长率(%)'] > 拐点_n28['速率增长率(%)'] else "N28"
            总结内容 += f"<b>📊 对比分析</b>：{对比结论}的速率拐点变化更显著，建议重点关注该制式的CQI优化"
        elif n41有数据 and n28有数据:
            总结内容 += "<b>📊 对比分析</b>：两组数据均已分析"
        
        总结内容 += "</div>"
        st.markdown(总结内容, unsafe_allow_html=True)
    else:
        st.warning("⚠️ 当前数据不满足拐点分析条件。可能原因：数据样本分布过于集中，建议检查CQI优良率数据分布或增加样本量。")


def 渲染制式对比贡献度分析(分析器: CQI分析器):
    """渲染贡献度分析的网络制式对比"""
    st.markdown("""
    <div class="highlight">
    <b>💡 贡献度分析说明：</b><br>
    基于各指标与CQI的相关性，量化每个指标对CQI的贡献度，从而明确优化优先级，指导优化资源分配。
    <br><br>
    <b>📊 计算方法：</b><br>
    • <b>相关系数</b>：计算皮尔逊相关系数 r，衡量指标与CQI的线性相关程度<br>
    • <b>贡献度</b>：贡献度 = |r| / Σ|r| × 100%，即该指标相关系数绝对值占所有指标相关系数绝对值之和的比例<br>
    • <b>排序规则</b>：按贡献度从高到低排序，贡献度越高表示该指标对CQI影响越大<br>
    <br>
    <b>🎯 分析指标：</b>覆盖电平、SINR、TA、干扰电平、PRB利用率、覆盖系数、重叠覆盖比例<br>
    <br>
    <b>💡 应用场景：</b>识别对CQI影响最大的因素，指导网络优化资源投入方向
    </div>
    """, unsafe_allow_html=True)

    with st.spinner('正在分析...'):
        贡献度结果 = 分析器.贡献度分析_按制式()

    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])

    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 贡献度分析</div>', unsafe_allow_html=True)
        if 'n41' in 贡献度结果:
            贡献度df_n41 = pd.DataFrame(贡献度结果['n41']['贡献度列表'])
            
            # 自定义格式化函数处理None值
            def 格式化相关系数(val):
                return '-' if val is None else f"{val:.4f}"
            
            st.dataframe(
                贡献度df_n41.style.format({
                    '相关系数': 格式化相关系数,
                    '贡献度(%)': '{:.2f}',
                    '累积贡献度(%)': '{:.2f}%'
                }).background_gradient(subset=['贡献度(%)'], cmap='Blues'),
                use_container_width=True
            )

            # 饼图只使用有贡献度的数据
            if len(贡献度df_n41) > 0:
                fig_pie_n41 = go.Figure(data=[go.Pie(
                    labels=贡献度df_n41['指标'],
                    values=贡献度df_n41['贡献度(%)'],
                    hole=0.3,
                    textinfo='label+percent',
                    marker=dict(colors=px.colors.sequential.Blues[:len(贡献度df_n41)])
                )])
                fig_pie_n41.update_layout(title='N41 - 贡献度分布', template='plotly_white', height=400)
                st.plotly_chart(fig_pie_n41, use_container_width=True)
            else:
                st.warning("N41无有效的贡献度数据")

    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 贡献度分析</div>', unsafe_allow_html=True)
        if 'n28' in 贡献度结果:
            贡献度df_n28 = pd.DataFrame(贡献度结果['n28']['贡献度列表'])
            
            # 自定义格式化函数处理None值
            def 格式化相关系数(val):
                return '-' if val is None else f"{val:.4f}"
            
            st.dataframe(
                贡献度df_n28.style.format({
                    '相关系数': 格式化相关系数,
                    '贡献度(%)': '{:.2f}',
                    '累积贡献度(%)': '{:.2f}%'
                }).background_gradient(subset=['贡献度(%)'], cmap='Reds'),
                use_container_width=True
            )

            # 饼图只使用有贡献度的数据
            if len(贡献度df_n28) > 0:
                fig_pie_n28 = go.Figure(data=[go.Pie(
                    labels=贡献度df_n28['指标'],
                    values=贡献度df_n28['贡献度(%)'],
                    hole=0.3,
                    textinfo='label+percent',
                    marker=dict(colors=px.colors.sequential.Reds[:len(贡献度df_n28)])
                )])
                fig_pie_n28.update_layout(title='N28 - 贡献度分布', template='plotly_white', height=400)
                st.plotly_chart(fig_pie_n28, use_container_width=True)
            else:
                st.warning("N28无有效的贡献度数据")

    # 分析总结
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 分析总结</p>', unsafe_allow_html=True)

    if 'n41' in 贡献度结果 and 'n28' in 贡献度结果:
        贡献度df_n41 = pd.DataFrame(贡献度结果['n41']['贡献度列表'])
        贡献度df_n28 = pd.DataFrame(贡献度结果['n28']['贡献度列表'])
        
        # 检查是否有有效数据
        n41有数据 = len(贡献度df_n41) > 0
        n28有数据 = len(贡献度df_n28) > 0
        
        总结内容 = "<div class='highlight'><b>📊 贡献度分析总结</b><br><br>"

        if n41有数据:
            总结内容 += "<b>1. N41网络制式贡献度排名：</b><br>"
            for i, row in 贡献度df_n41.head(5).iterrows():
                总结内容 += f"• {row['指标']}: {row['贡献度(%)']:.2f}% (累积: {row['累积贡献度(%)']:.2f}%)<br>"
        else:
            总结内容 += "<b>1. N41网络制式：</b><br>• 无有效的贡献度数据<br>"

        if n28有数据:
            总结内容 += "<br><b>2. N28网络制式贡献度排名：</b><br>"
            for i, row in 贡献度df_n28.head(5).iterrows():
                总结内容 += f"• {row['指标']}: {row['贡献度(%)']:.2f}% (累积: {row['累积贡献度(%)']:.2f}%)<br>"
        else:
            总结内容 += "<br><b>2. N28网络制式：</b><br>• 无有效的贡献度数据<br>"

        # 找出主要贡献因素
        if n41有数据 and n28有数据:
            n41_top1 = 贡献度df_n41.iloc[0]['指标']
            n28_top1 = 贡献度df_n28.iloc[0]['指标']

            总结内容 += "<br><b>3. 主要贡献因素：</b><br>"
            总结内容 += f"• N41: {n41_top1}贡献最大，占比{贡献度df_n41.iloc[0]['贡献度(%)']:.2f}%<br>"
            总结内容 += f"• N28: {n28_top1}贡献最大，占比{贡献度df_n28.iloc[0]['贡献度(%)']:.2f}%<br>"

            总结内容 += "<br><b>4. 优化建议：</b><br>"
            总结内容 += f"• N41应优先优化{n41_top1}指标<br>"
            总结内容 += f"• N28应优先优化{n28_top1}指标<br>"
            总结内容 += "• 集中资源优化贡献度最高的指标可获得最大性能提升<br>"
            总结内容 += f"• N41前3个指标累积贡献度: {贡献度df_n41.head(3)['贡献度(%)'].sum():.2f}%<br>"
            总结内容 += f"• N28前3个指标累积贡献度: {贡献度df_n28.head(3)['贡献度(%)'].sum():.2f}%"
        
        总结内容 += "</div>"
        st.markdown(总结内容, unsafe_allow_html=True)


def 渲染制式对比分组分析(分析器: CQI分析器):
    """渲染分组分析的网络制式对比"""
    st.markdown("""
    <div class="highlight">
    <b>📊 分组分析说明：</b><br>
    按CQI优良率将小区分为若干组，对比不同CQI水平下其他网络指标的特征差异，发现影响CQI的关键因素。
    <br><br>
    <b>🎯 分组方式：</b><br>
    • 将小区按CQI优良率<b>等频分组</b>（每组样本数大致相等）<br>
    • 默认分为5组（可通过滑块调整3-10组）<br>
    • 例如5组对应：CQI最差20%、较差20%、中等20%、较好20%、最好20%的小区<br>
    <br>
    <b>📈 分析维度：</b><br>
    • 每组计算覆盖电平、SINR、TA、干扰、PRB利用率等指标的平均值<br>
    • 观察指标随CQI变化的规律，找出与CQI强相关的指标<br>
    <br>
    <b>💡 应用价值：</b>识别低CQI小区的共同特征，为针对性优化提供数据支撑
    </div>
    """, unsafe_allow_html=True)
    
    分组数 = st.slider("选择分组数（将CQI按等频分为N组）", 3, 10, 5, key="group_slider")

    with st.spinner('正在分析...'):
        分组分析 = 分析器.按CQI分组分析_按制式(分组数)

    # ========== 分组对比图（图表部分）==========
    st.markdown('<p class="sub-header">📈 分组对比图</p>', unsafe_allow_html=True)

    # 1. 下行速率对比
    st.markdown("**📊 下行用户平均速率分组对比**")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        if 'n41' in 分组分析:
            分组标签 = 分组分析['n41'].index.tolist()
            下行均值 = 分组分析['n41']['下行用户平均速率(MBPS)']['mean'].values

            fig_n41 = go.Figure(data=[go.Bar(
                x=分组标签,
                y=下行均值,
                marker_color='#1E90FF',
                text=np.round(下行均值, 2),
                textposition='outside'
            )])
            fig_n41.update_layout(
                title='N41 - 下行速率分组对比',
                xaxis_title='CQI分组',
                yaxis_title='下行速率 (Mbps)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n41, use_container_width=True)

    with col_chart2:
        if 'n28' in 分组分析:
            分组标签 = 分组分析['n28'].index.tolist()
            下行均值 = 分组分析['n28']['下行用户平均速率(MBPS)']['mean'].values

            fig_n28 = go.Figure(data=[go.Bar(
                x=分组标签,
                y=下行均值,
                marker_color='#FF6B6B',
                text=np.round(下行均值, 2),
                textposition='outside'
            )])
            fig_n28.update_layout(
                title='N28 - 下行速率分组对比',
                xaxis_title='CQI分组',
                yaxis_title='下行速率 (Mbps)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n28, use_container_width=True)

    # 2. 上行速率对比
    st.markdown("**📊 上行用户平均速率分组对比**")
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        if 'n41' in 分组分析:
            分组标签 = 分组分析['n41'].index.tolist()
            上行均值 = 分组分析['n41']['上行用户平均速率(MBPS)']['mean'].values

            fig_n41_up = go.Figure(data=[go.Bar(
                x=分组标签,
                y=上行均值,
                marker_color='#4169E1',
                text=np.round(上行均值, 2),
                textposition='outside'
            )])
            fig_n41_up.update_layout(
                title='N41 - 上行速率分组对比',
                xaxis_title='CQI分组',
                yaxis_title='上行速率 (Mbps)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n41_up, use_container_width=True)

    with col_chart4:
        if 'n28' in 分组分析:
            分组标签 = 分组分析['n28'].index.tolist()
            上行均值 = 分组分析['n28']['上行用户平均速率(MBPS)']['mean'].values

            fig_n28_up = go.Figure(data=[go.Bar(
                x=分组标签,
                y=上行均值,
                marker_color='#FF8E53',
                text=np.round(上行均值, 2),
                textposition='outside'
            )])
            fig_n28_up.update_layout(
                title='N28 - 上行速率分组对比',
                xaxis_title='CQI分组',
                yaxis_title='上行速率 (Mbps)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n28_up, use_container_width=True)

    # 3. SINR对比
    st.markdown("**📡 小区MR覆盖平均SINR分组对比**")
    col_chart5, col_chart6 = st.columns(2)

    with col_chart5:
        if 'n41' in 分组分析:
            分组标签 = 分组分析['n41'].index.tolist()
            sinr均值 = 分组分析['n41']['小区MR覆盖平均SINR']['mean'].values

            fig_n41_sinr = go.Figure(data=[go.Bar(
                x=分组标签,
                y=sinr均值,
                marker_color='#00CED1',
                text=np.round(sinr均值, 2),
                textposition='outside'
            )])
            fig_n41_sinr.update_layout(
                title='N41 - SINR分组对比',
                xaxis_title='CQI分组',
                yaxis_title='SINR (dB)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n41_sinr, use_container_width=True)

    with col_chart6:
        if 'n28' in 分组分析:
            分组标签 = 分组分析['n28'].index.tolist()
            sinr均值 = 分组分析['n28']['小区MR覆盖平均SINR']['mean'].values

            fig_n28_sinr = go.Figure(data=[go.Bar(
                x=分组标签,
                y=sinr均值,
                marker_color='#FF6347',
                text=np.round(sinr均值, 2),
                textposition='outside'
            )])
            fig_n28_sinr.update_layout(
                title='N28 - SINR分组对比',
                xaxis_title='CQI分组',
                yaxis_title='SINR (dB)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n28_sinr, use_container_width=True)

    # 4. 覆盖电平对比
    st.markdown("**📶 小区MR覆盖平均电平分组对比**")
    col_chart7, col_chart8 = st.columns(2)

    with col_chart7:
        if 'n41' in 分组分析:
            分组标签 = 分组分析['n41'].index.tolist()
            电平均值 = 分组分析['n41']['小区MR覆盖平均电平']['mean'].values

            fig_n41_rsrp = go.Figure(data=[go.Bar(
                x=分组标签,
                y=电平均值,
                marker_color='#9370DB',
                text=np.round(电平均值, 2),
                textposition='outside'
            )])
            fig_n41_rsrp.update_layout(
                title='N41 - 覆盖电平分组对比',
                xaxis_title='CQI分组',
                yaxis_title='覆盖电平 (dBm)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n41_rsrp, use_container_width=True)

    with col_chart8:
        if 'n28' in 分组分析:
            分组标签 = 分组分析['n28'].index.tolist()
            电平均值 = 分组分析['n28']['小区MR覆盖平均电平']['mean'].values

            fig_n28_rsrp = go.Figure(data=[go.Bar(
                x=分组标签,
                y=电平均值,
                marker_color='#DC143C',
                text=np.round(电平均值, 2),
                textposition='outside'
            )])
            fig_n28_rsrp.update_layout(
                title='N28 - 覆盖电平分组对比',
                xaxis_title='CQI分组',
                yaxis_title='覆盖电平 (dBm)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n28_rsrp, use_container_width=True)

    # 5. TA对比
    st.markdown("**📍 小区MR覆盖平均TA分组对比**")
    col_chart9, col_chart10 = st.columns(2)

    with col_chart9:
        if 'n41' in 分组分析:
            分组标签 = 分组分析['n41'].index.tolist()
            ta均值 = 分组分析['n41']['小区MR覆盖平均TA']['mean'].values

            fig_n41_ta = go.Figure(data=[go.Bar(
                x=分组标签,
                y=ta均值,
                marker_color='#20B2AA',
                text=np.round(ta均值, 2),
                textposition='outside'
            )])
            fig_n41_ta.update_layout(
                title='N41 - TA分组对比',
                xaxis_title='CQI分组',
                yaxis_title='TA',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n41_ta, use_container_width=True)

    with col_chart10:
        if 'n28' in 分组分析:
            分组标签 = 分组分析['n28'].index.tolist()
            ta均值 = 分组分析['n28']['小区MR覆盖平均TA']['mean'].values

            fig_n28_ta = go.Figure(data=[go.Bar(
                x=分组标签,
                y=ta均值,
                marker_color='#FF4500',
                text=np.round(ta均值, 2),
                textposition='outside'
            )])
            fig_n28_ta.update_layout(
                title='N28 - TA分组对比',
                xaxis_title='CQI分组',
                yaxis_title='TA',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n28_ta, use_container_width=True)

    # 6. 干扰电平对比
    st.markdown("**⚡ 小区上行平均干扰电平分组对比**")
    col_chart11, col_chart12 = st.columns(2)

    with col_chart11:
        if 'n41' in 分组分析:
            分组标签 = 分组分析['n41'].index.tolist()
            干扰均值 = 分组分析['n41']['小区上行平均干扰电平']['mean'].values

            fig_n41_interf = go.Figure(data=[go.Bar(
                x=分组标签,
                y=干扰均值,
                marker_color='#FF69B4',
                text=np.round(干扰均值, 2),
                textposition='outside'
            )])
            fig_n41_interf.update_layout(
                title='N41 - 干扰电平分组对比',
                xaxis_title='CQI分组',
                yaxis_title='干扰电平 (dBm)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n41_interf, use_container_width=True)

    with col_chart12:
        if 'n28' in 分组分析:
            分组标签 = 分组分析['n28'].index.tolist()
            干扰均值 = 分组分析['n28']['小区上行平均干扰电平']['mean'].values

            fig_n28_interf = go.Figure(data=[go.Bar(
                x=分组标签,
                y=干扰均值,
                marker_color='#B22222',
                text=np.round(干扰均值, 2),
                textposition='outside'
            )])
            fig_n28_interf.update_layout(
                title='N28 - 干扰电平分组对比',
                xaxis_title='CQI分组',
                yaxis_title='干扰电平 (dBm)',
                template='plotly_white',
                height=380,
                margin=dict(t=50)
            )
            st.plotly_chart(fig_n28_interf, use_container_width=True)

    # 7. 覆盖系数分组对比（如果数据中存在）
    if 'n41' in 分组分析 and '覆盖系数' in 分组分析['n41'].columns.get_level_values(0):
        st.markdown("**📐 覆盖系数分组对比**")
        st.caption("覆盖系数 = TA / 站间距，反映小区覆盖范围与理想覆盖的比例关系。值>1.0表示越区覆盖，<0.3表示覆盖不足。")
        col_chart13, col_chart14 = st.columns(2)

        with col_chart13:
            if 'n41' in 分组分析:
                分组标签 = 分组分析['n41'].index.tolist()
                覆盖系数均值 = 分组分析['n41']['覆盖系数']['mean'].values

                fig_n41_coef = go.Figure(data=[go.Bar(
                    x=分组标签,
                    y=覆盖系数均值,
                    marker_color='#32CD32',
                    text=np.round(覆盖系数均值, 3),
                    textposition='outside'
                )])
                fig_n41_coef.update_layout(
                    title='N41 - 覆盖系数分组对比',
                    xaxis_title='CQI分组',
                    yaxis_title='覆盖系数',
                    template='plotly_white',
                    height=380,
                    margin=dict(t=50),
                    yaxis=dict(range=[0, max(覆盖系数均值) * 1.2] if len(覆盖系数均值) > 0 else [0, 1])
                )
                # 添加参考线
                fig_n41_coef.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="越区阈值=1.0")
                fig_n41_coef.add_hline(y=0.3, line_dash="dash", line_color="orange", annotation_text="覆盖不足=0.3")
                st.plotly_chart(fig_n41_coef, use_container_width=True)

        with col_chart14:
            if 'n28' in 分组分析 and '覆盖系数' in 分组分析['n28'].columns.get_level_values(0):
                分组标签 = 分组分析['n28'].index.tolist()
                覆盖系数均值 = 分组分析['n28']['覆盖系数']['mean'].values

                fig_n28_coef = go.Figure(data=[go.Bar(
                    x=分组标签,
                    y=覆盖系数均值,
                    marker_color='#228B22',
                    text=np.round(覆盖系数均值, 3),
                    textposition='outside'
                )])
                fig_n28_coef.update_layout(
                    title='N28 - 覆盖系数分组对比',
                    xaxis_title='CQI分组',
                    yaxis_title='覆盖系数',
                    template='plotly_white',
                    height=380,
                    margin=dict(t=50),
                    yaxis=dict(range=[0, max(覆盖系数均值) * 1.2] if len(覆盖系数均值) > 0 else [0, 1])
                )
                # 添加参考线
                fig_n28_coef.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="越区阈值=1.0")
                fig_n28_coef.add_hline(y=0.3, line_dash="dash", line_color="orange", annotation_text="覆盖不足=0.3")
                st.plotly_chart(fig_n28_coef, use_container_width=True)

    # 8. 重叠覆盖采样点比例分组对比（如果数据中存在）
    if 'n41' in 分组分析 and '重叠覆盖采样点比例(%)' in 分组分析['n41'].columns.get_level_values(0):
        st.markdown("**🔀 重叠覆盖采样点比例分组对比**")
        st.caption("重叠覆盖采样点比例反映小区受到邻区干扰的程度。比例越高，说明该小区覆盖区域与邻区重叠越严重，干扰越大。")
        col_chart15, col_chart16 = st.columns(2)

        with col_chart15:
            if 'n41' in 分组分析:
                分组标签 = 分组分析['n41'].index.tolist()
                重叠比例均值 = 分组分析['n41']['重叠覆盖采样点比例(%)']['mean'].values

                fig_n41_overlap = go.Figure(data=[go.Bar(
                    x=分组标签,
                    y=重叠比例均值,
                    marker_color='#FF1493',
                    text=np.round(重叠比例均值, 2),
                    textposition='outside'
                )])
                fig_n41_overlap.update_layout(
                    title='N41 - 重叠覆盖比例分组对比',
                    xaxis_title='CQI分组',
                    yaxis_title='重叠覆盖采样点比例 (%)',
                    template='plotly_white',
                    height=380,
                    margin=dict(t=50)
                )
                st.plotly_chart(fig_n41_overlap, use_container_width=True)

        with col_chart16:
            if 'n28' in 分组分析 and '重叠覆盖采样点比例(%)' in 分组分析['n28'].columns.get_level_values(0):
                分组标签 = 分组分析['n28'].index.tolist()
                重叠比例均值 = 分组分析['n28']['重叠覆盖采样点比例(%)']['mean'].values

                fig_n28_overlap = go.Figure(data=[go.Bar(
                    x=分组标签,
                    y=重叠比例均值,
                    marker_color='#C71585',
                    text=np.round(重叠比例均值, 2),
                    textposition='outside'
                )])
                fig_n28_overlap.update_layout(
                    title='N28 - 重叠覆盖比例分组对比',
                    xaxis_title='CQI分组',
                    yaxis_title='重叠覆盖采样点比例 (%)',
                    template='plotly_white',
                    height=380,
                    margin=dict(t=50)
                )
                st.plotly_chart(fig_n28_overlap, use_container_width=True)

    # ========== 分组对比表格（表格部分）==========
    st.markdown("---")
    st.markdown('<p class="sub-header">📊 分组对比表格</p>', unsafe_allow_html=True)
    st.info("💡 **说明**：展示各CQI分组下各项指标的详细统计信息（均值、标准差、样本数）")

    col_n41_table, col_divider_table, col_n28_table = st.columns([10, 1, 10])

    with col_n41_table:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 分组统计</div>', unsafe_allow_html=True)
        if 'n41' in 分组分析:
            for 列 in 分组分析['n41'].columns.get_level_values(0).unique():
                with st.expander(f"**{列}**", expanded=True):
                    显示列 = 分组分析['n41'][列].reset_index()
                    显示列.columns = ['CQI分组', '均值', '标准差', '样本数']
                    st.dataframe(显示列.style.format({'均值': '{:.2f}', '标准差': '{:.2f}', '样本数': '{:.0f}'}), use_container_width=True)

    with col_divider_table:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)

    with col_n28_table:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 分组统计</div>', unsafe_allow_html=True)
        if 'n28' in 分组分析:
            for 列 in 分组分析['n28'].columns.get_level_values(0).unique():
                with st.expander(f"**{列}**", expanded=True):
                    显示列 = 分组分析['n28'][列].reset_index()
                    显示列.columns = ['CQI分组', '均值', '标准差', '样本数']
                    st.dataframe(显示列.style.format({'均值': '{:.2f}', '标准差': '{:.2f}', '样本数': '{:.0f}'}), use_container_width=True)

    # 分析总结
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 分析总结</p>', unsafe_allow_html=True)

    if 'n41' in 分组分析 and 'n28' in 分组分析:
        总结内容 = "<div class='highlight'><b>📊 分组分析总结</b><br><br>"

        # 获取各分组的CQI数据
        n41_cqi_groups = 分组分析['n41'].index.tolist()
        n28_cqi_groups = 分组分析['n28'].index.tolist()

        # 找出CQI最优分组
        n41_best_group = n41_cqi_groups[-1] if n41_cqi_groups else "无"
        n28_best_group = n28_cqi_groups[-1] if n28_cqi_groups else "无"

        总结内容 += "<b>1. CQI分组概况：</b><br>"
        总结内容 += f"• N41共有{len(n41_cqi_groups)}个分组: {', '.join(n41_cqi_groups)}<br>"
        总结内容 += f"• N28共有{len(n28_cqi_groups)}个分组: {', '.join(n28_cqi_groups)}<br>"

        # 下行速率分析
        if '下行用户平均速率(MBPS)' in 分组分析['n41'].columns.get_level_values(0):
            n41下行 = 分组分析['n41']['下行用户平均速率(MBPS)']['mean'].values
            n28下行 = 分组分析['n28']['下行用户平均速率(MBPS)']['mean'].values

            n41_max_rate = max(n41下行)
            n28_max_rate = max(n28下行)
            n41_min_rate = min(n41下行)
            n28_min_rate = min(n28下行)

            总结内容 += "<br><b>2. 下行速率分析：</b><br>"
            总结内容 += f"• N41速率范围: {n41_min_rate:.2f} ~ {n41_max_rate:.2f} Mbps (跨度: {n41_max_rate - n41_min_rate:.2f} Mbps)<br>"
            总结内容 += f"• N28速率范围: {n28_min_rate:.2f} ~ {n28_max_rate:.2f} Mbps (跨度: {n28_max_rate - n28_min_rate:.2f} Mbps)<br>"

        # 覆盖电平分析
        if '小区MR覆盖平均电平' in 分组分析['n41'].columns.get_level_values(0):
            n41_rsrp = 分组分析['n41']['小区MR覆盖平均电平']['mean'].values
            n28_rsrp = 分组分析['n28']['小区MR覆盖平均电平']['mean'].values

            总结内容 += "<br><b>3. 覆盖电平分析：</b><br>"
            总结内容 += f"• N41覆盖电平随CQI分组递增而{'改善' if n41_rsrp[-1] > n41_rsrp[0] else '下降'}<br>"
            总结内容 += f"• N28覆盖电平随CQI分组递增而{'改善' if n28_rsrp[-1] > n28_rsrp[0] else '下降'}<br>"

        # SINR分析
        if '小区MR覆盖平均SINR' in 分组分析['n41'].columns.get_level_values(0):
            n41_sinr = 分组分析['n41']['小区MR覆盖平均SINR']['mean'].values
            n28_sinr = 分组分析['n28']['小区MR覆盖平均SINR']['mean'].values

            总结内容 += "<br><b>4. SINR分析：</b><br>"
            总结内容 += f"• N41最优CQI分组SINR均值: {n41_sinr[-1]:.2f} dB<br>"
            总结内容 += f"• N28最优CQI分组SINR均值: {n28_sinr[-1]:.2f} dB<br>"

        # 覆盖系数分析
        if '覆盖系数' in 分组分析['n41'].columns.get_level_values(0):
            n41_coef = 分组分析['n41']['覆盖系数']['mean'].values
            n28_coef = 分组分析['n28']['覆盖系数']['mean'].values

            总结内容 += "<br><b>5. 覆盖系数分析：</b><br>"
            总结内容 += f"• N41覆盖系数范围: {min(n41_coef):.3f} ~ {max(n41_coef):.3f}<br>"
            总结内容 += f"• N28覆盖系数范围: {min(n28_coef):.3f} ~ {max(n28_coef):.3f}<br>"
            # 判断是否有越区覆盖问题
            n41_越区 = any(v > 1.0 for v in n41_coef)
            n28_越区 = any(v > 1.0 for v in n28_coef)
            if n41_越区 or n28_越区:
                总结内容 += f"• {'N41存在' if n41_越区 else ''}{'、' if n41_越区 and n28_越区 else ''}{'N28存在' if n28_越区 else ''}越区覆盖风险（覆盖系数>1.0）<br>"

        # 重叠覆盖采样点比例分析
        if '重叠覆盖采样点比例(%)' in 分组分析['n41'].columns.get_level_values(0):
            n41_overlap = 分组分析['n41']['重叠覆盖采样点比例(%)']['mean'].values
            n28_overlap = 分组分析['n28']['重叠覆盖采样点比例(%)']['mean'].values

            总结内容 += "<br><b>6. 重叠覆盖分析：</b><br>"
            总结内容 += f"• N41重叠覆盖比例范围: {min(n41_overlap):.2f}% ~ {max(n41_overlap):.2f}%<br>"
            总结内容 += f"• N28重叠覆盖比例范围: {min(n28_overlap):.2f}% ~ {max(n28_overlap):.2f}%<br>"
            # 判断是否有严重的重叠覆盖问题
            n41_高重叠 = any(v > 30 for v in n41_overlap)
            n28_高重叠 = any(v > 30 for v in n28_overlap)
            if n41_高重叠 or n28_高重叠:
                总结内容 += f"• {'注意：N41' if n41_高重叠 else ''}{'、' if n41_高重叠 and n28_高重叠 else ''}{'N28' if n28_高重叠 else ''}存在较严重的重叠覆盖问题（比例>30%），可能导致干扰<br>"

        总结内容 += "<br><b>7. 关键发现：</b><br>"
        总结内容 += "• CQI优良率与各项性能指标呈现明显的正相关趋势<br>"
        总结内容 += "• 随着CQI分组等级提高，下行速率和SINR通常会提升<br>"
        总结内容 += "• 高CQI分组小区的各项指标普遍优于低CQI分组小区<br>"
        if '覆盖系数' in 分组分析['n41'].columns.get_level_values(0):
            总结内容 += "• 覆盖系数可反映小区覆盖范围是否合理，过高可能导致越区干扰<br>"
        if '重叠覆盖采样点比例(%)' in 分组分析['n41'].columns.get_level_values(0):
            总结内容 += "• 重叠覆盖采样点比例高说明邻区干扰严重，会影响CQI和SINR<br>"

        总结内容 += "<br><b>8. 优化建议：</b><br>"
        总结内容 += "• 关注低CQI分组小区的性能瓶颈<br>"
        总结内容 += "• 提升CQI优良率可有效改善用户体验<br>"
        总结内容 += "• 针对不同CQI等级制定差异化的优化策略<br>"
        if '覆盖系数' in 分组分析['n41'].columns.get_level_values(0):
            总结内容 += "• 检查覆盖系数>1.0的小区，考虑调整天线下倾角或功率控制越区覆盖<br>"
        if '重叠覆盖采样点比例(%)' in 分组分析['n41'].columns.get_level_values(0):
            总结内容 += "• 优化重叠覆盖严重区域的频率规划和邻区关系，降低干扰<br>"

        总结内容 += "</div>"
        st.markdown(总结内容, unsafe_allow_html=True)


def 渲染制式对比多维度交叉分析(分析器: CQI分析器):
    """渲染多维度交叉分析的网络制式对比"""
    st.markdown("""
    <div class="highlight">
    <b>🔄 多维度交叉分析说明：</b><br>
    通过覆盖、SINR、TA、CQI、速率等多个维度的交叉分析，深入挖掘网络性能瓶颈和优化方向。
    </div>
    """, unsafe_allow_html=True)
    
    # 使用子标签页组织3个分析模块（TA分层和条件分组已合并到距离覆盖分析）
    子标签 = st.tabs([
        "📊 1.三维散点图分析",
        "🎯 2.四象限分析",
        "🔍 3.CQI不达标根因分析"
    ])
    
    # ========== 1. 三维散点图分析 ==========
    with 子标签[0]:
        st.markdown("""
        <div class="highlight">
        <b>📊 三维散点图分析说明：</b><br>
        通过三维散点图展示覆盖电平、SINR与CQI/速率之间的关系，识别网络质量的分布模式。<br><br>
        <b>📈 图表解读：</b><br>
        • <b>X轴</b>：覆盖电平（dBm），值越大表示信号越强<br>
        • <b>Y轴</b>：SINR（dB），值越大表示干扰越小、信号质量越好<br>
        • <b>颜色</b>：CQI优良率，颜色越暖（红/黄）表示CQI越好<br>
        • <b>点大小</b>：下行速率，点越大表示速率越高<br>
        <br>
        <b>💡 分析价值：</b>直观展示覆盖、干扰、CQI、速率四者的关系，识别异常分布模式
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<p class="sub-header">📊 三维散点图 - 覆盖×SINR×CQI/速率</p>', unsafe_allow_html=True)
        
        三维数据 = 分析器.三维散点图分析_按制式()
        
        # 添加样本数选择滑块
        总样本数_n41 = len(三维数据['n41']) if 'n41' in 三维数据 else 0
        总样本数_n28 = len(三维数据['n28']) if 'n28' in 三维数据 else 0
        最大样本数 = max(总样本数_n41, 总样本数_n28)
        
        if 最大样本数 > 0:
            样本数选项 = [2000, 4000, 6000, 8000, 10000]
            可选样本数 = [x for x in 样本数选项 if x <= 最大样本数] + [最大样本数]
            可选样本数 = sorted(list(set(可选样本数)))
            
            if len(可选样本数) > 1:
                选择样本数 = st.select_slider(
                    "选择散点图样本数量（过多样本可能导致浏览器卡顿）",
                    options=可选样本数,
                    value=min(4000, 最大样本数),
                    key="scatter_sample_size"
                )
            else:
                选择样本数 = 最大样本数
                st.info(f"数据样本共 {最大样本数} 个，将显示全部样本")
        else:
            选择样本数 = 2000
        
        col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
        
        with col_n41:
            st.markdown('<div class="network-type-header n41-header">📡 N41 - 三维关系</div>', unsafe_allow_html=True)
            if 'n41' in 三维数据 and len(三维数据['n41']) > 0:
                st.caption(f"总样本数: {len(三维数据['n41'])} | 显示样本数: {min(选择样本数, len(三维数据['n41']))}")
                数据 = 三维数据['n41'].sample(min(选择样本数, len(三维数据['n41']))).copy()

                # 确保size列为正数（plotly要求size必须>0）
                数据['速率大小'] = 数据['下行用户平均速率(MBPS)'].clip(lower=0.1)

                # 覆盖×SINR×CQI
                fig1 = px.scatter(
                    数据, x='小区MR覆盖平均电平', y='小区MR覆盖平均SINR',
                    color='CQI优良率', size='速率大小',
                    color_continuous_scale='Blues',
                    title="N41: 覆盖×SINR×CQI(颜色)×速率(大小)",
                    height=450
                )
                fig1.update_layout(template="plotly_white")
                st.plotly_chart(fig1, use_container_width=True)
                
                # 分析总结
                corr_覆盖_sinr = 数据['小区MR覆盖平均电平'].corr(数据['小区MR覆盖平均SINR'])
                corr_覆盖_cqi = 数据['小区MR覆盖平均电平'].corr(数据['CQI优良率'])
                corr_sinr_cqi = 数据['小区MR覆盖平均SINR'].corr(数据['CQI优良率'])
                
                st.markdown(f"""
                <div class="success-box">
                <b>📊 N41三维关系分析：</b><br>
                • 覆盖与SINR相关性: <b>{corr_覆盖_sinr:.3f}</b><br>
                • 覆盖与CQI相关性: <b>{corr_覆盖_cqi:.3f}</b><br>
                • SINR与CQI相关性: <b>{corr_sinr_cqi:.3f}</b><br>
                • 样本数: {len(数据):,}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("N41数据不足")
        
        with col_divider:
            st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
        
        with col_n28:
            st.markdown('<div class="network-type-header n28-header">📡 N28 - 三维关系</div>', unsafe_allow_html=True)
            if 'n28' in 三维数据 and len(三维数据['n28']) > 0:
                st.caption(f"总样本数: {len(三维数据['n28'])} | 显示样本数: {min(选择样本数, len(三维数据['n28']))}")
                数据 = 三维数据['n28'].sample(min(选择样本数, len(三维数据['n28']))).copy()

                # 确保size列为正数（plotly要求size必须>0）
                数据['速率大小'] = 数据['下行用户平均速率(MBPS)'].clip(lower=0.1)

                fig2 = px.scatter(
                    数据, x='小区MR覆盖平均电平', y='小区MR覆盖平均SINR',
                    color='CQI优良率', size='速率大小',
                    color_continuous_scale='Reds',
                    title="N28: 覆盖×SINR×CQI(颜色)×速率(大小)",
                    height=450
                )
                fig2.update_layout(template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True)
                
                corr_覆盖_sinr = 数据['小区MR覆盖平均电平'].corr(数据['小区MR覆盖平均SINR'])
                corr_覆盖_cqi = 数据['小区MR覆盖平均电平'].corr(数据['CQI优良率'])
                corr_sinr_cqi = 数据['小区MR覆盖平均SINR'].corr(数据['CQI优良率'])
                
                st.markdown(f"""
                <div class="success-box">
                <b>📊 N28三维关系分析：</b><br>
                • 覆盖与SINR相关性: <b>{corr_覆盖_sinr:.3f}</b><br>
                • 覆盖与CQI相关性: <b>{corr_覆盖_cqi:.3f}</b><br>
                • SINR与CQI相关性: <b>{corr_sinr_cqi:.3f}</b><br>
                • 样本数: {len(数据):,}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("N28数据不足")
    
    # ========== 2. 四象限分析 ==========
    with 子标签[1]:
        st.markdown("""
        <div class="highlight">
        <b>🎯 四象限分析说明：</b><br>
        通过覆盖电平和SINR两个维度，将小区划分为四个象限，识别不同网络质量特征的小区群体。<br><br>
        <b>📊 四象限定义：</b><br>
        • <b>第一象限（好覆盖+好SINR）</b>：覆盖>-90dBm且SINR>15dB，网络质量优良<br>
        • <b>第二象限（差覆盖+好SINR）</b>：覆盖≤-90dBm但SINR>15dB，需增强覆盖<br>
        • <b>第三象限（差覆盖+差SINR）</b>：覆盖≤-90dBm且SINR≤15dB，需综合优化<br>
        • <b>第四象限（好覆盖+差SINR）</b>：覆盖>-90dBm但SINR≤15dB，存在干扰问题<br>
        <br>
        <b>💡 应用价值：</b>快速定位问题小区类型，制定针对性优化策略
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<p class="sub-header">🎯 四象限矩阵 - 覆盖×SINR</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            覆盖阈值 = st.number_input("覆盖阈值(dBm)", value=-90, key="覆盖阈值")
        with col2:
            SINR阈值 = st.number_input("SINR阈值(dB)", value=15, key="SINR阈值")
        
        四象限结果 = 分析器.四象限分析_按制式(覆盖阈值, SINR阈值)
        
        col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
        
        with col_n41:
            st.markdown('<div class="network-type-header n41-header">📡 N41 - 四象限</div>', unsafe_allow_html=True)
            if 'n41' in 四象限结果 and len(四象限结果['n41']) > 0:
                st.dataframe(四象限结果['n41'], use_container_width=True)
                
                # 饼图展示占比
                fig = px.pie(
                    四象限结果['n41'], values='占比(%)', names='象限',
                    title="N41: 四象限分布", hole=0.3,
                    color_discrete_sequence=['#1E90FF', '#4169E1', '#87CEEB', '#B0C4DE']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("N41数据不足")
        
        with col_divider:
            st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
        
        with col_n28:
            st.markdown('<div class="network-type-header n28-header">📡 N28 - 四象限</div>', unsafe_allow_html=True)
            if 'n28' in 四象限结果 and len(四象限结果['n28']) > 0:
                st.dataframe(四象限结果['n28'], use_container_width=True)
                
                fig = px.pie(
                    四象限结果['n28'], values='占比(%)', names='象限',
                    title="N28: 四象限分布", hole=0.3,
                    color_discrete_sequence=['#FF6B6B', '#FF8E53', '#FFA07A', '#FFB6C1']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("N28数据不足")
    
    # ========== 3. CQI不达标根因分析 ==========
    with 子标签[2]:
        st.markdown('<p class="sub-header">🔍 CQI不达标根因分析 - 问题定位</p>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="highlight">
        <b>🔍 根因分析说明：</b><br>
        识别CQI不达标小区的根因类型：覆盖问题、干扰问题、越区覆盖等。<br>
        ⭐ N41和N28可分别设置不同的CQI达标阈值（因两制式性能基准不同）。<br>
        ⭐ 越区覆盖使用<b>覆盖系数>0.65</b>作为判断标准（TA/站间距）。
        </div>
        """, unsafe_allow_html=True)
        
        # ⭐ 使用两个独立的滑块分别设置N41和N28的阈值
        col_n41_th, col_n28_th = st.columns(2)
        with col_n41_th:
            n41阈值 = st.slider("N41 CQI达标阈值(%)", 70, 95, 85, key="n41_CQI根因阈值")
        with col_n28_th:
            n28阈值 = st.slider("N28 CQI达标阈值(%)", 70, 95, 75, key="n28_CQI根因阈值")
        
        # 传入字典形式的阈值
        CQI阈值 = {'n41': n41阈值, 'n28': n28阈值}
        根因结果 = 分析器.CQI不达标根因分析_按制式(CQI阈值)
        
        col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
        
        with col_n41:
            st.markdown(f'<div class="network-type-header n41-header">📡 N41 - 根因分析 (阈值:{n41阈值}%)</div>', unsafe_allow_html=True)
            if 'n41' in 根因结果:
                st.metric("不达标比例", f"{根因结果['n41']['不达标比例']:.2f}%")
                st.metric("不达标小区数", f"{根因结果['n41']['不达标小区数']:,} / {根因结果['n41']['总小区数']:,}")
                
                if len(根因结果['n41']['根因统计']) > 0:
                    st.dataframe(根因结果['n41']['根因统计'], use_container_width=True)
                    
                    # 根因分布图
                    fig = px.bar(
                        根因结果['n41']['根因统计'], x='根因类型', y='占比(%)',
                        title="N41: CQI不达标根因分布",
                        color='占比(%)', color_continuous_scale='Blues',
                        height=400
                    )
                    fig.update_layout(template="plotly_white", xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("N41数据不足")
        
        with col_divider:
            st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
        
        with col_n28:
            st.markdown(f'<div class="network-type-header n28-header">📡 N28 - 根因分析 (阈值:{n28阈值}%)</div>', unsafe_allow_html=True)
            if 'n28' in 根因结果:
                st.metric("不达标比例", f"{根因结果['n28']['不达标比例']:.2f}%")
                st.metric("不达标小区数", f"{根因结果['n28']['不达标小区数']:,} / {根因结果['n28']['总小区数']:,}")
                
                if len(根因结果['n28']['根因统计']) > 0:
                    st.dataframe(根因结果['n28']['根因统计'], use_container_width=True)
                    
                    fig = px.bar(
                        根因结果['n28']['根因统计'], x='根因类型', y='占比(%)',
                        title="N28: CQI不达标根因分布",
                        color='占比(%)', color_continuous_scale='Reds',
                        height=400
                    )
                    fig.update_layout(template="plotly_white", xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("N28数据不足")

    # ========== 总体分析总结 ==========
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 多维度交叉分析总结</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="highlight">
    <b>🔄 多维度交叉分析洞察：</b><br><br>

    <b>1. 三维关系洞察：</b><br>
    • 通过覆盖×SINR×CQI的三维分析，可以识别出网络质量的关键瓶颈<br>
    • 颜色深浅代表CQI水平，气泡大小代表下行速率<br><br>

    <b>2. 四象限分析应用：</b><br>
    • 象限1(好覆盖+好SINR)：网络质量优良，可作为标杆<br>
    • 象限2(好覆盖+差SINR)：存在干扰问题，需优化干扰<br>
    • 象限3(差覆盖+好SINR)：覆盖不足，需增强覆盖<br>
    • 象限4(差覆盖+差SINR)：综合问题，需全面优化<br><br>

    <b>3. 根因分析指导：</b><br>
    • 通过量化各类问题的占比，明确优化优先级<br>
    • 针对主要根因制定专项优化方案，提高优化效率<br><br>

    <b>💡 提示：</b> TA分层分析和条件分组分析已合并到「📏 距离覆盖分析」标签页
    </div>
    """, unsafe_allow_html=True)


def 渲染制式对比距离覆盖分析(分析器: CQI分析器):
    """渲染距离覆盖分析的制式对比 - 整合覆盖系数、TA分层、条件分组"""
    st.markdown("""
    <div class="highlight">
    <b>📏 距离覆盖分析说明：</b><br>
    综合分析覆盖系数、TA距离、覆盖电平等多个维度，全面评估网络覆盖合理性。
    <br>• <b>覆盖系数</b> = TA / 站间距 | <b>TA</b> = 时间提前量(米) | <b>覆盖电平</b> = RSRP(dBm)
    </div>
    """, unsafe_allow_html=True)
    
    # 覆盖系数分析内容（直接显示，无子标签）
    st.markdown('<p class="sub-header">📊 覆盖系数分析 - TA/站间距评估覆盖合理性</p>', unsafe_allow_html=True)
    
    st.info("""
    📊 **覆盖系数说明**：覆盖系数 = TA / 站间距
    • <0.3：近覆盖 | 0.3~0.65：适中覆盖 | >0.65：越区覆盖
    • 需要原始数据包含「方向角站间距（米）」和「小区MR覆盖平均TA」字段
    """)
    
    # 覆盖系数统计
    覆盖系数统计 = 分析器.覆盖系数统计_按制式()
    
    if len(覆盖系数统计) == 0:
        st.warning("⚠️ 数据中未找到覆盖系数字段")
        return
    
    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
    
    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 覆盖系数统计</div>', unsafe_allow_html=True)
        if 'n41' in 覆盖系数统计:
            数据 = 覆盖系数统计['n41']
            st.metric("样本数", f"{数据['样本数']:,}")
            st.metric("平均值", f"{数据['平均值']:.3f}")
            st.metric("中位数", f"{数据['中位数']:.3f}")
            st.metric("标准差", f"{数据['标准差']:.3f}")
            st.markdown("---")
            st.markdown("**📊 覆盖距离分布**")
            st.write(f"• 覆盖较近(<0.3): {数据['覆盖较近(<0.3)']:,} ({数据['覆盖较近(<0.3)']/数据['样本数']*100:.1f}%)")
            st.write(f"• 覆盖适中(0.3-0.65): {数据['覆盖适中(0.3-0.65)']:,} ({数据['覆盖适中(0.3-0.65)']/数据['样本数']*100:.1f}%)")
            st.write(f"• 越区覆盖(>0.65): {数据['越区覆盖(>0.65)']:,} ({数据['越区覆盖(>0.65)']/数据['样本数']*100:.1f}%)")
    
    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
    
    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 覆盖系数统计</div>', unsafe_allow_html=True)
        if 'n28' in 覆盖系数统计:
            数据 = 覆盖系数统计['n28']
            st.metric("样本数", f"{数据['样本数']:,}")
            st.metric("平均值", f"{数据['平均值']:.3f}")
            st.metric("中位数", f"{数据['中位数']:.3f}")
            st.metric("标准差", f"{数据['标准差']:.3f}")
            st.markdown("---")
            st.markdown("**📊 覆盖距离分布**")
            st.write(f"• 覆盖较近(<0.3): {数据['覆盖较近(<0.3)']:,} ({数据['覆盖较近(<0.3)']/数据['样本数']*100:.1f}%)")
            st.write(f"• 覆盖适中(0.3-0.65): {数据['覆盖适中(0.3-0.65)']:,} ({数据['覆盖适中(0.3-0.65)']/数据['样本数']*100:.1f}%)")
            st.write(f"• 越区覆盖(>0.65): {数据['越区覆盖(>0.65)']:,} ({数据['越区覆盖(>0.65)']/数据['样本数']*100:.1f}%)")
    
    st.markdown("---")
    
    # 2. 覆盖系数分布直方图
    st.markdown('<p class="sub-header">📈 覆盖系数分布对比</p>', unsafe_allow_html=True)
    
    col_hist1, col_hist2 = st.columns(2)
    
    with col_hist1:
        if 'n41' in 覆盖系数统计:
            数据 = 覆盖系数统计['n41']['覆盖系数数据']
            import plotly.graph_objects as go
            import numpy as np
            
            # 创建自定义区间：0-0.5细分(步长0.05)，0.5-2.0适度细分(步长0.1)，>2.0合并为一个区间
            区间边界 = list(np.arange(0, 0.5, 0.05)) + list(np.arange(0.5, 2.0, 0.1)) + [float('inf')]
            区间标签 = [f"{区间边界[i]:.2f}-{区间边界[i+1]:.2f}" if 区间边界[i+1] != float('inf') else ">2.00" for i in range(len(区间边界)-1)]
            
            # 使用pd.cut手动分箱
            分箱结果 = pd.cut(数据, bins=区间边界, labels=区间标签, include_lowest=True, right=False)
            频数统计 = 分箱结果.value_counts().sort_index()
            
            # 合并>2.00的区间标签
            频数统计索引 = [label if label != ">2.00" else ">2.00" for label in 频数统计.index]
            
            fig_n41 = go.Figure(data=[go.Bar(
                x=频数统计.index,
                y=频数统计.values,
                marker_color='#1E90FF',
                name='小区数量'
            )])
            # 设置x轴刻度，只显示部分标签避免拥挤
            tick_indices = list(range(0, 15, 2)) + [len(频数统计)-1]  # 前15个每2个显示一个，最后一个
            tick_texts = [频数统计.index[i] for i in tick_indices[:-1]] + [">2.00"]
            fig_n41.update_xaxes(
                tickmode='array',
                tickvals=[频数统计.index[i] for i in tick_indices[:-1]] + [频数统计.index[-1]],
                ticktext=tick_texts,
                tickangle=45
            )
            fig_n41.add_vline(x=5, line_dash="dash", line_color="green", annotation_text="适中下限=0.3")  # 0.3对应第6个区间(0.25-0.30)
            fig_n41.add_vline(x=11, line_dash="dash", line_color="orange", annotation_text="适中上限=0.65")  # 0.65在0.60-0.70之间
            fig_n41.add_vline(x=15, line_dash="dash", line_color="red", annotation_text="越区阈值=1.0")  # 1.0对应第16个区间
            fig_n41.update_layout(
                template="plotly_white",
                height=400,
                title="N41 - 覆盖系数分布",
                xaxis_title="覆盖系数区间",
                yaxis_title="小区数量",
                bargap=0.1
            )
            st.plotly_chart(fig_n41, use_container_width=True)
    
    with col_hist2:
        if 'n28' in 覆盖系数统计:
            数据 = 覆盖系数统计['n28']['覆盖系数数据']
            import plotly.graph_objects as go
            import numpy as np
            
            # 创建自定义区间：0-0.5细分(步长0.05)，0.5-2.0适度细分(步长0.1)，>2.0合并为一个区间
            区间边界 = list(np.arange(0, 0.5, 0.05)) + list(np.arange(0.5, 2.0, 0.1)) + [float('inf')]
            区间标签 = [f"{区间边界[i]:.2f}-{区间边界[i+1]:.2f}" if 区间边界[i+1] != float('inf') else ">2.00" for i in range(len(区间边界)-1)]
            
            # 使用pd.cut手动分箱
            分箱结果 = pd.cut(数据, bins=区间边界, labels=区间标签, include_lowest=True, right=False)
            频数统计 = 分箱结果.value_counts().sort_index()
            
            fig_n28 = go.Figure(data=[go.Bar(
                x=频数统计.index,
                y=频数统计.values,
                marker_color='#FF6B6B',
                name='小区数量'
            )])
            # 设置x轴刻度，只显示部分标签避免拥挤
            tick_indices = list(range(0, 15, 2)) + [len(频数统计)-1]
            tick_texts = [频数统计.index[i] for i in tick_indices[:-1]] + [">2.00"]
            fig_n28.update_xaxes(
                tickmode='array',
                tickvals=[频数统计.index[i] for i in tick_indices[:-1]] + [频数统计.index[-1]],
                ticktext=tick_texts,
                tickangle=45
            )
            fig_n28.add_vline(x=5, line_dash="dash", line_color="green", annotation_text="适中下限=0.3")
            fig_n28.add_vline(x=11, line_dash="dash", line_color="orange", annotation_text="适中上限=0.65")
            fig_n28.add_vline(x=15, line_dash="dash", line_color="red", annotation_text="越区阈值=1.0")
            fig_n28.update_layout(
                template="plotly_white",
                height=400,
                title="N28 - 覆盖系数分布",
                xaxis_title="覆盖系数区间",
                yaxis_title="小区数量",
                bargap=0.1
            )
            st.plotly_chart(fig_n28, use_container_width=True)
    
    st.markdown("---")
    
    # 3. 覆盖系数与CQI相关性分析
    st.markdown('<p class="sub-header">🔗 覆盖系数与网络质量相关性</p>', unsafe_allow_html=True)
    
    相关性结果 = 分析器.覆盖系数与CQI相关性_按制式()
    
    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
    
    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 相关性分析</div>', unsafe_allow_html=True)
        if 'n41' in 相关性结果:
            图表数据 = pd.DataFrame(相关性结果['n41'])
            fig_n41 = px.bar(
                图表数据,
                x="相关系数",
                y="指标",
                orientation='h',
                color="相关系数",
                color_continuous_scale="Blues",
                title="N41 - 覆盖系数与各指标相关性",
                text_auto=".3f"
            )
            fig_n41.update_layout(template="plotly_white", yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_n41, use_container_width=True)
            st.dataframe(图表数据[['指标', '相关系数', '显著性', '强度']], use_container_width=True)
    
    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
    
    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 相关性分析</div>', unsafe_allow_html=True)
        if 'n28' in 相关性结果:
            图表数据 = pd.DataFrame(相关性结果['n28'])
            fig_n28 = px.bar(
                图表数据,
                x="相关系数",
                y="指标",
                orientation='h',
                color="相关系数",
                color_continuous_scale="Reds",
                title="N28 - 覆盖系数与各指标相关性",
                text_auto=".3f"
            )
            fig_n28.update_layout(template="plotly_white", yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_n28, use_container_width=True)
            st.dataframe(图表数据[['指标', '相关系数', '显著性', '强度']], use_container_width=True)
    
    st.markdown("---")
    
    # 4. 覆盖系数分层分析
    st.markdown('<p class="sub-header">📊 覆盖系数分层分析</p>', unsafe_allow_html=True)
    
    分层结果 = 分析器.多维度分层分析_按制式(维度='覆盖系数')
    
    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
    
    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 分层分析</div>', unsafe_allow_html=True)
        if 'n41' in 分层结果 and len(分层结果['n41']) > 0:
            st.dataframe(分层结果['n41'], use_container_width=True)
            
            # 双轴图：CQI和速率随覆盖系数档位变化
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go
            
            fig = make_subplots(rows=1, cols=2, subplot_titles=('CQI随覆盖系数变化', '速率随覆盖系数变化'))
            fig.add_trace(
                go.Bar(x=分层结果['n41']['档位'], y=分层结果['n41']['平均CQI'], 
                       name='CQI', marker_color='#1E90FF'),
                row=1, col=1
            )
            fig.add_trace(
                go.Bar(x=分层结果['n41']['档位'], y=分层结果['n41']['平均下行速率'], 
                       name='速率', marker_color='#4169E1'),
                row=1, col=2
            )
            fig.update_layout(template='plotly_white', height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
    
    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 分层分析</div>', unsafe_allow_html=True)
        if 'n28' in 分层结果 and len(分层结果['n28']) > 0:
            st.dataframe(分层结果['n28'], use_container_width=True)
            
            # 双轴图：CQI和速率随覆盖系数档位变化
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go
            
            fig = make_subplots(rows=1, cols=2, subplot_titles=('CQI随覆盖系数变化', '速率随覆盖系数变化'))
            fig.add_trace(
                go.Bar(x=分层结果['n28']['档位'], y=分层结果['n28']['平均CQI'], 
                       name='CQI', marker_color='#FF6B6B'),
                row=1, col=1
            )
            fig.add_trace(
                go.Bar(x=分层结果['n28']['档位'], y=分层结果['n28']['平均下行速率'], 
                       name='速率', marker_color='#FF8E53'),
                row=1, col=2
            )
            fig.update_layout(template='plotly_white', height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 5. 四象限分析
    st.markdown('<p class="sub-header">🎯 覆盖系数×覆盖电平 四象限分析</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        覆盖系数阈值 = st.number_input("覆盖系数阈值", value=0.7, step=0.1, key="覆盖系数阈值")
    with col2:
        覆盖电平阈值 = st.number_input("覆盖电平阈值(dBm)", value=-90, key="四象限覆盖电平阈值")
    
    四象限结果 = 分析器.覆盖系数四象限分析_按制式(覆盖系数阈值, 覆盖电平阈值)
    
    col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
    
    with col_n41:
        st.markdown('<div class="network-type-header n41-header">📡 N41 - 四象限分布</div>', unsafe_allow_html=True)
        if 'n41' in 四象限结果 and len(四象限结果['n41']) > 0:
            st.dataframe(四象限结果['n41'], use_container_width=True)
            
            fig = px.pie(
                四象限结果['n41'], values='占比(%)', names='象限',
                title="N41: 四象限分布", hole=0.3,
                color_discrete_sequence=['#1E90FF', '#4169E1', '#87CEEB', '#B0C4DE']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_divider:
        st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
    
    with col_n28:
        st.markdown('<div class="network-type-header n28-header">📡 N28 - 四象限分布</div>', unsafe_allow_html=True)
        if 'n28' in 四象限结果 and len(四象限结果['n28']) > 0:
            st.dataframe(四象限结果['n28'], use_container_width=True)
            
            fig = px.pie(
                四象限结果['n28'], values='占比(%)', names='象限',
                title="N28: 四象限分布", hole=0.3,
                color_discrete_sequence=['#FF6B6B', '#FF8E53', '#FFA07A', '#FFB6C1']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # 分析总结 - 横跨左右两列显示
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 覆盖系数分析总结</p>', unsafe_allow_html=True)
    
    if len(覆盖系数统计) > 0:
        总结内容 = "<div class='highlight'><b>📊 覆盖系数分析洞察</b><br><br>"
        
        总结内容 += "<b>1. 覆盖系数统计摘要：</b><br>"
        for 制式, 数据 in 覆盖系数统计.items():
            越区占比 = 数据['越区覆盖(>0.65)'] / 数据['样本数'] * 100
            总结内容 += f"• <b>{制式.upper()}</b>: 均值={数据['平均值']:.3f}, 中位数={数据['中位数']:.3f}, 越区覆盖占比={越区占比:.1f}%<br>"
        
        if len(相关性结果) > 0:
            总结内容 += "<br><b>2. 覆盖系数与CQI关系：</b><br>"
            for 制式, 列表 in 相关性结果.items():
                if len(列表) > 0:
                    cqi_corr = next((x for x in 列表 if x['指标'] == 'CQI优良率'), None)
                    if cqi_corr:
                        方向 = "负相关" if cqi_corr['相关系数'] < 0 else "正相关"
                        总结内容 += f"• <b>{制式.upper()}</b>: 覆盖系数与CQI呈{cqi_corr['强度']}{方向}(r={cqi_corr['相关系数']:.3f})<br>"
        
        总结内容 += "<br><b>3. 优化建议：</b><br>"
        总结内容 += "• 关注覆盖系数>0.65的越区覆盖小区，可能需要调整下倾角或功率<br>"
        总结内容 += "• 覆盖系数<0.3的小区可能存在覆盖不足，建议检查天线方位角<br>"
        总结内容 += "• 覆盖系数在0.3~0.65范围内的网络质量通常较好，可作为标杆<br>"
        总结内容 += "• 结合四象限分析，优先处理'差覆盖+过远覆盖距离'的小区"
        
        总结内容 += "</div>"
        st.markdown(总结内容, unsafe_allow_html=True)


def 渲染制式对比数据导出(分析器: CQI分析器):
    """渲染数据导出的网络制式对比"""
    st.markdown('<p class="sub-header">📥 数据导出</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="highlight">
    <b>📥 导出说明：</b><br>
    生成包含N41和N28两个网络制式完整分析结果的Excel报告，包含新增的覆盖系数分析结果。
    </div>
    """, unsafe_allow_html=True)

    分组数据 = 分析器.按网络制式分组()
    
    # 显示数据量统计
    if 'n41' in 分组数据 and 'n28' in 分组数据:
        col_n41, col_divider, col_n28 = st.columns([10, 1, 10])
        
        with col_n41:
            st.markdown('<div class="network-type-header n41-header">📡 N41 数据概况</div>', unsafe_allow_html=True)
            st.metric("数据量", f"{len(分组数据['n41']):,} 条")
            # 显示覆盖系数统计
            if '覆盖系数' in 分组数据['n41'].columns:
                越区数 = len(分组数据['n41'][分组数据['n41']['覆盖系数'] > 0.65])
                st.metric("越区覆盖小区", f"{越区数:,} 条")
        
        with col_divider:
            st.markdown('<div class="comparison-divider"></div>', unsafe_allow_html=True)
        
        with col_n28:
            st.markdown('<div class="network-type-header n28-header">📡 N28 数据概况</div>', unsafe_allow_html=True)
            st.metric("数据量", f"{len(分组数据['n28']):,} 条")
            # 显示覆盖系数统计
            if '覆盖系数' in 分组数据['n28'].columns:
                越区数 = len(分组数据['n28'][分组数据['n28']['覆盖系数'] > 0.65])
                st.metric("越区覆盖小区", f"{越区数:,} 条")

    st.markdown("---")

    # 导出完整分析报告
    st.markdown('<p class="sub-header">📊 导出完整分析报告</p>', unsafe_allow_html=True)
    
    st.info("""
    📊 报告内容清单（18个工作表）：
    • N41原始数据 / N28原始数据  
    • 统计摘要
    • N41_CQI对速率影响 / N28_CQI对速率影响
    • N41_影响CQI的因素 / N28_影响CQI的因素
    • N41_相关性矩阵 / N28_相关性矩阵
    • N41_拐点分析 / N28_拐点分析
    • N41_贡献度分析 / N28_贡献度分析
    • N41_分组分析 / N28_分组分析
    • N41_覆盖系数统计 / N28_覆盖系数统计 ⭐新增
    • N41_覆盖系数分层分析 / N28_覆盖系数分层分析 ⭐新增
    """)
    
    # 预生成报告数据
    @st.cache_data
    def 生成报告数据():
        """生成报告数据并缓存"""
        import io
        输出 = io.BytesIO()
        with pd.ExcelWriter(输出, engine='openpyxl') as writer:
            # 1. N41原始数据
            if 'n41' in 分组数据:
                分组数据['n41'].to_excel(writer, sheet_name='N41原始数据', index=False)
            
            # 2. N28原始数据
            if 'n28' in 分组数据:
                分组数据['n28'].to_excel(writer, sheet_name='N28原始数据', index=False)
            
            # 3. 统计摘要
            统计摘要 = 分析器.获取统计摘要_按制式()
            统计df = pd.DataFrame(统计摘要).T
            统计df.to_excel(writer, sheet_name='统计摘要')
            
            # 4. CQI对速率影响分析
            速率影响 = 分析器.分析CQI对速率影响_按制式()
            if 'n41' in 速率影响:
                n41_rate_df = pd.DataFrame(速率影响['n41']).T
                n41_rate_df.to_excel(writer, sheet_name='N41_CQI对速率影响')
            if 'n28' in 速率影响:
                n28_rate_df = pd.DataFrame(速率影响['n28']).T
                n28_rate_df.to_excel(writer, sheet_name='N28_CQI对速率影响')
            
            # 5. 影响CQI的因素分析
            影响结果 = 分析器.分析影响CQI的指标_按制式()
            if 'n41' in 影响结果:
                n41_factor_df = pd.DataFrame(影响结果['n41'])
                n41_factor_df.to_excel(writer, sheet_name='N41_影响CQI的因素', index=False)
            if 'n28' in 影响结果:
                n28_factor_df = pd.DataFrame(影响结果['n28'])
                n28_factor_df.to_excel(writer, sheet_name='N28_影响CQI的因素', index=False)
            
            # 6. 相关性矩阵
            列名列表 = [
                'CQI优良率',
                '下行用户平均速率(MBPS)',
                '上行用户平均速率(MBPS)',
                '小区MR覆盖平均电平',
                '小区MR覆盖平均SINR',
                '小区MR覆盖平均TA',
                '小区上行平均干扰电平',
                '重叠覆盖采样点比例(%)',  # ⭐新增
                '覆盖系数'  # ⭐新增
            ]
            相关性矩阵 = 分析器.计算相关性矩阵_按制式(列名列表)
            if 'n41' in 相关性矩阵:
                相关性矩阵['n41'].to_excel(writer, sheet_name='N41_相关性矩阵')
            if 'n28' in 相关性矩阵:
                相关性矩阵['n28'].to_excel(writer, sheet_name='N28_相关性矩阵')
            
            # 7. 拐点分析
            拐点分析结果 = 分析器.CQI速率拐点分析_按制式(10)
            if 'n41' in 拐点分析结果:
                拐点分析结果['n41']['区间统计'].to_excel(writer, sheet_name='N41_拐点分析', index=False)
            if 'n28' in 拐点分析结果:
                拐点分析结果['n28']['区间统计'].to_excel(writer, sheet_name='N28_拐点分析', index=False)
            
            # 8. 贡献度分析
            贡献度结果 = 分析器.贡献度分析_按制式()
            if 'n41' in 贡献度结果:
                n41_contrib_df = pd.DataFrame(贡献度结果['n41']['贡献度列表'])
                n41_contrib_df.to_excel(writer, sheet_name='N41_贡献度分析', index=False)
            if 'n28' in 贡献度结果:
                n28_contrib_df = pd.DataFrame(贡献度结果['n28']['贡献度列表'])
                n28_contrib_df.to_excel(writer, sheet_name='N28_贡献度分析', index=False)
            
            # 9. 分组分析
            分组分析 = 分析器.按CQI分组分析_按制式(5)
            if 'n41' in 分组分析:
                分组分析['n41'].to_excel(writer, sheet_name='N41_分组分析')
            if 'n28' in 分组分析:
                分组分析['n28'].to_excel(writer, sheet_name='N28_分组分析')
            
            # 10. 覆盖系数统计 ⭐新增
            覆盖系数统计 = 分析器.覆盖系数统计_按制式()
            if 'n41' in 覆盖系数统计:
                n41_coef_stats = {k: v for k, v in 覆盖系数统计['n41'].items() if k != '覆盖系数数据'}
                pd.DataFrame([n41_coef_stats]).to_excel(writer, sheet_name='N41_覆盖系数统计', index=False)
            if 'n28' in 覆盖系数统计:
                n28_coef_stats = {k: v for k, v in 覆盖系数统计['n28'].items() if k != '覆盖系数数据'}
                pd.DataFrame([n28_coef_stats]).to_excel(writer, sheet_name='N28_覆盖系数统计', index=False)
            
            # 11. 覆盖系数与CQI相关性 ⭐新增
            相关性结果 = 分析器.覆盖系数与CQI相关性_按制式()
            if 'n41' in 相关性结果:
                pd.DataFrame(相关性结果['n41']).to_excel(writer, sheet_name='N41_覆盖系数相关性', index=False)
            if 'n28' in 相关性结果:
                pd.DataFrame(相关性结果['n28']).to_excel(writer, sheet_name='N28_覆盖系数相关性', index=False)
            
            # 12. 覆盖系数分层分析 ⭐新增
            分层结果 = 分析器.多维度分层分析_按制式(维度='覆盖系数')
            if 'n41' in 分层结果:
                分层结果['n41'].to_excel(writer, sheet_name='N41_覆盖系数分层', index=False)
            if 'n28' in 分层结果:
                分层结果['n28'].to_excel(writer, sheet_name='N28_覆盖系数分层', index=False)

        输出.seek(0)
        return 输出.getvalue()
    
    # 生成报告
    with st.spinner('正在准备报告...'):
        try:
            报告数据 = 生成报告数据()
            st.success("✅ 报告已准备好！")
            
            # 直接显示下载按钮
            st.download_button(
                label="📥 下载完整分析报告",
                data=报告数据,
                file_name="CQI_ZTE/CQI分析完整报告_N41vsN28.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        except Exception as e:
            st.error(f"❌ 报告生成失败: {str(e)}")

    # 分析总结
    st.markdown("---")
    st.markdown('<p class="sub-header">📝 数据导出总结</p>', unsafe_allow_html=True)

    分组数据 = 分析器.按网络制式分组()

    总结内容 = "<div class='highlight'><b>📊 数据导出说明</b><br><br>"

    总结内容 += "<b>1. 可导出数据类型：</b><br>"
    总结内容 += "• <b>N41原始数据</b>：包含N41网络制式所有小区的详细数据<br>"
    总结内容 += "• <b>N28原始数据</b>：包含N28网络制式所有小区的详细数据<br>"
    总结内容 += "• <b>统计摘要</b>：N41和N28的汇总统计信息<br>"

    if 'n41' in 分组数据 and 'n28' in 分组数据:
        n41_count = len(分组数据['n41'])
        n28_count = len(分组数据['n28'])
        total_count = n41_count + n28_count

        总结内容 += "<br><b>2. 数据量统计：</b><br>"
        总结内容 += f"• N41数据量: {n41_count:,} 条 ({n41_count/total_count*100:.1f}%)<br>"
        总结内容 += f"• N28数据量: {n28_count:,} 条 ({n28_count/total_count*100:.1f}%)<br>"
        总结内容 += f"• 总数据量: {total_count:,} 条<br>"

    总结内容 += "<br><b>3. 导出文件说明：</b><br>"
    总结内容 += "• <b>N41_CQI分析数据.xlsx</b>：仅包含N41网络制式的分析数据<br>"
    总结内容 += "• <b>N28_CQI分析数据.xlsx</b>：仅包含N28网络制式的分析数据<br>"
    总结内容 += "• <b>CQI分析完整报告_N41vsN28.xlsx</b>：包含两个制式的完整分析报告<br>"

    总结内容 += "<br><b>4. 使用建议：</b><br>"
    总结内容 += "• 如需单独分析某一制式，请下载对应的单独数据文件<br>"
    总结内容 += "• 如需整体对比分析，请下载完整报告<br>"
    总结内容 += "• 导出的Excel文件可直接用于后续的定制化分析或报告制作"

    总结内容 += "</div>"
    st.markdown(总结内容, unsafe_allow_html=True)


def main():
    """主函数"""
    st.markdown('<p class="main-header">📡 5G CQI关联性能分析系统<br><small>网络制式对比版 (N41 vs N28)</small></p>', unsafe_allow_html=True)

    st.markdown("---")

    # 使用新的数据源文件（支持本地和云端部署）
    import os
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    文件路径 = os.path.join(current_dir, "CQI关联指标_中兴.xlsx")

    # 创建分析器
    分析器 = CQI分析器(文件路径)

    with st.spinner('正在加载数据...'):
        if 分析器.读取数据() and 分析器.清洗数据():
            数据量 = len(分析器.清洗后数据)
            分组数据 = 分析器.按网络制式分组()
            if len(分组数据) > 1:
                制式信息 = " | ".join([f"{k}: {len(v):,}条" for k, v in 分组数据.items()])
                st.success(f"✅ 数据加载成功！共 {数据量:,} 条有效记录 ({制式信息})")
            else:
                st.success(f"✅ 数据加载成功！共 {数据量:,} 条有效记录")
        else:
            st.error("❌ 数据加载失败")
            return

    st.markdown("---")

    # ⭐ 重组后的标签页结构（6个主标签页）
    选项卡 = st.tabs([
        "🏠 概览",
        "🔗 相关性分析",      # 合并：CQI对速率影响 + 影响CQI的因素 + 相关性矩阵
        "🎯 深度关联分析",    # 合并：阈值分析 + 贡献度分析 + 分组分析
        "🔄 多维度诊断",      # 原多维度交叉分析（移除TA分层和条件分组）
        "📏 距离覆盖分析",    # ⭐ 合并：覆盖系数 + TA分层 + 条件分组
        "📥 数据导出"
    ])

    with 选项卡[0]:
        st.markdown('<p class="sub-header">📊 数据概览 - N41 vs N28 对比</p>', unsafe_allow_html=True)
        渲染制式对比概览(分析器)

    with 选项卡[1]:
        # 🔗 相关性分析 - 使用子标签组织2个原页面
        st.markdown('<p class="sub-header">🔗 相关性分析 - N41 vs N28 对比</p>', unsafe_allow_html=True)
        相关性子标签 = st.tabs([
            "📊 CQI对速率影响",
            "📈 相关性可视化"
        ])
        with 相关性子标签[0]:
            渲染制式对比速率影响(分析器)
        with 相关性子标签[1]:
            渲染制式对比相关性矩阵(分析器)

    with 选项卡[2]:
        # 🎯 深度关联分析 - 使用子标签组织3个原页面
        st.markdown('<p class="sub-header">🎯 深度关联分析 - N41 vs N28 对比</p>', unsafe_allow_html=True)
        深度子标签 = st.tabs([
            "📈 拐点分析",
            "📊 贡献度分析",
            "📈 分组分析"
        ])
        with 深度子标签[0]:
            渲染制式对比拐点分析(分析器)
        with 深度子标签[1]:
            渲染制式对比贡献度分析(分析器)
        with 深度子标签[2]:
            渲染制式对比分组分析(分析器)

    with 选项卡[3]:
        st.markdown('<p class="sub-header">🔄 多维度诊断 - N41 vs N28 对比</p>', unsafe_allow_html=True)
        渲染制式对比多维度交叉分析(分析器)

    with 选项卡[4]:  # 📏 距离覆盖分析
        st.markdown('<p class="sub-header">📏 距离覆盖分析 - N41 vs N28 对比</p>', unsafe_allow_html=True)
        渲染制式对比距离覆盖分析(分析器)

    with 选项卡[5]:  # 📥 数据导出
        st.markdown('<p class="sub-header">📥 数据导出 - N41 vs N28</p>', unsafe_allow_html=True)
        渲染制式对比数据导出(分析器)

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
    <b>5G CQI关联性能分析系统 - 网络制式对比版</b> | Powered by Streamlit & Plotly<br>
    支持N41和N28网络制式左右对比分析
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
