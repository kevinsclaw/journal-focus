#!/usr/bin/env python3
"""
论文标签统计脚本 - 基于 JSON 分析结果生成直方图统计

从 analysis/*.json 读取已有分析结果，生成 JEL、行业领域、研究方法的直方图。

Usage:
    # 从已有 JSON 生成统计
    python tools/paper_stats.py /path/to/pdfs/

    # 指定 JSON 目录
    python tools/paper_stats.py --json-dir /path/to/json/

    # 先分析再统计
    python tools/paper_stats.py /path/to/pdfs/ --analyze
"""

import os
import sys
import json
from collections import Counter


def load_json_results(json_dir):
    """从目录加载所有 JSON 分析结果"""
    results = []
    
    json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json')])
    
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            print(f"警告: 无法读取 {json_file}: {e}", file=sys.stderr)
    
    return results


def collect_stats(results):
    """从 JSON 结果中收集统计数据"""
    all_jel_codes = []
    all_jel_paper = []
    all_jel_inferred = []
    all_industries = []
    all_methods = []
    all_keywords = []
    
    for data in results:
        # 收集 JEL 代码
        for jel in data.get('jel_codes', []):
            code = jel.get('code', '')
            source = jel.get('source', 'inferred')
            confidence = jel.get('confidence', 0)
            
            if source == 'paper':
                all_jel_paper.append(code)
                all_jel_codes.append(code)
            elif confidence >= 0.6:  # 只统计置信度 >= 60% 的推断
                all_jel_inferred.append(code)
                all_jel_codes.append(code)
        
        # 收集行业领域
        industries = data.get('industries', []) or []
        all_industries.extend(industries)
        
        # 收集研究方法
        methods = data.get('methods', []) or []
        all_methods.extend(methods)
        
        # 收集关键词
        keywords = data.get('keywords', []) or []
        all_keywords.extend(keywords)
    
    # 合并语义相近的关键词
    normalized_keywords = normalize_keywords(all_keywords)
    
    return {
        'jel_all': Counter(all_jel_codes),
        'jel_paper': Counter(all_jel_paper),
        'jel_inferred': Counter(all_jel_inferred),
        'industries': Counter(all_industries),
        'methods': Counter(all_methods),
        'keywords': Counter(normalized_keywords),
        'total_papers': len(results)
    }


def normalize_keywords(keywords):
    """标准化关键词，合并语义相近的"""
    # 同义词映射（小写）
    synonyms = {
        'china': 'China',
        'chinese': 'China',
        'robot': 'Robots',
        'robots': 'Robots',
        'industrial robot': 'Robots',
        'industrial robots': 'Robots',
        'climate change': 'Climate change',
        'climate': 'Climate change',
        'gender': 'Gender',
        'gender differences': 'Gender',
        'gender gap': 'Gender',
        'gender earnings gap': 'Gender earnings gap',
        'fdi': 'FDI',
        'foreign direct investment': 'FDI',
        'gvc': 'Global Value Chains',
        'global value chain': 'Global Value Chains',
        'global value chains': 'Global Value Chains',
        'supply chain': 'Supply chain',
        'supply chains': 'Supply chain',
        'did': 'DID',
        'difference-in-differences': 'DID',
        'trade': 'Trade',
        'international trade': 'Trade',
        'trade policy': 'Trade policy',
        'trade sanctions': 'Trade sanctions',
        'air pollution': 'Air pollution',
        'pollution': 'Air pollution',
        'environment': 'Environment',
        'environmental': 'Environment',
        'environmental regulation': 'Environmental regulation',
        'unemployment': 'Unemployment',
        'labor': 'Labor',
        'labour': 'Labor',
        'labor market': 'Labor market',
        'labour market': 'Labor market',
        'digital economy': 'Digital economy',
        'digital': 'Digital economy',
        'fintech': 'Digital finance',
        'digital finance': 'Digital finance',
        'digital financial inclusion': 'Digital finance',
        'household': 'Household',
        'households': 'Household',
        'firm': 'Firm',
        'firms': 'Firm',
        'firm performance': 'Firm performance',
        'productivity': 'Productivity',
        'total factor productivity': 'Productivity (TFP)',
        'tfp': 'Productivity (TFP)',
        'energy': 'Energy',
        'clean energy': 'Clean energy',
        'migration': 'Migration',
        'rural migration': 'Migration',
        'labor migration': 'Migration',
        'hukou': 'Hukou (household registration)',
        'household registration': 'Hukou (household registration)',
        'health': 'Health',
        'personal health': 'Health',
        'covid': 'COVID-19',
        'covid-19': 'COVID-19',
        'university': 'University/Higher education',
        'higher education': 'University/Higher education',
        'research': 'Research',
        'research performance': 'Research performance',
        'innovation': 'Innovation',
        'technological progress': 'Technological progress',
        'technology': 'Technology',
    }
    
    normalized = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        # 查找同义词映射
        if kw_lower in synonyms:
            normalized.append(synonyms[kw_lower])
        else:
            # 保持原样但首字母大写
            normalized.append(kw.strip())
    
    return normalized


