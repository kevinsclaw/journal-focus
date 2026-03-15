#!/usr/bin/env python3
"""
标签共现网络图生成器

基于论文分析 JSON，生成标签之间的网状关联图。
同一篇论文中同时出现的标签之间建立链接。

Usage:
    python tag_network.py CER05-06/
    python tag_network.py 经济研究05-06/
"""

import os
import json
import re
import argparse
from collections import Counter, defaultdict
from itertools import combinations

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# 尝试导入 networkx
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("Warning: networkx not installed. Run: pip install networkx")

# 设置字体
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# JEL 一级分类颜色
JEL_COLORS = {
    'A': '#FF6B6B', 'B': '#4ECDC4', 'C': '#45B7D1', 'D': '#96CEB4',
    'E': '#FFEAA7', 'F': '#DDA0DD', 'G': '#98D8C8', 'H': '#F7DC6F',
    'I': '#BB8FCE', 'J': '#85C1E9', 'K': '#F8B500', 'L': '#FF8C00',
    'M': '#00CED1', 'N': '#9370DB', 'O': '#3CB371', 'P': '#FF69B4',
    'Q': '#20B2AA', 'R': '#87CEEB', 'Z': '#D3D3D3'
}

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
        r'.*fixed effect.*': 'FE',
        r'.*固定效应.*': 'FE',
        r'.*regression discontinuity.*': 'RDD',
        r'.*断点回归.*': 'RDD',
        r'.*propensity score.*': 'PSM',
        r'.*general equilibrium.*': 'GE',
        r'.*一般均衡.*': 'GE',
        r'.*game theor.*': 'Game',
        r'.*博弈.*': 'Game',
        r'.*experiment.*': 'Exp',
        r'.*machine learning.*': 'ML',
        r'.*机器学习.*': 'ML',
        r'.*text analysis.*': 'NLP',
        r'.*文本分析.*': 'NLP',
        r'.*nlp.*': 'NLP',
        r'.*structural.*': 'Struct',
        r'.*event study.*': 'Event',
        r'.*事件研究.*': 'Event',
        r'.*quasi.?experiment.*': 'Quasi-Exp',
        r'.*准自然实验.*': 'Quasi-Exp',
        r'.*input.?output.*': 'IO',
        r'.*投入产出.*': 'IO',
        r'.*spatial.*': 'Spatial',
        r'.*空间.*': 'Spatial',
    }
    
    for pattern, replacement in rules.items():
        if re.match(pattern, m):
            return replacement
    return None


def extract_jel_l1(code):
    if not code or not isinstance(code, str):
        return None
    code = code.strip().upper()
    if re.match(r'^[A-Z]\d{0,2}$', code):
        return code[0]
    return None


def translate_industry(ind):
    """将中文行业名翻译为英文"""
    if not ind:
        return None
    
    # 如果已经是英文，直接返回
    if ind.isascii():
        return ind[:18]
    
    # 尝试直接匹配
    if ind in INDUSTRY_CN_TO_EN:
        return INDUSTRY_CN_TO_EN[ind]
    
    # 尝试部分匹配
    for cn, en in INDUSTRY_CN_TO_EN.items():
        if cn in ind:
            return en
    
    # 无法翻译，返回简化版
    return ind[:8] if len(ind) > 8 else ind


def extract_jel_l2(code):
    if not code or not isinstance(code, str):
        return None
    code = code.strip().upper()
    match = re.match(r'^([A-Z]\d)', code)
    if match:
        return match.group(1)
    return None


def load_json_files(analysis_dir):
    """加载分析目录下的所有JSON"""
    papers = []
    if not os.path.isdir(analysis_dir):
        return papers
    
    for f in os.listdir(analysis_dir):
        if f.endswith('.json'):
            try:
                with open(os.path.join(analysis_dir, f), 'r', encoding='utf-8') as fp:
                    papers.append(json.load(fp))
            except:
                pass
    return papers


