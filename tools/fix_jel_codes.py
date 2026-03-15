#!/usr/bin/env python3
"""
修复脚本：补齐遗漏的 JEL codes

扫描 PDF 提取原文 JEL codes，更新对应 JSON 文件
"""

import os
import re
import json
import sys

try:
    import fitz
except ImportError:
    print("请安装 PyMuPDF: pip install pymupdf")
    sys.exit(1)


def extract_jel_from_pdf(pdf_path: str) -> list:
    """从 PDF 提取原文 JEL codes"""
    try:
        pdf = fitz.open(pdf_path)
        text = ""
        for page in pdf[:3]:  # 只看前3页
            text += page.get_text()
        pdf.close()
    except Exception as e:
        print(f"  ⚠️ 无法读取 PDF: {e}")
        return []
    
    jel_codes = []
    
    # 多行格式: JEL codes:\nJ24\nL26\nQ53
    jel_block_match = re.search(
        r'JEL\s*[Cc]odes?[:\s]*\n?((?:[A-Z]\d{1,2}\s*\n?)+)',
        text, re.IGNORECASE
    )
    if jel_block_match:
        codes = re.findall(r'[A-Z]\d{1,2}', jel_block_match.group(1))
        jel_codes.extend(codes)
    
    # 单行格式: JEL: J24, L26, Q53
    if not jel_codes:
        patterns = [
            r'JEL\s*[Cc]lass(?:ification)?[:\s]*([A-Z]\d{1,2}(?:[,;\s]+[A-Z]\d{1,2})*)',
            r'JEL[:\s]+([A-Z]\d{1,2}(?:[,;\s]+[A-Z]\d{1,2})*)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                codes = re.findall(r'[A-Z]\d{1,2}', match)
                jel_codes.extend(codes)
            if jel_codes:
                break
    
    return list(set(jel_codes))  # 去重


def fix_json_jel(json_path: str, paper_jel_codes: list) -> bool:
    """更新 JSON 文件中的 JEL codes"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ⚠️ 无法读取 JSON: {e}")
        return False
    
    # 获取现有的 paper source JEL codes
    existing_paper_jel = set()
    existing_inferred_jel = []
    
    for jel in data.get('jel_codes', []):
        if jel.get('source') == 'paper':
            existing_paper_jel.add(jel['code'])
        else:
            existing_inferred_jel.append(jel)
    
    # 检查是否需要更新
    new_codes = [c for c in paper_jel_codes if c not in existing_paper_jel]
    
    if not new_codes:
        return False  # 无需更新
    
    # 构建新的 jel_codes 列表：paper source 在前
    new_jel_list = []
    
    # 添加所有 paper source 的 JEL（包括新发现的）
    all_paper_codes = existing_paper_jel | set(new_codes)
    for code in sorted(all_paper_codes):
        new_jel_list.append({
            'code': code,
            'confidence': 1.0,
            'source': 'paper'
        })
    
    # 保留 inferred 的（排除已在 paper 中的）
    for jel in existing_inferred_jel:
        if jel['code'] not in all_paper_codes:
            new_jel_list.append(jel)
    
    data['jel_codes'] = new_jel_list
    
    # 保存
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"  ⚠️ 无法保存 JSON: {e}")
        return False


def main():
    base_dir = "/home/ubuntu/.openclaw/workspace/CER05-06"
    
    total_fixed = 0
    total_scanned = 0
    
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        
        print(f"\n=== {folder} ===")
        
        analysis_dir = os.path.join(folder_path, "analysis")
        if not os.path.exists(analysis_dir):
            print("  无 analysis 目录，跳过")
            continue
        
        folder_fixed = 0
        
        for pdf_file in os.listdir(folder_path):
            if not pdf_file.endswith('.pdf'):
                continue
            if 'Editorial' in pdf_file or 'editorial' in pdf_file:
                continue
            
            total_scanned += 1
            pdf_path = os.path.join(folder_path, pdf_file)
            
            # 查找对应的 JSON
            base_name = pdf_file.replace('.pdf', '')
            json_path = os.path.join(analysis_dir, base_name + '.json')
            
            if not os.path.exists(json_path):
                continue
            
            # 提取 PDF 中的 JEL
            paper_jel = extract_jel_from_pdf(pdf_path)
            
            if paper_jel:
                # 尝试修复
                if fix_json_jel(json_path, paper_jel):
                    print(f"  ✓ 修复: {base_name[:50]}... → {paper_jel}")
                    folder_fixed += 1
                    total_fixed += 1
        
        if folder_fixed == 0:
            print("  无需修复")
        else:
            print(f"  本文件夹修复: {folder_fixed} 篇")
    
    print(f"\n{'='*50}")
    print(f"总计扫描: {total_scanned} 篇")
    print(f"总计修复: {total_fixed} 篇")


if __name__ == '__main__':
    main()
