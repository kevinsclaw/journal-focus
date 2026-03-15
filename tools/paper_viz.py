#!/usr/bin/env python3
"""
论文标签可视化脚本 - 生成直方图和热力图

Usage:
    python tools/paper_viz.py /path/to/pdfs/
    python tools/paper_viz.py --json-dir /path/to/json/
"""

import os
import sys
import json
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 设置中文字体
import matplotlib
matplotlib.use('Agg')
# 显式指定中文字体路径
font_paths = [
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]
for fp in font_paths:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
        break
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配色方案
COLORS = {
    'primary': '#2563eb',      # 蓝色
    'secondary': '#7c3aed',    # 紫色
    'success': '#059669',      # 绿色
    'warning': '#d97706',      # 橙色
    'danger': '#dc2626',       # 红色
    'gradient': ['#3b82f6', '#8b5cf6', '#ec4899', '#f97316', '#eab308'],
}


def load_json_results(json_dir):
    """从目录加载所有 JSON 分析结果"""
    results = []
    json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json')])
    
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_filename'] = json_file.replace('.json', '')
                results.append(data)
        except Exception as e:
            print(f"警告: 无法读取 {json_file}: {e}", file=sys.stderr)
    
    return results


def normalize_keywords(keywords):
    """标准化关键词"""
    synonyms = {
        'china': 'China', 'chinese': 'China',
        'robot': 'Robots', 'robots': 'Robots', 'industrial robots': 'Robots',
        'climate change': 'Climate', 'climate': 'Climate',
        'gender': 'Gender', 'gender differences': 'Gender', 'gender gap': 'Gender',
        'fdi': 'FDI', 'foreign direct investment': 'FDI',
        'trade': 'Trade', 'international trade': 'Trade',
        'air pollution': 'Pollution', 'pollution': 'Pollution',
        'environment': 'Environment', 'environmental': 'Environment',
        'unemployment': 'Unemployment', 'labor': 'Labor', 'labour': 'Labor',
        'digital economy': 'Digital Economy', 'digital': 'Digital Economy',
        'digital financial inclusion': 'Digital Finance', 'fintech': 'Digital Finance',
    }
    
    normalized = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        normalized.append(synonyms.get(kw_lower, kw.strip()))
    return normalized


def collect_stats(results):
    """收集统计数据"""
    stats = {
        'jel_level1': Counter(),
        'jel_level2': Counter(),
        'jel_level3_paper': Counter(),
        'industries': Counter(),
        'methods': Counter(),
        'keywords': Counter(),
    }
    
    # 论文-JEL 关系矩阵
    paper_jel_matrix = defaultdict(set)
    
    for data in results:
        paper_name = data.get('title', data['_filename'])[:30]
        
        for jel in data.get('jel_codes', []):
            code = jel.get('code', '')
            source = jel.get('source', 'inferred')
            confidence = jel.get('confidence', 0)
            
            if source == 'paper' or confidence >= 0.6:
                if code:
                    stats['jel_level1'][code[0]] += 1
                    if len(code) >= 2:
                        stats['jel_level2'][code[:2]] += 1
                    paper_jel_matrix[paper_name].add(code[0])
                    
            if source == 'paper':
                stats['jel_level3_paper'][code] += 1
        
        for ind in (data.get('industries') or []):
            stats['industries'][ind] += 1
            
        for method in (data.get('methods') or []):
            stats['methods'][method] += 1
            
        for kw in normalize_keywords(data.get('keywords') or []):
            stats['keywords'][kw] += 1
    
    return stats, paper_jel_matrix, results


def plot_horizontal_bar(counter, title, ax, top_n=15, color=COLORS['primary']):
    """绘制水平条形图"""
    items = counter.most_common(top_n)
    if not items:
        ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
        return
    
    labels, values = zip(*reversed(items))  # 反转使最大的在上面
    y_pos = np.arange(len(labels))
    
    # 渐变色
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(labels)))
    
    bars = ax.barh(y_pos, values, color=colors, edgecolor='white', height=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel('出现次数', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    
    # 添加数值标签
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, 
                str(val), va='center', fontsize=8, color='#374151')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, max(values) * 1.15)