def build_cooccurrence_network(papers, tag_type='jel_l1'):
    """
    构建共现网络
    tag_type: 'jel_l1', 'jel_l2', 'method', 'industry', 'jel_method'
    """
    # 边的权重（共现次数）
    edge_weights = Counter()
    # 节点出现次数
    node_counts = Counter()
    
    for paper in papers:
        tags = set()
        
        if tag_type == 'jel_l1':
            for jel in paper.get('jel_codes', []):
                code = jel.get('code', '') if isinstance(jel, dict) else str(jel)
                l1 = extract_jel_l1(code)
                if l1:
                    tags.add(('jel', l1))
        
        elif tag_type == 'jel_l2':
            for jel in paper.get('jel_codes', []):
                code = jel.get('code', '') if isinstance(jel, dict) else str(jel)
                l2 = extract_jel_l2(code)
                if l2:
                    tags.add(('jel', l2))
        
        elif tag_type == 'method':
            for m in paper.get('methods', []):
                normalized = normalize_method(m)
                if normalized:
                    tags.add(('method', normalized))
        
        elif tag_type == 'industry':
            for ind in paper.get('industries', []):
                if ind and len(ind) < 30:
                    ind_en = translate_industry(ind)
                    if ind_en:
                        tags.add(('industry', ind_en[:20]))
        
        elif tag_type == 'jel_method':
            # 跨类型：JEL L1 和 Method
            for jel in paper.get('jel_codes', []):
                code = jel.get('code', '') if isinstance(jel, dict) else str(jel)
                l1 = extract_jel_l1(code)
                if l1:
                    tags.add(('jel', l1))
            for m in paper.get('methods', []):
                normalized = normalize_method(m)
                if normalized:
                    tags.add(('method', normalized))
        
        elif tag_type == 'jel_industry':
            # 跨类型：JEL L1 和 Industry
            for jel in paper.get('jel_codes', []):
                code = jel.get('code', '') if isinstance(jel, dict) else str(jel)
                l1 = extract_jel_l1(code)
                if l1:
                    tags.add(('jel', l1))
            for ind in paper.get('industries', []):
                if ind and len(ind) < 25:
                    ind_en = translate_industry(ind)
                    if ind_en:
                        tags.add(('industry', ind_en))
        
        # 统计节点
        for tag in tags:
            node_counts[tag] += 1
        
        # 统计边（所有两两组合）
        for t1, t2 in combinations(sorted(tags), 2):
            edge_weights[(t1, t2)] += 1
    
    return node_counts, edge_weights


def draw_network(node_counts, edge_weights, title, output_path, 
                 min_node_count=2, min_edge_weight=1, max_nodes=50):
    """绘制网络图"""
    if not HAS_NETWORKX:
        print("  Skipped (networkx not installed)")
        return
    
    # 过滤节点
    filtered_nodes = {n: c for n, c in node_counts.items() if c >= min_node_count}
    
    # 按频次排序，取 top N
    top_nodes = dict(sorted(filtered_nodes.items(), key=lambda x: -x[1])[:max_nodes])
    
    if len(top_nodes) < 3:
        print(f"  Skipped (only {len(top_nodes)} nodes)")
        return
    
    # 创建图
    G = nx.Graph()
    
    # 添加节点
    for node, count in top_nodes.items():
        G.add_node(node, count=count)
    
    # 添加边
    for (n1, n2), weight in edge_weights.items():
        if n1 in top_nodes and n2 in top_nodes and weight >= min_edge_weight:
            G.add_edge(n1, n2, weight=weight)
    
    if G.number_of_edges() == 0:
        print(f"  Skipped (no edges)")
        return
    
    # 绘图
    fig, ax = plt.subplots(figsize=(14, 14))
    
    # 布局
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # 节点大小（基于频次）
    node_sizes = [top_nodes[n] * 100 + 200 for n in G.nodes()]
    
    # 节点颜色
    node_colors = []
    for node in G.nodes():
        tag_type, tag_value = node
        if tag_type == 'jel':
            node_colors.append(JEL_COLORS.get(tag_value[0], '#D3D3D3'))
        elif tag_type == 'method':
            node_colors.append('#45B7D1')
        else:
            node_colors.append('#96CEB4')
    
    # 边宽度（基于权重）
    edge_weights_list = [G[u][v]['weight'] for u, v in G.edges()]
    max_weight = max(edge_weights_list) if edge_weights_list else 1
    edge_widths = [w / max_weight * 5 + 0.5 for w in edge_weights_list]
    
    # 绘制边
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.4, 
                          edge_color='gray', ax=ax)
    
    # 绘制节点
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                          node_color=node_colors, alpha=0.8, ax=ax)
    
    # 标签
    labels = {n: n[1] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=9, ax=ax)
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  Generated: {output_path} ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")


