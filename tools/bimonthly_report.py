#!/usr/bin/env python3
"""
双月汇总与热力图生成器

功能:
    1. 对每个双月目录生成汇总报告
    2. 生成各标签类型的热力图 (行业、JEL三级、方法)

JEL 分类层级:
    - Level 1: 单字母 (A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, Z)
    - Level 2: 字母+1位数字 (A1, B2, C3, ...)
    - Level 3: 完整代码 (A11, B21, C32, ...)

Usage:
    python bimonthly_report.py CER05-06/
    python bimonthly_report.py 经济研究05-06/
"""

import os
import json
import re
import argparse
from collections import Counter, defaultdict
from datetime import datetime

# JEL 一级分类含义 (English only)
JEL_LEVEL1_NAMES = {
    'A': 'General Econ & Teaching',
    'B': 'History of Thought',
    'C': 'Math & Quant Methods',
    'D': 'Microeconomics',
    'E': 'Macro & Monetary',
    'F': 'International Econ',
    'G': 'Financial Econ',
    'H': 'Public Econ',
    'I': 'Health, Education, Welfare',
    'J': 'Labor & Demographics',
    'K': 'Law & Economics',
    'L': 'Industrial Organization',
    'M': 'Business Admin',
    'N': 'Economic History',
    'O': 'Development & Tech',
    'P': 'Economic Systems',
    'Q': 'Agricultural & Environ',
    'R': 'Urban & Regional',
    'Z': 'Other Special Topics',
}

# 截止期限
CUTOFF_PERIOD = '2026-02'

# 检查是否有matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # 非交互模式
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
    
    # 设置英文字体
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed, skipping charts")


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


def normalize_method(method):
    """
    标准化方法名称，合并同类项
    - 统一大小写
    - 去除多余空格
    - 标准化常见变体
    """
    if not method:
        return None
    
    # 去除首尾空格，统一为小写
    m = method.strip().lower()
    
    # 去除多余空格
    m = re.sub(r'\s+', ' ', m)
    
    # 去除括号内容（如 "(DID)", "(did)"）
    m = re.sub(r'\s*\([^)]*\)\s*', ' ', m).strip()
    
    # 标准化常见变体 (英文)
    normalizations = {
        # DID 变体
        r'.*difference.?in.?difference.*': 'DID',
        r'^did$': 'DID',
        r'^diff.?in.?diff$': 'DID',
        r'^staggered did$': 'Staggered DID',
        r'^multi.?period did$': 'Staggered DID',
        r'^event study$': 'Event Study',
        
        # IV 变体
        r'^iv$': 'IV',
        r'.*instrumental variable.*': 'IV',
        r'^2sls$': '2SLS',
        r'.*two.?stage least squares.*': '2SLS',
        
        # 面板数据变体
        r'.*panel data.*': 'Panel Data',
        r'.*panel regression.*': 'Panel Regression',
        r'.*fixed effect.*': 'Fixed Effects',
        r'^fe$': 'Fixed Effects',
        r'.*random effect.*': 'Random Effects',
        
        # RDD 变体
        r'^rdd$': 'RDD',
        r'.*regression discontinuity.*': 'RDD',
        
        # PSM 变体
        r'^psm$': 'PSM',
        r'.*propensity score.*': 'PSM',
        
        # 其他常见方法
        r'^ols$': 'OLS',
        r'.*ordinary least squares.*': 'OLS',
        r'^gmm$': 'GMM',
        r'.*generalized method of moments.*': 'GMM',
        r'.*machine learning.*': 'Machine Learning',
        r'^ml$': 'Machine Learning',
        r'^nlp$': 'NLP',
        r'.*natural language processing.*': 'NLP',
        r'.*text analysis.*': 'Text Analysis',
        r'.*structural model.*': 'Structural Model',
        r'.*structural estimation.*': 'Structural Model',
        r'.*general equilibrium.*': 'General Equilibrium',
        r'^dsge$': 'DSGE',
        r'.*game theor.*': 'Game Theory',
        r'.*experiment.*': 'Experiment',
        r'^rct$': 'RCT',
        r'.*randomized control.*': 'RCT',
        r'.*input.?output.*': 'Input-Output Analysis',
        r'.*spatial econometric.*': 'Spatial Econometrics',
        r'.*quantile regression.*': 'Quantile Regression',
        r'.*empirical analysis.*': 'Empirical Analysis',
        r'.*quasi.?experiment.*': 'Quasi-Experiment',
        r'.*heterogen.*analysis.*': 'Heterogeneity Analysis',
        r'.*mechanism analysis.*': 'Mechanism Analysis',
        r'.*robustness.*': 'Robustness Test',
        r'.*comparative analysis.*': 'Comparative Analysis',
        r'.*survey.*': 'Survey',
    }
    
    # 中文标准化
    cn_normalizations = {
        r'.*双重差分.*': 'DID',
        r'.*did.*': 'DID',
        r'.*工具变量.*': 'IV',
        r'.*面板.*': 'Panel Data',
        r'.*固定效应.*': 'Fixed Effects',
        r'.*随机效应.*': 'Random Effects',
        r'.*断点回归.*': 'RDD',
        r'.*倾向得分.*': 'PSM',
        r'.*一般均衡.*': 'General Equilibrium',
        r'.*博弈.*': 'Game Theory',
        r'.*准自然实验.*': 'Quasi-Experiment',
        r'.*自然实验.*': 'Natural Experiment',
        r'.*反事实.*': 'Counterfactual Analysis',
        r'.*理论.*模型.*': 'Theoretical Model',
        r'.*理论建模.*': 'Theoretical Model',
        r'.*机制分析.*': 'Mechanism Analysis',
        r'.*异质性.*': 'Heterogeneity Analysis',
        r'.*稳健性.*': 'Robustness Test',
        r'.*事件研究.*': 'Event Study',
        r'.*投入产出.*': 'Input-Output Analysis',
        r'.*空间计量.*': 'Spatial Econometrics',
        r'.*分位数回归.*': 'Quantile Regression',
        r'.*多元回归.*': 'Multiple Regression',
        r'.*比较静态.*': 'Comparative Statics',
        r'.*数值模拟.*': 'Numerical Simulation',
        r'.*文本分析.*': 'Text Analysis',
        r'.*机器学习.*': 'Machine Learning',
        r'.*深度学习.*': 'Deep Learning',
    }
    
    # 合并英文和中文规则
    all_rules = {**normalizations, **cn_normalizations}
    
    for pattern, replacement in all_rules.items():
        if re.match(pattern, m):
            return replacement
    
    # 首字母大写
    return m.title()


