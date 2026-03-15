#!/usr/bin/env python3
"""
期刊对比分析与可视化

生成:
1. 雷达图 - JEL大类分布对比
2. 堆叠面积图 - 主题随时间演变
3. 折线图 - 两期刊趋势对比
4. 差异热力图 - 期刊差异分析
"""

import os
import json
import re
from collections import Counter, defaultdict
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.colors as mcolors

# 设置字体
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# JEL 一级分类
JEL_CATEGORIES = {
    'A': 'General',
    'B': 'History of Thought',
    'C': 'Quant Methods',
    'D': 'Microeconomics',
    'E': 'Macro/Monetary',
    'F': 'International',
    'G': 'Finance',
    'H': 'Public Econ',
    'I': 'Health/Education',
    'J': 'Labor',
    'K': 'Law & Econ',
    'L': 'Industrial Org',
    'M': 'Business',
    'N': 'Economic History',
    'O': 'Development/Tech',
    'P': 'Economic Systems',
    'Q': 'Agri/Environment',
    'R': 'Urban/Regional',
    'Z': 'Other',
}

# 方法标准化
def normalize_method(method):
    if not method:
        return None
    m = method.strip().lower()
    m = re.sub(r'\s+', ' ', m)
    m = re.sub(r'\s*\([^)]*\)\s*', ' ', m).strip()
    
    rules = {
        r'.*difference.?in.?difference.*': 'DID',
        r'.*双重差分.*': 'DID',
        r'.*did.*': 'DID',
        r'.*instrumental variable.*': 'IV',
        r'.*工具变量.*': 'IV',
        r'.*panel.*': 'Panel',
        r'.*面板.*': 'Panel',
        r'.*fixed effect.*': 'Fixed Effects',
        r'.*固定效应.*': 'Fixed Effects',
        r'.*regression discontinuity.*': 'RDD',
        r'.*断点回归.*': 'RDD',
        r'.*propensity score.*': 'PSM',
        r'.*general equilibrium.*': 'GE Model',
        r'.*一般均衡.*': 'GE Model',
        r'.*game theor.*': 'Game Theory',
        r'.*博弈.*': 'Game Theory',
        r'.*experiment.*': 'Experiment',
        r'.*machine learning.*': 'ML',
        r'.*机器学习.*': 'ML',
        r'.*text analysis.*': 'Text/NLP',
        r'.*文本分析.*': 'Text/NLP',
        r'.*nlp.*': 'Text/NLP',
        r'.*structural.*': 'Structural',
        r'.*event study.*': 'Event Study',
        r'.*事件研究.*': 'Event Study',
        r'.*quasi.?experiment.*': 'Quasi-Experiment',
        r'.*准自然实验.*': 'Quasi-Experiment',
        r'.*自然实验.*': 'Natural Experiment',
        r'.*input.?output.*': 'IO Analysis',
        r'.*投入产出.*': 'IO Analysis',
        r'.*spatial.*': 'Spatial',
        r'.*空间.*': 'Spatial',
    }
    
    for pattern, replacement in rules.items():
        if re.match(pattern, m):
            return replacement
    return None  # 只保留标准化的方法