def process_period(papers, period, output_dir, journal_name):
    """处理单个双月的数据"""
    print(f"\n📁 {period} ({len(papers)} papers)")
    
    charts_dir = os.path.join(output_dir, 'networks')
    os.makedirs(charts_dir, exist_ok=True)
    
    # 1. JEL L1 网络
    node_counts, edge_weights = build_cooccurrence_network(papers, 'jel_l1')
    draw_network(node_counts, edge_weights, 
                f'{journal_name} {period}: JEL Category Network',
                os.path.join(charts_dir, f'{period}_jel_l1.png'),
                min_node_count=1, min_edge_weight=1, max_nodes=19)
    
    # 2. JEL L2 网络
    node_counts, edge_weights = build_cooccurrence_network(papers, 'jel_l2')
    draw_network(node_counts, edge_weights,
                f'{journal_name} {period}: JEL Subcategory Network',
                os.path.join(charts_dir, f'{period}_jel_l2.png'),
                min_node_count=2, min_edge_weight=1, max_nodes=30)
    
    # 3. 方法网络
    node_counts, edge_weights = build_cooccurrence_network(papers, 'method')
    draw_network(node_counts, edge_weights,
                f'{journal_name} {period}: Methods Network',
                os.path.join(charts_dir, f'{period}_methods.png'),
                min_node_count=2, min_edge_weight=1, max_nodes=20)
    
    # 4. JEL-Method 跨类型网络
    node_counts, edge_weights = build_cooccurrence_network(papers, 'jel_method')
    draw_network(node_counts, edge_weights,
                f'{journal_name} {period}: JEL-Method Cross Network',
                os.path.join(charts_dir, f'{period}_jel_method.png'),
                min_node_count=2, min_edge_weight=1, max_nodes=35)
    
    # 5. JEL-Industry 跨类型网络
    node_counts, edge_weights = build_cooccurrence_network(papers, 'jel_industry')
    draw_network(node_counts, edge_weights,
                f'{journal_name} {period}: JEL-Industry Cross Network',
                os.path.join(charts_dir, f'{period}_jel_industry.png'),
                min_node_count=2, min_edge_weight=1, max_nodes=40)


def process_journal(base_dir, cutoff='2026-02'):
    """处理整个期刊"""
    journal_name = os.path.basename(base_dir.rstrip('/'))
    
    print("=" * 60)
    print(f"  Tag Co-occurrence Network Generator")
    print(f"  Journal: {journal_name}")
    print("=" * 60)
    
    if not HAS_NETWORKX:
        print("\nError: networkx is required. Install with: pip install networkx")
        return
    
    # 收集所有论文用于汇总网络
    all_papers = []
    
    for folder in sorted(os.listdir(base_dir)):
        if folder > cutoff and 'inpress' not in folder.lower():
            continue
        if 'inpress' in folder.lower():
            continue
        
        folder_path = os.path.join(base_dir, folder)
        analysis_dir = os.path.join(folder_path, 'analysis')
        
        if not os.path.isdir(analysis_dir):
            continue
        
        papers = load_json_files(analysis_dir)
        if not papers:
            continue
        
        all_papers.extend(papers)
        
        # 处理单个双月
        process_period(papers, folder, base_dir, journal_name)
    
    # 生成汇总网络
    if all_papers:
        print(f"\n📊 Generating combined networks ({len(all_papers)} papers)...")
        
        output_dir = os.path.join(base_dir, 'networks')
        os.makedirs(output_dir, exist_ok=True)
        
        # 汇总 JEL L1 网络
        node_counts, edge_weights = build_cooccurrence_network(all_papers, 'jel_l1')
        draw_network(node_counts, edge_weights,
                    f'{journal_name}: JEL Category Network (All)',
                    os.path.join(output_dir, 'combined_jel_l1.png'),
                    min_node_count=3, min_edge_weight=2, max_nodes=19)
        
        # 汇总 JEL L2 网络
        node_counts, edge_weights = build_cooccurrence_network(all_papers, 'jel_l2')
        draw_network(node_counts, edge_weights,
                    f'{journal_name}: JEL Subcategory Network (All)',
                    os.path.join(output_dir, 'combined_jel_l2.png'),
                    min_node_count=5, min_edge_weight=2, max_nodes=40)
        
        # 汇总方法网络
        node_counts, edge_weights = build_cooccurrence_network(all_papers, 'method')
        draw_network(node_counts, edge_weights,
                    f'{journal_name}: Methods Network (All)',
                    os.path.join(output_dir, 'combined_methods.png'),
                    min_node_count=5, min_edge_weight=2, max_nodes=25)
        
        # 汇总 JEL-Method 网络
        node_counts, edge_weights = build_cooccurrence_network(all_papers, 'jel_method')
        draw_network(node_counts, edge_weights,
                    f'{journal_name}: JEL-Method Cross Network (All)',
                    os.path.join(output_dir, 'combined_jel_method.png'),
                    min_node_count=5, min_edge_weight=3, max_nodes=40)
        
        # 汇总 JEL-Industry 网络
        node_counts, edge_weights = build_cooccurrence_network(all_papers, 'jel_industry')
        draw_network(node_counts, edge_weights,
                    f'{journal_name}: JEL-Industry Cross Network (All)',
                    os.path.join(output_dir, 'combined_jel_industry.png'),
                    min_node_count=5, min_edge_weight=2, max_nodes=45)
    
    print(f"\n✅ {journal_name} network generation completed!")


def main():
    parser = argparse.ArgumentParser(description='Tag Co-occurrence Network Generator')
    parser.add_argument('directory', help='Journal directory')
    parser.add_argument('--cutoff', default='2026-02', help='Cutoff period')
    
    args = parser.parse_args()
    process_journal(args.directory, args.cutoff)


if __name__ == '__main__':
    main()