def extract_jel_levels(code):
    """
    从JEL代码提取三个级别
    例如: 'F14' -> ('F', 'F1', 'F14')
    """
    if not code or not isinstance(code, str):
        return None, None, None
    
    code = code.strip().upper()
    
    # 匹配 JEL 格式: 字母 + 数字
    match = re.match(r'^([A-Z])(\d{1,2})$', code)
    if not match:
        # 尝试只匹配字母
        if re.match(r'^[A-Z]$', code):
            return code, None, None
        return None, None, None
    
    letter = match.group(1)
    digits = match.group(2)
    
    level1 = letter                          # A, B, C, ...
    level2 = f"{letter}{digits[0]}"          # A1, B2, ...
    level3 = code                            # A11, B21, ...
    
    return level1, level2, level3


def should_include_period(period):
    """检查是否在截止期限内"""
    # 处理特殊命名
    if 'inpress' in period.lower():
        return False
    
    # 比较年月
    try:
        if period <= CUTOFF_PERIOD:
            return True
    except:
        pass
    
    return False


def load_json_files(analysis_dir):
    """加载分析目录下的所有JSON"""
    papers = []
    if not os.path.isdir(analysis_dir):
        return papers
    
    for f in os.listdir(analysis_dir):
        if f.endswith('.json'):
            path = os.path.join(analysis_dir, f)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    papers.append(json.load(fp))
            except:
                pass
    return papers


def collect_stats(papers):
    """收集统计数据，包括JEL三个级别"""
    # JEL 三个级别
    jel_level1 = Counter()
    jel_level2 = Counter()
    jel_level3 = Counter()
    
    industry_counter = Counter()
    method_counter = Counter()
    
    for p in papers:
        # JEL - 分三个级别统计
        for jel in p.get('jel_codes', []):
            code = jel.get('code', '') if isinstance(jel, dict) else str(jel)
            if code:
                l1, l2, l3 = extract_jel_levels(code)
                if l1:
                    jel_level1[l1] += 1
                if l2:
                    jel_level2[l2] += 1
                if l3:
                    jel_level3[l3] += 1
        
        # Industries - 翻译成英文
        for ind in p.get('industries', []):
            translated = translate_industry(ind)
            if translated:
                industry_counter[translated] += 1
        
        # Methods - 标准化后统计
        for m in p.get('methods', []):
            normalized = normalize_method(m)
            if normalized:
                method_counter[normalized] += 1
    
    return {
        'jel_l1': jel_level1,      # 一级: A, B, C, ...
        'jel_l2': jel_level2,      # 二级: A1, B2, ...
        'jel_l3': jel_level3,      # 三级: A11, B21, ...
        'jel': jel_level3,         # 兼容旧接口
        'industry': industry_counter,
        'method': method_counter,
        'total': len(papers)
    }