# 中文行业→英文映射
INDUSTRY_CN_TO_EN = {
    '制造业': 'Manufacturing',
    '金融': 'Finance',
    '金融业': 'Finance',
    '银行': 'Banking',
    '银行业': 'Banking',
    '房地产': 'Real Estate',
    '互联网': 'Internet',
    '电子商务': 'E-commerce',
    '数字经济': 'Digital Economy',
    '农业': 'Agriculture',
    '农村': 'Rural',
    '教育': 'Education',
    '高等教育': 'Higher Education',
    '医疗': 'Healthcare',
    '健康': 'Health',
    '交通': 'Transportation',
    '交通运输': 'Transportation',
    '物流': 'Logistics',
    '能源': 'Energy',
    '电力': 'Electricity',
    '新能源': 'New Energy',
    '环境': 'Environment',
    '环保': 'Environmental',
    '碳排放': 'Carbon Emission',
    '绿色': 'Green',
    '科技': 'Technology',
    '高新技术': 'High-tech',
    '人工智能': 'AI',
    '信息技术': 'IT',
    '通信': 'Telecom',
    '贸易': 'Trade',
    '国际贸易': 'Intl Trade',
    '进出口': 'Import/Export',
    '跨境': 'Cross-border',
    '供应链': 'Supply Chain',
    '产业链': 'Industry Chain',
    '资本市场': 'Capital Market',
    '债券': 'Bond',
    '证券': 'Securities',
    '股票': 'Stock',
    '保险': 'Insurance',
    '税收': 'Tax',
    '财政': 'Fiscal',
    '公共': 'Public',
    '政府': 'Government',
    '国有企业': 'SOE',
    '民营企业': 'Private Firm',
    '中小企业': 'SME',
    '创业': 'Entrepreneurship',
    '创新': 'Innovation',
    '研发': 'R&D',
    '专利': 'Patent',
    '劳动': 'Labor',
    '就业': 'Employment',
    '人口': 'Population',
    '城市': 'Urban',
    '区域': 'Regional',
    '住房': 'Housing',
    '消费': 'Consumption',
    '零售': 'Retail',
    '服务业': 'Services',
    '平台': 'Platform',
    '数据': 'Data',
    '宏观经济': 'Macroeconomics',
    '货币': 'Monetary',
}


def translate_industry(ind):
    """将中文行业名翻译为英文"""
    if not ind:
        return None
    
    ind = ind.strip()
    
    # 如果已经是英文，直接返回
    if ind.isascii():
        return ind[:20]
    
    # 尝试直接匹配
    if ind in INDUSTRY_CN_TO_EN:
        return INDUSTRY_CN_TO_EN[ind]
    
    # 尝试部分匹配
    for cn, en in INDUSTRY_CN_TO_EN.items():
        if cn in ind:
            return en
    
    # 无法翻译，跳过
    return None


def extract_jel_l1(code):
    if not code or not isinstance(code, str):
        return None
    code = code.strip().upper()
    if re.match(r'^[A-Z]\d{0,2}$', code):
        return code[0]
    return None


def load_journal_data(base_dir, cutoff='2026-02'):
    """加载期刊数据，按双月组织"""
    data = {}
    
    for folder in sorted(os.listdir(base_dir)):
        if folder > cutoff and 'inpress' not in folder.lower():
            continue
        if 'inpress' in folder.lower():
            continue
            
        folder_path = os.path.join(base_dir, folder)
        analysis_dir = os.path.join(folder_path, 'analysis')
        
        if not os.path.isdir(analysis_dir):
            continue
        
        papers = []
        for f in os.listdir(analysis_dir):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(analysis_dir, f), 'r', encoding='utf-8') as fp:
                        papers.append(json.load(fp))
                except:
                    pass
        
        if papers:
            data[folder] = papers
    
    return data


def compute_stats(journal_data):
    """计算各维度统计"""
    jel_l1 = Counter()
    jel_l2 = Counter()
    methods = Counter()
    industries = Counter()
    
    # 按时期统计
    by_period = defaultdict(lambda: {'jel_l1': Counter(), 'methods': Counter(), 'industries': Counter(), 'total': 0})
    
    for period, papers in journal_data.items():
        by_period[period]['total'] = len(papers)
        
        for p in papers:
            # JEL
            for jel in p.get('jel_codes', []):
                code = jel.get('code', '') if isinstance(jel, dict) else str(jel)
                l1 = extract_jel_l1(code)
                if l1:
                    jel_l1[l1] += 1
                    by_period[period]['jel_l1'][l1] += 1
                if code and len(code) >= 2:
                    jel_l2[code[:2]] += 1
            
            # Methods
            for m in p.get('methods', []):
                normalized = normalize_method(m)
                if normalized:
                    methods[normalized] += 1
                    by_period[period]['methods'][normalized] += 1
            
            # Industries - 翻译成英文
            for ind in p.get('industries', []):
                translated = translate_industry(ind)
                if translated:
                    industries[translated] += 1
                    by_period[period]['industries'][translated] += 1
    
    total_papers = sum(len(papers) for papers in journal_data.values())
    
    return {
        'jel_l1': jel_l1,
        'jel_l2': jel_l2,
        'methods': methods,
        'industries': industries,
        'by_period': dict(by_period),
        'total': total_papers
    }