def plot_jel_heatmap(paper_jel_matrix, results, ax):
    """绘制论文-JEL一级分类热力图"""
    # JEL 一级分类
    jel_categories = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'Z']
    jel_names = {
        'A': '通用', 'B': '思想史', 'C': '数量', 'D': '微观', 'E': '宏观',
        'F': '国际', 'G': '金融', 'H': '公共', 'I': '教育健康', 'J': '劳动',
        'K': '法经济', 'L': '产业', 'M': '管理', 'N': '经济史', 'O': '发展创新',
        'P': '体制', 'Q': '农业环境', 'R': '区域', 'Z': '其他',
    }
    
    # 只保留有数据的 JEL 分类
    used_jels = set()
    for jels in paper_jel_matrix.values():
        used_jels.update(jels)
    jel_categories = [j for j in jel_categories if j in used_jels]
    
    # 构建矩阵
    papers = list(paper_jel_matrix.keys())[:20]  # 最多显示 20 篇
    matrix = np.zeros((len(papers), len(jel_categories)))
    
    for i, paper in enumerate(papers):
        for j, jel in enumerate(jel_categories):
            if jel in paper_jel_matrix[paper]:
                matrix[i, j] = 1
    
    # 绘制热力图
    im = ax.imshow(matrix, cmap='Blues', aspect='auto', vmin=0, vmax=1)
    
    ax.set_xticks(np.arange(len(jel_categories)))
    ax.set_yticks(np.arange(len(papers)))
    ax.set_xticklabels([f"{j}\n{jel_names.get(j, '')}" for j in jel_categories], fontsize=8)
    ax.set_yticklabels([p[:25] + '...' if len(p) > 25 else p for p in papers], fontsize=7)
    
    ax.set_title('论文 × JEL一级分类 热力图', fontsize=12, fontweight='bold', pad=10)
    ax.set_xlabel('JEL 一级分类', fontsize=10)
    
    # 添加网格
    ax.set_xticks(np.arange(len(jel_categories)+1)-.5, minor=True)
    ax.set_yticks(np.arange(len(papers)+1)-.5, minor=True)
    ax.grid(which='minor', color='white', linestyle='-', linewidth=2)
    
    return im


def plot_method_industry_heatmap(results, ax):
    """绘制研究方法-行业热力图"""
    # 收集所有方法和行业
    method_counter = Counter()
    industry_counter = Counter()
    co_occurrence = defaultdict(lambda: defaultdict(int))
    
    for data in results:
        methods = (data.get('methods') or [])[:5]
        industries = (data.get('industries') or [])[:5]
        
        for m in methods:
            method_counter[m] += 1
        for i in industries:
            industry_counter[i] += 1
        
        for m in methods:
            for i in industries:
                co_occurrence[m][i] += 1
    
    # 选取 top 方法和行业
    top_methods = [m for m, _ in method_counter.most_common(10)]
    top_industries = [i for i, _ in industry_counter.most_common(10)]
    
    # 构建矩阵
    matrix = np.zeros((len(top_methods), len(top_industries)))
    for i, m in enumerate(top_methods):
        for j, ind in enumerate(top_industries):
            matrix[i, j] = co_occurrence[m][ind]
    
    # 绘制
    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
    
    ax.set_xticks(np.arange(len(top_industries)))
    ax.set_yticks(np.arange(len(top_methods)))
    ax.set_xticklabels(top_industries, fontsize=8, rotation=45, ha='right')
    ax.set_yticklabels(top_methods, fontsize=8)
    
    ax.set_title('研究方法 × 行业领域 共现热力图', fontsize=12, fontweight='bold', pad=10)
    
    # 添加数值
    for i in range(len(top_methods)):
        for j in range(len(top_industries)):
            if matrix[i, j] > 0:
                ax.text(j, i, int(matrix[i, j]), ha='center', va='center', 
                       fontsize=7, color='white' if matrix[i, j] > matrix.max()/2 else 'black')
    
    return im