def generate_bimonthly_summary(folder_path, papers, output_path):
    """生成双月汇总Markdown"""
    stats = collect_stats(papers)
    folder_name = os.path.basename(folder_path)
    
    lines = []
    lines.append(f"# {folder_name} Bimonthly Summary")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\nPapers: **{stats['total']}**\n")
    
    # JEL Level 1
    if stats['jel_l1']:
        lines.append("## JEL Level 1 (Major Categories)\n")
        lines.append("| Code | Category | Count |")
        lines.append("|------|----------|-------|")
        for code, count in stats['jel_l1'].most_common(19):
            name = JEL_LEVEL1_NAMES.get(code, '')
            lines.append(f"| {code} | {name} | {count} |")
    
    # JEL Level 2
    if stats['jel_l2']:
        lines.append("\n## JEL Level 2 (Top 15)\n")
        lines.append("| JEL | Count |")
        lines.append("|-----|-------|")
        for code, count in stats['jel_l2'].most_common(15):
            lines.append(f"| {code} | {count} |")
    
    # JEL Level 3
    if stats['jel_l3']:
        lines.append("\n## JEL Level 3 (Top 15)\n")
        lines.append("| JEL | Count |")
        lines.append("|-----|-------|")
        for code, count in stats['jel_l3'].most_common(15):
            lines.append(f"| {code} | {count} |")
    
    # Industries
    if stats['industry']:
        lines.append("\n## Industries\n")
        lines.append("| Industry | Count |")
        lines.append("|----------|-------|")
        for ind, count in stats['industry'].most_common(15):
            lines.append(f"| {ind[:40]} | {count} |")
    
    # Methods
    if stats['method']:
        lines.append("\n## Methods\n")
        lines.append("| Method | Count |")
        lines.append("|--------|-------|")
        for m, count in stats['method'].most_common(15):
            lines.append(f"| {m[:40]} | {count} |")
    
    # 论文列表
    lines.append("\n## Paper List\n")
    lines.append("| # | Title | Keywords |")
    lines.append("|---|-------|----------|")
    for i, p in enumerate(papers, 1):
        title = p.get('title', 'N/A')[:50]
        kws = ', '.join(p.get('keywords', [])[:3])[:40]
        lines.append(f"| {i} | {title}... | {kws} |")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return stats


