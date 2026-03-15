#!/usr/bin/env python3
"""
论文汇总脚本 - 基于已有的 JSON 分析结果生成汇总表格

流程:
    1. 先用 paper_tagger.py --json -o result.json 分析论文并保存 JSON
    2. 再用 paper_summary.py 读取 JSON 生成汇总

Usage:
    # 方式1: 指定包含 JSON 文件的目录
    python tools/paper_summary.py --json-dir /path/to/json/

    # 方式2: 指定 PDF 目录，自动查找同目录下的 JSON（或 analysis/ 子目录）
    python tools/paper_summary.py /path/to/pdfs/

    # 方式3: 先批量分析再汇总（会先生成 JSON）
    python tools/paper_summary.py /path/to/pdfs/ --analyze

生成文件:
    - full_summary.md      完整表格（标题、JEL、行业、方法）
    - jel_summary_table.md JEL 分类汇总
    - keywords_summary.md  关键词汇总
"""

import subprocess
import os
import re
import sys
import json
from datetime import datetime


def batch_analyze(pdf_dir, output_dir):
    """批量分析 PDF 并保存 JSON 结果"""
    cwd = os.path.expanduser("~/xlerobot-sim")
    
    pdfs = sorted([f for f in os.listdir(pdf_dir) 
                   if f.endswith('.pdf') and 'Editorial_Board' not in f])
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n批量分析 {len(pdfs)} 篇论文...\n")
    
    for i, pdf in enumerate(pdfs, 1):
        pdf_path = os.path.join(pdf_dir, pdf)
        json_name = pdf.replace('.pdf', '.json')
        json_path = os.path.join(output_dir, json_name)
        
        print(f"[{i}/{len(pdfs)}] {pdf[:50]}...")
        
        # 调用 paper_tagger.py 生成 JSON
        subprocess.run(
            ['python', 'tools/paper_tagger.py', pdf_path, '--json', '-o', json_path],
            cwd=cwd, capture_output=True
        )
    
    print(f"\n✅ JSON 结果已保存到: {output_dir}\n")
    return output_dir


def load_json_results(json_dir):
    """从目录加载所有 JSON 分析结果"""
    results = []
    
    json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json')])
    
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 从文件名提取原始 PDF 名
                pdf_name = json_file.replace('.json', '.pdf')
                results.append((pdf_name, data))
        except Exception as e:
            print(f"警告: 无法读取 {json_file}: {e}")
    
    return results


def extract_info_from_json(data):
    """从 JSON 数据中提取标准化信息"""
    info = {
        'title': data.get('title', ''),
        'keywords': data.get('keywords', []),
        'paper_jels': [],
        'inferred_jels': [],
        'industries': data.get('industries', []) or [],
        'methods': data.get('methods', []) or []
    }
    
    # 分离论文标注和推断的 JEL
    for jel in data.get('jel_codes', []):
        code = jel.get('code', '')
        source = jel.get('source', 'inferred')
        if source == 'paper':
            info['paper_jels'].append(code)
        else:
            info['inferred_jels'].append(code)
    
    return info


def generate_full_summary(papers, output_dir):
    """生成完整汇总表格"""
    output_file = os.path.join(output_dir, "full_summary.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 论文完整分析汇总\n\n")
        f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**论文数量:** {len(papers)}\n\n")
        f.write("| # | 标题 | JEL | 来源 | 行业领域 | 研究方法 |\n")
        f.write("|---|------|-----|------|----------|----------|\n")
        
        for i, (filename, info) in enumerate(papers, 1):
            short_name = filename.replace('25-02-', '').split('---')[0].replace('_', ' ')[:35]
            
            if info['paper_jels']:
                jel_str = ', '.join(info['paper_jels'][:4])
                jel_source = '📄'
            else:
                jel_str = ', '.join(info['inferred_jels'][:3])
                jel_source = '🔍'
            
            ind_str = ', '.join(info['industries'][:3])
            method_str = ', '.join(info['methods'][:3])
            
            f.write(f"| {i} | {short_name} | {jel_str} | {jel_source} | {ind_str} | {method_str} |\n")
        
        f.write(f"\n**共 {len(papers)} 篇论文**\n")
    
    return output_file