def generate_visualizations(json_dir, output_dir):
    """生成所有可视化图表"""
    print(f"从 {json_dir} 加载数据...")
    results = load_json_results(json_dir)
    
    if not results:
        print("错误: 未找到 JSON 文件")
        return
    
    print(f"找到 {len(results)} 篇论文，生成图表...")
    
    stats, paper_jel_matrix, results = collect_stats(results)
    
    # 图1: 直方图汇总 (2x3)
    fig1, axes1 = plt.subplots(2, 3, figsize=(16, 10))
    fig1.suptitle('CER 论文标签统计', fontsize=16, fontweight='bold', y=1.02)
    
    # JEL 一级
    jel1_names = {'A': 'A-通用', 'B': 'B-思想史', 'C': 'C-数量', 'D': 'D-微观', 
                  'E': 'E-宏观', 'F': 'F-国际', 'G': 'G-金融', 'H': 'H-公共',
                  'I': 'I-教育健康', 'J': 'J-劳动', 'K': 'K-法经济', 'L': 'L-产业',
                  'M': 'M-管理', 'N': 'N-经济史', 'O': 'O-发展', 'P': 'P-体制',
                  'Q': 'Q-农环', 'R': 'R-区域', 'Z': 'Z-其他'}
    jel1_counter = Counter({jel1_names.get(k, k): v for k, v in stats['jel_level1'].items()})
    plot_horizontal_bar(jel1_counter, 'JEL 一级分类', axes1[0, 0], top_n=12)
    
    # JEL 二级
    jel2_names = {'F1': 'F1-贸易', 'J1': 'J1-人口', 'Q5': 'Q5-环境', 'D8': 'D8-信息',
                  'O1': 'O1-发展', 'I2': 'I2-教育', 'O3': 'O3-创新', 'Q1': 'Q1-农业',
                  'L1': 'L1-市场', 'D2': 'D2-组织', 'J2': 'J2-劳动需求', 'G2': 'G2-金融机构'}
    jel2_counter = Counter({jel2_names.get(k, k): v for k, v in stats['jel_level2'].items()})
    plot_horizontal_bar(jel2_counter, 'JEL 二级分类', axes1[0, 1], top_n=12)
    
    # JEL 三级 (论文标注)
    plot_horizontal_bar(stats['jel_level3_paper'], 'JEL 三级 (论文标注)', axes1[0, 2], top_n=12)
    
    # 行业领域
    plot_horizontal_bar(stats['industries'], '行业领域', axes1[1, 0], top_n=12)
    
    # 研究方法
    plot_horizontal_bar(stats['methods'], '研究方法', axes1[1, 1], top_n=12)
    
    # 关键词
    plot_horizontal_bar(stats['keywords'], '关键词 (合并同义词)', axes1[1, 2], top_n=12)
    
    plt.tight_layout()
    fig1_path = os.path.join(output_dir, 'stats_histogram.png')
    fig1.savefig(fig1_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"  ✅ {fig1_path}")
    
    # 图2: 热力图
    fig2, axes2 = plt.subplots(1, 2, figsize=(16, 8))
    fig2.suptitle('CER 论文标签关系热力图', fontsize=16, fontweight='bold', y=1.02)
    
    plot_jel_heatmap(paper_jel_matrix, results, axes2[0])
    plot_method_industry_heatmap(results, axes2[1])
    
    plt.tight_layout()
    fig2_path = os.path.join(output_dir, 'stats_heatmap.png')
    fig2.savefig(fig2_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"  ✅ {fig2_path}")
    
    plt.close('all')
    print(f"\n完成! 图表保存到 {output_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="生成论文标签可视化图表")
    parser.add_argument("directory", nargs='?', help="PDF 目录")
    parser.add_argument("--json-dir", help="JSON 文件目录")
    parser.add_argument("--output", "-o", help="输出目录")
    
    args = parser.parse_args()
    
    if not args.directory and not args.json_dir:
        parser.print_help()
        sys.exit(1)
    
    input_dir = os.path.expanduser(args.directory) if args.directory else None
    
    # 确定 JSON 目录
    if args.json_dir:
        json_dir = os.path.expanduser(args.json_dir)
    elif input_dir:
        if os.path.exists(os.path.join(input_dir, "analysis")):
            json_dir = os.path.join(input_dir, "analysis")
        else:
            print("错误: 未找到 analysis/ 目录，请先运行 paper_summary.py --analyze")
            sys.exit(1)
    
    output_dir = args.output if args.output else input_dir
    
    generate_visualizations(json_dir, output_dir)


if __name__ == "__main__":
    main()