def generate_heatmap(data, title, output_path, top_n=20, label_map=None):
    """生成水平条形图（作为热力图替代）"""
    if not HAS_MATPLOTLIB or not data:
        return
    
    items = data.most_common(top_n)
    if not items:
        return
    
    # 使用label_map添加含义（如果提供）
    if label_map:
        labels = [f"{item[0]} ({label_map.get(item[0], '')})"[:35] for item in items]
    else:
        labels = [item[0][:30] for item in items]
    
    values = [item[1] for item in items]
    
    # 创建图形
    fig_height = max(6, len(items) * 0.4)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    
    # 颜色映射
    colors = plt.cm.YlOrRd([v / max(values) for v in values])
    
    # 水平条形图
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, values, color=colors)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # 最高在上
    ax.set_xlabel('Frequency')
    ax.set_title(title)
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars, values)):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, 
                str(val), va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def generate_combined_heatmap(all_stats, output_dir, stat_type, title_prefix, top_n=15, label_map=None):
    """生成跨双月的组合热力图"""
    if not HAS_MATPLOTLIB:
        return
    
    # 收集所有双月的数据（只包含截止期限内的）
    periods = sorted([p for p in all_stats.keys() if should_include_period(p)])
    
    if not periods:
        return
    
    # 找出所有时期的top items
    combined = Counter()
    for period in periods:
        combined.update(all_stats[period].get(stat_type, {}))
    
    top_items = [item[0] for item in combined.most_common(top_n)]
    
    if not top_items:
        return
    
    # 构建矩阵
    matrix = []
    for item in top_items:
        row = [all_stats[period].get(stat_type, {}).get(item, 0) for period in periods]
        matrix.append(row)
    
    # 创建热力图
    fig, ax = plt.subplots(figsize=(12, max(6, len(top_items) * 0.5)))
    
    # 绘制热力图
    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
    
    # 设置标签
    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels(periods, rotation=45, ha='right')
    ax.set_yticks(range(len(top_items)))
    
    # Y轴标签（可选添加含义）
    if label_map:
        y_labels = [f"{item} ({label_map.get(item, '')})"[:30] for item in top_items]
    else:
        y_labels = [item[:30] for item in top_items]
    ax.set_yticklabels(y_labels)
    
    # 添加数值
    max_val = max(max(row) for row in matrix) if matrix else 1
    for i in range(len(top_items)):
        for j in range(len(periods)):
            val = matrix[i][j]
            if val > 0:
                ax.text(j, i, str(val), ha='center', va='center', 
                       color='white' if val > max_val * 0.6 else 'black',
                       fontsize=8)
    
    ax.set_title(f'{title_prefix} - Bimonthly Trend Heatmap (through {CUTOFF_PERIOD})')
    plt.colorbar(im, ax=ax, label='Frequency')
    plt.tight_layout()
    
    output_path = os.path.join(output_dir, f'heatmap_{stat_type}.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Generated: {output_path}")


def process_journal(base_dir):
    """处理整个期刊目录"""
    journal_name = os.path.basename(base_dir.rstrip('/'))
    
    print(f"\n{'='*60}")
    print(f"  Processing: {journal_name}")
    print(f"  Cutoff: {CUTOFF_PERIOD}")
    print(f"{'='*60}")
    
    all_stats = {}
    
    # 遍历所有双月目录
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        analysis_dir = os.path.join(folder_path, 'analysis')
        
        if not os.path.isdir(analysis_dir):
            continue
        
        papers = load_json_files(analysis_dir)
        if not papers:
            continue
        
        # 检查是否在截止期限内
        include_in_combined = should_include_period(folder)
        status = "✓" if include_in_combined else "⏭ (skipped in combined)"
        
        print(f"\n📁 {folder} ({len(papers)} papers) {status}")
        
        # 生成双月汇总（所有目录都生成）
        summary_path = os.path.join(folder_path, 'summary.md')
        stats = generate_bimonthly_summary(folder_path, papers, summary_path)
        print(f"  ✓ Summary: {summary_path}")
        
        all_stats[folder] = stats
        
        # 生成单双月的条形图（所有目录都生成）
        if HAS_MATPLOTLIB:
            charts_dir = os.path.join(folder_path, 'charts')
            os.makedirs(charts_dir, exist_ok=True)
            
            # JEL Level 1 (大类)
            if stats['jel_l1']:
                generate_heatmap(stats['jel_l1'], f'{folder} JEL Level 1', 
                               os.path.join(charts_dir, 'jel_l1.png'), 
                               top_n=19, label_map=JEL_LEVEL1_NAMES)
            
            # JEL Level 2 (中类)
            if stats['jel_l2']:
                generate_heatmap(stats['jel_l2'], f'{folder} JEL Level 2',
                               os.path.join(charts_dir, 'jel_l2.png'), 
                               top_n=20)
            
            # JEL Level 3 (小类)
            if stats['jel_l3']:
                generate_heatmap(stats['jel_l3'], f'{folder} JEL Level 3',
                               os.path.join(charts_dir, 'jel_l3.png'), 
                               top_n=20)
            
            # 行业和方法
            if stats['industry']:
                generate_heatmap(stats['industry'], f'{folder} Industries',
                               os.path.join(charts_dir, 'industry.png'))
            if stats['method']:
                generate_heatmap(stats['method'], f'{folder} Methods',
                               os.path.join(charts_dir, 'method.png'))
            print(f"  ✓ Charts: {charts_dir}/")
    
    # 生成跨双月的组合热力图（只包含截止期限内的数据）
    included_periods = [p for p in all_stats.keys() if should_include_period(p)]
    if HAS_MATPLOTLIB and len(included_periods) > 1:
        print(f"\n📊 Generating combined heatmaps (through {CUTOFF_PERIOD})...")
        
        # JEL 三个级别的热力图
        generate_combined_heatmap(all_stats, base_dir, 'jel_l1', 
                                 f'{journal_name} JEL L1', top_n=19, label_map=JEL_LEVEL1_NAMES)
        generate_combined_heatmap(all_stats, base_dir, 'jel_l2', 
                                 f'{journal_name} JEL L2', top_n=15)
        generate_combined_heatmap(all_stats, base_dir, 'jel_l3', 
                                 f'{journal_name} JEL L3', top_n=15)
        
        # 行业和方法
        generate_combined_heatmap(all_stats, base_dir, 'industry', f'{journal_name} Industries')
        generate_combined_heatmap(all_stats, base_dir, 'method', f'{journal_name} Methods')
    
    print(f"\n✅ {journal_name} completed!")
    print(f"   Total directories: {len(all_stats)}")
    print(f"   Included in heatmap: {len(included_periods)} (through {CUTOFF_PERIOD})")
    print(f"   Total papers: {sum(s['total'] for s in all_stats.values())}")


def main():
    parser = argparse.ArgumentParser(description='Bimonthly Summary & Heatmap Generator')
    parser.add_argument('directory', help='Journal directory')
    
    args = parser.parse_args()
    process_journal(args.directory)


if __name__ == '__main__':
    main()