def print_histogram(counter, title, max_bar=40, top_n=20):
    """打印文本直方图"""
    if not counter:
        print(f"\n{title}: 无数据\n")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print(f"{'='*60}")
    
    sorted_items = counter.most_common(top_n)
    if not sorted_items:
        print("无数据")
        return
    
    max_count = sorted_items[0][1]
    
    for label, count in sorted_items:
        bar_len = int(count / max_count * max_bar)
        bar = "█" * bar_len
        label_display = label[:25] + "..." if len(label) > 28 else label
        print(f"  {label_display:<30} {bar} ({count})")
    
    total = sum(counter.values())
    unique = len(counter)
    print(f"\n  总计: {total} | 唯一值: {unique}")


def print_jel_by_category(jel_counter):
    """按一级分类统计 JEL"""
    category_counter = Counter()
    for code, count in jel_counter.items():
        if code:
            category_counter[code[0]] += count
    
    jel_names = {
        'A': 'A-通用经济学',
        'B': 'B-经济思想史',
        'C': 'C-数量方法',
        'D': 'D-微观经济学',
        'E': 'E-宏观/货币',
        'F': 'F-国际经济学',
        'G': 'G-金融学',
        'H': 'H-公共经济学',
        'I': 'I-健康/教育/福利',
        'J': 'J-劳动经济学',
        'K': 'K-法与经济学',
        'L': 'L-产业组织',
        'M': 'M-商业管理',
        'N': 'N-经济史',
        'O': 'O-经济发展/创新',
        'P': 'P-经济体制',
        'Q': 'Q-农业/环境',
        'R': 'R-城市/区域',
        'Z': 'Z-其他专题',
    }
    
    print(f"\n{'='*60}")
    print(f"📊 JEL 一级分类分布")
    print(f"{'='*60}")
    
    sorted_items = category_counter.most_common()
    if not sorted_items:
        print("无数据")
        return
    
    max_count = sorted_items[0][1]
    max_bar = 40
    
    for cat, count in sorted_items:
        bar_len = int(count / max_count * max_bar)
        bar = "█" * bar_len
        name = jel_names.get(cat, cat)
        print(f"  {name:<20} {bar} ({count})")


def print_jel_level2(jel_counter):
    """按二级分类统计 JEL"""
    level2_counter = Counter()
    for code, count in jel_counter.items():
        if code and len(code) >= 2:
            # 提取二级分类：如 J16 -> J1, D22 -> D2
            level2 = code[:2]
            level2_counter[level2] += count
    
    # JEL 二级分类名称（常见的）
    jel2_names = {
        'A1': 'A1-通用经济学',
        'A2': 'A2-经济学教育',
        'C1': 'C1-计量方法',
        'C2': 'C2-单方程模型',
        'C3': 'C3-多方程模型',
        'C5': 'C5-计量建模',
        'C6': 'C6-数学方法',
        'C7': 'C7-博弈论',
        'D1': 'D1-家庭行为',
        'D2': 'D2-生产与组织',
        'D3': 'D3-分配',
        'D8': 'D8-信息与不确定性',
        'D9': 'D9-跨期选择',
        'E2': 'E2-消费/储蓄/投资',
        'E5': 'E5-货币政策',
        'F1': 'F1-贸易',
        'F2': 'F2-国际要素流动',
        'F5': 'F5-国际关系',
        'F6': 'F6-全球化影响',
        'G2': 'G2-金融机构',
        'G3': 'G3-公司金融',
        'I1': 'I1-健康',
        'I2': 'I2-教育',
        'I3': 'I3-福利',
        'J1': 'J1-人口经济学',
        'J2': 'J2-劳动力需求',
        'J3': 'J3-工资与劳动成本',
        'J4': 'J4-特定劳动力市场',
        'J6': 'J6-流动与失业',
        'L1': 'L1-市场结构',
        'L2': 'L2-企业目标与行为',
        'N3': 'N3-劳动与人口史',
        'O1': 'O1-经济发展',
        'O3': 'O3-创新与技术变革',
        'P2': 'P2-社会主义经济',
        'Q1': 'Q1-农业',
        'Q4': 'Q4-能源',
        'Q5': 'Q5-环境经济学',
        'Z1': 'Z1-文化经济学',
    }
    
    print(f"\n{'='*60}")
    print(f"📊 JEL 二级分类分布")
    print(f"{'='*60}")
    
    sorted_items = level2_counter.most_common(20)
    if not sorted_items:
        print("无数据")
        return
    
    max_count = sorted_items[0][1]
    max_bar = 40
    
    for level2, count in sorted_items:
        bar_len = int(count / max_count * max_bar)
        bar = "█" * bar_len
        name = jel2_names.get(level2, level2)
        print(f"  {name:<25} {bar} ({count})")