def generate_jel_summary(papers, output_dir):
    """生成 JEL 汇总表格"""
    output_file = os.path.join(output_dir, "jel_summary_table.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# JEL 分类汇总\n\n")
        f.write("| # | 标题 | 论文标注 JEL | 推断 JEL |\n")
        f.write("|---|------|--------------|----------|\n")
        
        for i, (filename, info) in enumerate(papers, 1):
            short_name = filename.replace('25-02-', '').split('---')[0].replace('_', ' ')[:40]
            
            if info['paper_jels']:
                paper_str = ', '.join(info['paper_jels'][:5])
                inferred_str = '—'
            else:
                paper_str = '—'
                inferred_str = ', '.join(info['inferred_jels'][:3]) if info['inferred_jels'] else '?'
            
            f.write(f"| {i} | {short_name} | {paper_str} | {inferred_str} |\n")
        
        paper_count = sum(1 for _, info in papers if info['paper_jels'])
        inferred_count = len(papers) - paper_count
        f.write(f"\n**共 {len(papers)} 篇论文** (📄 论文标注: {paper_count} | 🔍 推断: {inferred_count})\n")
    
    return output_file


def generate_keywords_summary(papers, output_dir):
    """生成关键词汇总表格"""
    output_file = os.path.join(output_dir, "keywords_summary.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 关键词汇总\n\n")
        f.write("| # | 标题 | 关键词 |\n")
        f.write("|---|------|--------|\n")
        
        for i, (filename, info) in enumerate(papers, 1):
            short_name = filename.replace('25-02-', '').split('---')[0].replace('_', ' ')[:40]
            keywords_str = '; '.join(info['keywords']) if info['keywords'] else '—'
            f.write(f"| {i} | {short_name} | {keywords_str} |\n")
        
        f.write(f"\n**共 {len(papers)} 篇论文**\n")
    
    return output_file


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="基于 JSON 分析结果生成论文汇总表格")
    parser.add_argument("directory", help="PDF 目录或 JSON 目录")
    parser.add_argument("--json-dir", help="指定 JSON 文件目录")
    parser.add_argument("--analyze", action="store_true", help="先批量分析生成 JSON，再汇总")
    parser.add_argument("--output", "-o", help="输出目录（默认与输入目录相同）")
    
    args = parser.parse_args()
    
    input_dir = os.path.expanduser(args.directory)
    
    if not os.path.isdir(input_dir):
        print(f"错误: 目录不存在 - {input_dir}")
        sys.exit(1)
    
    # 确定 JSON 目录
    if args.json_dir:
        json_dir = os.path.expanduser(args.json_dir)
    elif args.analyze:
        # 批量分析，JSON 保存到 analysis/ 子目录
        json_dir = os.path.join(input_dir, "analysis")
        batch_analyze(input_dir, json_dir)
    else:
        # 尝试查找 JSON 文件
        if os.path.exists(os.path.join(input_dir, "analysis")):
            json_dir = os.path.join(input_dir, "analysis")
        elif any(f.endswith('.json') for f in os.listdir(input_dir)):
            json_dir = input_dir
        else:
            print("错误: 未找到 JSON 分析结果")
            print("请先运行: python tools/paper_summary.py <pdf目录> --analyze")
            sys.exit(1)
    
    # 输出目录
    output_dir = args.output if args.output else input_dir
    
    # 加载 JSON 结果
    print(f"从 {json_dir} 加载分析结果...")
    json_results = load_json_results(json_dir)
    
    if not json_results:
        print("错误: 未找到任何 JSON 文件")
        sys.exit(1)
    
    print(f"找到 {len(json_results)} 个分析结果\n")
    
    # 提取信息
    papers = [(filename, extract_info_from_json(data)) for filename, data in json_results]
    
    # 生成汇总
    print("生成汇总文件...")
    
    f1 = generate_full_summary(papers, output_dir)
    print(f"  ✅ {f1}")
    
    f2 = generate_jel_summary(papers, output_dir)
    print(f"  ✅ {f2}")
    
    f3 = generate_keywords_summary(papers, output_dir)
    print(f"  ✅ {f3}")
    
    print(f"\n完成! 共生成 3 个汇总文件。\n")


if __name__ == "__main__":
    main()