def plot_radar_comparison(stats1, stats2, name1, name2, output_path):
    """雷达图对比 JEL 大类分布"""
    # 选择有数据的类别
    all_cats = sorted(set(stats1['jel_l1'].keys()) | set(stats2['jel_l1'].keys()))
    
    if len(all_cats) < 3:
        print("Not enough categories for radar chart")
        return
    
    # 计算比例
    total1 = sum(stats1['jel_l1'].values()) or 1
    total2 = sum(stats2['jel_l1'].values()) or 1
    
    values1 = [stats1['jel_l1'].get(c, 0) / total1 * 100 for c in all_cats]
    values2 = [stats2['jel_l1'].get(c, 0) / total2 * 100 for c in all_cats]
    
    # 创建雷达图
    angles = np.linspace(0, 2 * np.pi, len(all_cats), endpoint=False).tolist()
    values1 += values1[:1]
    values2 += values2[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    
    ax.plot(angles, values1, 'o-', linewidth=2, label=name1, color='#2E86AB')
    ax.fill(angles, values1, alpha=0.25, color='#2E86AB')
    
    ax.plot(angles, values2, 'o-', linewidth=2, label=name2, color='#E94F37')
    ax.fill(angles, values2, alpha=0.25, color='#E94F37')
    
    # 标签
    labels = [f"{c}\n({JEL_CATEGORIES.get(c, '')})" for c in all_cats]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=9)
    
    ax.set_title('JEL Category Distribution Comparison\n(% of total)', size=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def plot_method_comparison(stats1, stats2, name1, name2, output_path):
    """双条形图对比研究方法"""
    # 找出两边都有的方法
    all_methods = set(stats1['methods'].keys()) | set(stats2['methods'].keys())
    
    # 按总频次排序，取 top 15
    combined = Counter()
    for m in all_methods:
        combined[m] = stats1['methods'].get(m, 0) + stats2['methods'].get(m, 0)
    
    top_methods = [m for m, _ in combined.most_common(15)]
    
    # 计算比例
    total1 = sum(stats1['methods'].values()) or 1
    total2 = sum(stats2['methods'].values()) or 1
    
    vals1 = [stats1['methods'].get(m, 0) / total1 * 100 for m in top_methods]
    vals2 = [stats2['methods'].get(m, 0) / total2 * 100 for m in top_methods]
    
    # 绘图
    fig, ax = plt.subplots(figsize=(12, 8))
    
    y = np.arange(len(top_methods))
    height = 0.35
    
    bars1 = ax.barh(y - height/2, vals1, height, label=name1, color='#2E86AB')
    bars2 = ax.barh(y + height/2, vals2, height, label=name2, color='#E94F37')
    
    ax.set_yticks(y)
    ax.set_yticklabels(top_methods)
    ax.invert_yaxis()
    ax.set_xlabel('Percentage (%)')
    ax.set_title('Research Methods Comparison', fontweight='bold', size=14)
    ax.legend()
    
    # 添加数值标签
    for bar, val in zip(bars1, vals1):
        if val > 0:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                   f'{val:.1f}%', va='center', fontsize=8, color='#2E86AB')
    for bar, val in zip(bars2, vals2):
        if val > 0:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                   f'{val:.1f}%', va='center', fontsize=8, color='#E94F37')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def plot_industry_comparison(stats1, stats2, name1, name2, output_path):
    """双条形图对比行业分布"""
    # 找出两边都有的行业
    all_industries = set(stats1['industries'].keys()) | set(stats2['industries'].keys())
    
    # 按总频次排序，取 top 15
    combined = Counter()
    for ind in all_industries:
        combined[ind] = stats1['industries'].get(ind, 0) + stats2['industries'].get(ind, 0)
    
    top_industries = [ind for ind, _ in combined.most_common(15)]
    
    if not top_industries:
        print("  Skipped industry comparison (no data)")
        return
    
    # 计算比例
    total1 = sum(stats1['industries'].values()) or 1
    total2 = sum(stats2['industries'].values()) or 1
    
    vals1 = [stats1['industries'].get(ind, 0) / total1 * 100 for ind in top_industries]
    vals2 = [stats2['industries'].get(ind, 0) / total2 * 100 for ind in top_industries]
    
    # 绘图
    fig, ax = plt.subplots(figsize=(12, 8))
    
    y = np.arange(len(top_industries))
    height = 0.35
    
    bars1 = ax.barh(y - height/2, vals1, height, label=name1, color='#2E86AB')
    bars2 = ax.barh(y + height/2, vals2, height, label=name2, color='#E94F37')
    
    ax.set_yticks(y)
    ax.set_yticklabels(top_industries)
    ax.invert_yaxis()
    ax.set_xlabel('Percentage (%)')
    ax.set_title('Industry Focus Comparison', fontweight='bold', size=14)
    ax.legend()
    
    # 添加数值标签
    for bar, val in zip(bars1, vals1):
        if val > 0:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, 
                   f'{val:.1f}%', va='center', fontsize=8, color='#2E86AB')
    for bar, val in zip(bars2, vals2):
        if val > 0:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, 
                   f'{val:.1f}%', va='center', fontsize=8, color='#E94F37')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def plot_industry_trend(stats1, stats2, name1, name2, output_path):
    """行业趋势折线图"""
    periods = sorted(set(stats1['by_period'].keys()) & set(stats2['by_period'].keys()))
    
    if len(periods) < 2:
        print("  Skipped industry trend (not enough periods)")
        return
    
    # 选择最重要的 6 个行业
    combined_ind = Counter()
    for p in periods:
        combined_ind.update(stats1['by_period'][p].get('industries', {}))
        combined_ind.update(stats2['by_period'][p].get('industries', {}))
    
    top_industries = [ind for ind, _ in combined_ind.most_common(6)]
    
    if len(top_industries) < 3:
        print("  Skipped industry trend (not enough industries)")
        return
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    for idx, ind in enumerate(top_industries):
        ax = axes[idx // 3, idx % 3]
        
        vals1 = []
        vals2 = []
        for p in periods:
            t1 = sum(stats1['by_period'][p].get('industries', {}).values()) or 1
            t2 = sum(stats2['by_period'][p].get('industries', {}).values()) or 1
            vals1.append(stats1['by_period'][p].get('industries', {}).get(ind, 0) / t1 * 100)
            vals2.append(stats2['by_period'][p].get('industries', {}).get(ind, 0) / t2 * 100)
        
        ax.plot(periods, vals1, 'o-', label=name1, color='#2E86AB', linewidth=2, markersize=6)
        ax.plot(periods, vals2, 's-', label=name2, color='#E94F37', linewidth=2, markersize=6)
        
        ax.set_title(ind, fontweight='bold')
        ax.set_ylabel('% of papers')
        ax.tick_params(axis='x', rotation=45)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('Industry Focus Trends Over Time', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def plot_time_trend(stats1, stats2, name1, name2, output_dir):
    """时间趋势折线图"""
    periods = sorted(set(stats1['by_period'].keys()) & set(stats2['by_period'].keys()))
    
    if len(periods) < 2:
        print("Not enough periods for trend analysis")
        return
    
    # 1. JEL 大类随时间变化
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # 选择最重要的 6 个 JEL 大类
    combined_jel = Counter()
    for p in periods:
        combined_jel.update(stats1['by_period'][p]['jel_l1'])
        combined_jel.update(stats2['by_period'][p]['jel_l1'])
    
    top_jel = [c for c, _ in combined_jel.most_common(6)]
    
    for idx, jel in enumerate(top_jel):
        ax = axes[idx // 3, idx % 3]
        
        # 计算每期的比例
        vals1 = []
        vals2 = []
        for p in periods:
            t1 = sum(stats1['by_period'][p]['jel_l1'].values()) or 1
            t2 = sum(stats2['by_period'][p]['jel_l1'].values()) or 1
            vals1.append(stats1['by_period'][p]['jel_l1'].get(jel, 0) / t1 * 100)
            vals2.append(stats2['by_period'][p]['jel_l1'].get(jel, 0) / t2 * 100)
        
        ax.plot(periods, vals1, 'o-', label=name1, color='#2E86AB', linewidth=2, markersize=6)
        ax.plot(periods, vals2, 's-', label=name2, color='#E94F37', linewidth=2, markersize=6)
        
        ax.set_title(f'{jel} - {JEL_CATEGORIES.get(jel, "")}', fontweight='bold')
        ax.set_ylabel('% of papers')
        ax.tick_params(axis='x', rotation=45)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('JEL Category Trends Over Time', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'trend_jel.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {os.path.join(output_dir, 'trend_jel.png')}")
    
    # 2. 方法随时间变化
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    combined_methods = Counter()
    for p in periods:
        combined_methods.update(stats1['by_period'][p]['methods'])
        combined_methods.update(stats2['by_period'][p]['methods'])
    
    top_methods = [m for m, _ in combined_methods.most_common(6)]
    
    for idx, method in enumerate(top_methods):
        ax = axes[idx // 3, idx % 3]
        
        vals1 = []
        vals2 = []
        for p in periods:
            t1 = sum(stats1['by_period'][p]['methods'].values()) or 1
            t2 = sum(stats2['by_period'][p]['methods'].values()) or 1
            vals1.append(stats1['by_period'][p]['methods'].get(method, 0) / t1 * 100)
            vals2.append(stats2['by_period'][p]['methods'].get(method, 0) / t2 * 100)
        
        ax.plot(periods, vals1, 'o-', label=name1, color='#2E86AB', linewidth=2, markersize=6)
        ax.plot(periods, vals2, 's-', label=name2, color='#E94F37', linewidth=2, markersize=6)
        
        ax.set_title(method, fontweight='bold')
        ax.set_ylabel('% of papers')
        ax.tick_params(axis='x', rotation=45)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('Research Methods Trends Over Time', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'trend_methods.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {os.path.join(output_dir, 'trend_methods.png')}")


def plot_stacked_area(stats, name, output_path, stat_type='jel_l1'):
    """堆叠面积图显示主题演变"""
    periods = sorted(stats['by_period'].keys())
    
    if len(periods) < 2:
        return
    
    # 找出 top 类别
    combined = Counter()
    for p in periods:
        combined.update(stats['by_period'][p][stat_type])
    
    top_cats = [c for c, _ in combined.most_common(8)]
    
    # 构建数据矩阵 (比例)
    data = []
    for cat in top_cats:
        row = []
        for p in periods:
            total = sum(stats['by_period'][p][stat_type].values()) or 1
            row.append(stats['by_period'][p][stat_type].get(cat, 0) / total * 100)
        data.append(row)
    
    # 绘图
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(top_cats)))
    
    ax.stackplot(periods, data, labels=top_cats, colors=colors, alpha=0.8)
    
    ax.set_xlabel('Period')
    ax.set_ylabel('Percentage (%)')
    
    type_name = 'JEL Categories' if stat_type == 'jel_l1' else 'Methods'
    ax.set_title(f'{name}: {type_name} Evolution Over Time', fontweight='bold', size=14)
    
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=9)
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def plot_difference_heatmap(stats1, stats2, name1, name2, output_path):
    """差异热力图 - 显示两期刊在各 JEL 二级分类上的差异"""
    # 获取所有 JEL L2 代码
    all_codes = sorted(set(stats1['jel_l2'].keys()) | set(stats2['jel_l2'].keys()))
    
    if len(all_codes) < 5:
        return
    
    # 计算比例差异 (journal2 - journal1)
    total1 = sum(stats1['jel_l2'].values()) or 1
    total2 = sum(stats2['jel_l2'].values()) or 1
    
    diffs = {}
    for code in all_codes:
        pct1 = stats1['jel_l2'].get(code, 0) / total1 * 100
        pct2 = stats2['jel_l2'].get(code, 0) / total2 * 100
        diffs[code] = pct2 - pct1
    
    # 按差异排序，取极端值
    sorted_codes = sorted(diffs.items(), key=lambda x: x[1])
    
    # 取两端各 10 个
    n = min(10, len(sorted_codes) // 2)
    selected = sorted_codes[:n] + sorted_codes[-n:]
    
    codes = [c for c, _ in selected]
    values = [v for _, v in selected]
    
    # 绘图
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 颜色：负值（偏向 journal1）用蓝色，正值（偏向 journal2）用红色
    colors = ['#2E86AB' if v < 0 else '#E94F37' for v in values]
    
    y = np.arange(len(codes))
    bars = ax.barh(y, values, color=colors)
    
    ax.set_yticks(y)
    ax.set_yticklabels(codes)
    ax.axvline(x=0, color='black', linewidth=0.5)
    
    ax.set_xlabel('Difference in Percentage Points')
    ax.set_title(f'JEL Focus Difference: {name2} vs {name1}\n(positive = more in {name2})', 
                fontweight='bold', size=12)
    
    # 添加图例
    legend_elements = [
        Patch(facecolor='#2E86AB', label=f'More in {name1}'),
        Patch(facecolor='#E94F37', label=f'More in {name2}')
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def main():
    workspace = '/home/ubuntu/.openclaw/workspace'
    output_dir = os.path.join(workspace, 'comparison')
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("  Journal Comparison Analysis")
    print("=" * 60)
    
    # 加载数据
    print("\n📚 Loading data...")
    cer_data = load_journal_data(os.path.join(workspace, 'CER05-06'))
    jjyj_data = load_journal_data(os.path.join(workspace, '经济研究05-06'))
    
    # 计算统计
    print("📊 Computing statistics...")
    cer_stats = compute_stats(cer_data)
    jjyj_stats = compute_stats(jjyj_data)
    
    print(f"   CER: {cer_stats['total']} papers")
    print(f"   JJYJ: {jjyj_stats['total']} papers")
    
    # 生成图表
    print("\n🎨 Generating charts...")
    
    # 1. 雷达图 - JEL 大类对比
    plot_radar_comparison(cer_stats, jjyj_stats, 'CER', 'JJYJ', 
                         os.path.join(output_dir, 'radar_jel.png'))
    
    # 2. 方法对比条形图
    plot_method_comparison(cer_stats, jjyj_stats, 'CER', 'JJYJ',
                          os.path.join(output_dir, 'methods_comparison.png'))
    
    # 3. 行业对比条形图
    plot_industry_comparison(cer_stats, jjyj_stats, 'CER', 'JJYJ',
                            os.path.join(output_dir, 'industry_comparison.png'))
    
    # 4. 时间趋势图
    plot_time_trend(cer_stats, jjyj_stats, 'CER', 'JJYJ', output_dir)
    
    # 5. 行业趋势图
    plot_industry_trend(cer_stats, jjyj_stats, 'CER', 'JJYJ',
                       os.path.join(output_dir, 'trend_industries.png'))
    
    # 6. 堆叠面积图 - JEL 演变
    plot_stacked_area(cer_stats, 'CER', 
                     os.path.join(output_dir, 'stacked_jel_cer.png'), 'jel_l1')
    plot_stacked_area(jjyj_stats, 'JJYJ', 
                     os.path.join(output_dir, 'stacked_jel_jjyj.png'), 'jel_l1')
    
    # 7. 堆叠面积图 - 方法演变
    plot_stacked_area(cer_stats, 'CER', 
                     os.path.join(output_dir, 'stacked_methods_cer.png'), 'methods')
    plot_stacked_area(jjyj_stats, 'JJYJ', 
                     os.path.join(output_dir, 'stacked_methods_jjyj.png'), 'methods')
    
    # 8. 差异热力图
    plot_difference_heatmap(cer_stats, jjyj_stats, 'CER', 'JJYJ',
                           os.path.join(output_dir, 'difference_jel.png'))
    
    print(f"\n✅ All charts saved to: {output_dir}/")
    print("\nGenerated files:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.png'):
            print(f"   - {f}")


if __name__ == '__main__':
    main()