def batch_analyze(pdf_dir, json_dir):
    """批量分析 PDF 并保存 JSON 结果"""
    import subprocess
    cwd = os.path.expanduser("~/xlerobot-sim")
    
    pdfs = sorted([f for f in os.listdir(pdf_dir) 
                   if f.endswith('.pdf') and 'Editorial_Board' not in f])
    
    os.makedirs(json_dir, exist_ok=True)
    
    print(f"\n批量分析 {len(pdfs)} 篇论文...\n", file=sys.stderr)
    
    for i, pdf in enumerate(pdfs, 1):
        pdf_path = os.path.join(pdf_dir, pdf)
        json_name = pdf.replace('.pdf', '.json')
        json_path = os.path.join(json_dir, json_name)
        
        print(f"[{i}/{len(pdfs)}] {pdf[:50]}...", file=sys.stderr)
        
        subprocess.run(
            ['python', 'tools/paper_tagger.py', pdf_path, '--json', '-o', json_path],
            cwd=cwd, capture_output=True
        )
    
    print(f"\n✅ JSON 结果已保存到: {json_dir}\n", file=sys.stderr)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="基于 JSON 分析结果生成标签统计直方图")
    parser.add_argument("directory", nargs='?', help="PDF 目录或 JSON 目录")
    parser.add_argument("--json-dir", help="指定 JSON 文件目录")
    parser.add_argument("--analyze", action="store_true", help="先批量分析生成 JSON")
    parser.add_argument("--output", "-o", help="输出统计结果到文件")
    
    args = parser.parse_args()
    
    if not args.directory and not args.json_dir:
        parser.print_help()
        sys.exit(1)
    
    input_dir = os.path.expanduser(args.directory) if args.directory else None
    
    # 确定 JSON 目录
    if args.json_dir:
        json_dir = os.path.expanduser(args.json_dir)
    elif args.analyze and input_dir:
        json_dir = os.path.join(input_dir, "analysis")
        batch_analyze(input_dir, json_dir)
    elif input_dir:
        if os.path.exists(os.path.join(input_dir, "analysis")):
            json_dir = os.path.join(input_dir, "analysis")
        elif any(f.endswith('.json') for f in os.listdir(input_dir)):
            json_dir = input_dir
        else:
            print("错误: 未找到 JSON 分析结果", file=sys.stderr)
            print("请先运行: python tools/paper_stats.py <pdf目录> --analyze", file=sys.stderr)
            sys.exit(1)
    else:
        print("错误: 请指定目录", file=sys.stderr)
        sys.exit(1)
    
    # 加载 JSON 结果
    print(f"从 {json_dir} 加载分析结果...", file=sys.stderr)
    results = load_json_results(json_dir)
    
    if not results:
        print("错误: 未找到任何 JSON 文件", file=sys.stderr)
        sys.exit(1)
    
    print(f"找到 {len(results)} 个分析结果\n", file=sys.stderr)
    
    # 收集统计数据
    stats = collect_stats(results)
    
    # 输出统计
    print(f"\n{'#'*60}")
    print(f"# 论文标签统计报告")
    print(f"# 论文数量: {stats['total_papers']}")
    print(f"{'#'*60}")
    
    print_jel_by_category(stats['jel_all'])
    print_jel_level2(stats['jel_all'])
    print_histogram(stats['jel_paper'], "JEL 三级分类 (📄 论文标注)", top_n=25)
    print_histogram(stats['jel_inferred'], "JEL 三级分类 (🔍 推断, ≥60%置信度)", top_n=15)
    print_histogram(stats['industries'], "行业领域分布", top_n=20)
    print_histogram(stats['methods'], "研究方法分布", top_n=20)
    print_histogram(stats['keywords'], "关键词分布 (已合并同义词)", top_n=25)
    
    print(f"\n{'='*60}")
    print("统计完成!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
