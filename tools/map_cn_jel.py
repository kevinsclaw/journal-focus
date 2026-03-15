#!/usr/bin/env python3
"""
中文期刊 JEL 代码映射脚本

根据中文关键词、行业领域、研究方法推断 JEL 代码并补齐到 JSON 文件

JEL 分类体系:
    A - 一般经济学与教学
    B - 经济思想史、方法论与异端学派
    C - 数学与计量方法
    D - 微观经济学
    E - 宏观经济学与货币经济学
    F - 国际经济学
    G - 金融经济学
    H - 公共经济学
    I - 健康、教育与福利
    J - 劳动与人口经济学
    K - 法律与经济学
    L - 产业组织
    M - 企业管理与商业经济学
    N - 经济史
    O - 经济发展、创新、技术变迁与增长
    P - 经济体制
    Q - 农业与自然资源经济学
    R - 城市、农村、区域、房地产与交通经济学
    Z - 其他特殊主题

Usage:
    python map_cn_jel.py 经济研究05-06/
"""

import os
import json
import re
import argparse
from collections import defaultdict


# 中文关键词到 JEL 的映射规则
KEYWORD_JEL_MAPPING = {
    # ===== A - 一般经济学 =====
    # ===== B - 经济思想 =====
    '马克思': ['B14', 'B51'],
    '习近平经济思想': ['B20', 'P20'],
    '中国特色社会主义': ['P20', 'P51'],
    '社会主义市场经济': ['P20', 'P51'],
    '政治经济学': ['B14', 'B51'],
    '新发展理念': ['O10', 'P20'],
    '新质生产力': ['O30', 'O40'],
    
    # ===== C - 计量方法 =====
    '双重差分': ['C21', 'C23'],
    'DID': ['C21', 'C23'],
    '工具变量': ['C26', 'C36'],
    '面板数据': ['C23', 'C33'],
    '机器学习': ['C45', 'C55'],
    '神经网络': ['C45', 'C55'],
    '大数据': ['C55', 'C81'],
    '文本分析': ['C45', 'C55'],
    '自然实验': ['C21', 'C90'],
    '准自然实验': ['C21', 'C90'],
    '回归分析': ['C21', 'C26'],
    '计量模型': ['C20', 'C50'],
    '一般均衡': ['C68', 'D58'],
    '博弈': ['C70', 'C72'],
    '实验': ['C90', 'C91'],
    
    # ===== D - 微观经济学 =====
    '消费': ['D12', 'E21'],
    '家庭': ['D10', 'D13'],
    '企业行为': ['D21', 'D22'],
    '生产函数': ['D24'],
    '决策': ['D81', 'D83'],
    '信息': ['D82', 'D83'],
    '不确定性': ['D81'],
    '风险': ['D81', 'G32'],
    '市场结构': ['D40', 'L10'],
    '垄断': ['D42', 'L12'],
    '竞争': ['D41', 'L13'],
    '外部性': ['D62', 'H23'],
    '公共品': ['D71', 'H41'],
    '福利': ['D60', 'I30'],
    '效率': ['D61', 'D24'],
    '资源配置': ['D61', 'O47'],
    '契约': ['D86'],
    '激励': ['D82', 'D86'],
    '代理': ['D82', 'G34'],
    
    # ===== E - 宏观经济学 =====
    '宏观经济': ['E00', 'E10'],
    '经济增长': ['E10', 'O40'],
    'GDP': ['E01', 'E23'],
    '经济周期': ['E32'],
    '波动': ['E32'],
    '通货膨胀': ['E31'],
    '价格': ['E31'],
    '货币政策': ['E52', 'E58'],
    '利率': ['E43', 'E52'],
    '央行': ['E58'],
    '财政政策': ['E62', 'H30'],
    '投资': ['E22', 'G11'],
    '储蓄': ['E21'],
    '就业': ['E24', 'J21'],
    '失业': ['E24', 'J64'],
    '工资': ['E24', 'J31'],
    'DSGE': ['E10', 'E37'],
    
    # ===== F - 国际经济学 =====
    '贸易': ['F10', 'F14'],
    '出口': ['F14'],
    '进口': ['F14'],
    '关税': ['F13'],
    '全球价值链': ['F14', 'F23'],
    'GVC': ['F14', 'F23'],
    '国际': ['F00'],
    '跨境': ['F21', 'F23'],
    '外资': ['F21', 'F23'],
    'FDI': ['F21', 'F23'],
    '汇率': ['F31'],
    '资本流动': ['F21', 'F32'],
    '开放': ['F10', 'F40'],
    '一带一路': ['F10', 'O19'],
    '自贸区': ['F13', 'F15'],
    
    # ===== G - 金融经济学 =====
    '金融': ['G00', 'G20'],
    '银行': ['G21'],
    '信贷': ['G21', 'G32'],
    '贷款': ['G21'],
    '债券': ['G12', 'G23'],
    '股票': ['G11', 'G12'],
    '资本市场': ['G10', 'G14'],
    '股价': ['G12', 'G14'],
    '融资': ['G30', 'G32'],
    '融资约束': ['G32'],
    '公司金融': ['G30', 'G32'],
    '公司治理': ['G34'],
    '信用': ['G21', 'G24'],
    '风险管理': ['G32'],
    '保险': ['G22'],
    '绿色金融': ['G20', 'Q56'],
    '数字金融': ['G20', 'O33'],
    '普惠金融': ['G21', 'O16'],
    '金融科技': ['G20', 'O33'],
    '系统性风险': ['G01', 'G28'],
    
    # ===== H - 公共经济学 =====
    '税收': ['H20', 'H25'],
    '增值税': ['H25'],
    '所得税': ['H24'],
    '减税': ['H20', 'H25'],
    '财政': ['H30', 'H50'],
    '政府支出': ['H50', 'H72'],
    '地方政府': ['H70', 'H77'],
    '地方债务': ['H63', 'H74'],
    '公共服务': ['H40', 'H44'],
    '社会保障': ['H55'],
    '养老': ['H55', 'J26'],
    '医保': ['H51', 'I13'],
    '转移支付': ['H77'],
    '财政分权': ['H77'],
    
    # ===== I - 健康、教育与福利 =====
    '健康': ['I10', 'I12'],
    '医疗': ['I11', 'I18'],
    '教育': ['I20', 'I21'],
    '人力资本': ['I26', 'J24'],
    '高等教育': ['I23'],
    '义务教育': ['I21', 'I28'],
    '收入分配': ['I30', 'D31'],
    '贫困': ['I32'],
    '扶贫': ['I38'],
    '不平等': ['I30', 'D63'],
    '共同富裕': ['I30', 'D63'],
    '住房': ['I31', 'R21'],
    
    # ===== J - 劳动与人口经济学 =====
    '劳动': ['J00', 'J20'],
    '劳动力': ['J21', 'J23'],
    '人口': ['J10', 'J11'],
    '生育': ['J13'],
    '老龄化': ['J11', 'J14'],
    '流动人口': ['J61'],
    '迁移': ['J61'],
    '农民工': ['J61', 'R23'],
    '性别': ['J16'],
    '工资差距': ['J31', 'J71'],
    '人才': ['J24', 'J44'],
    '就业': ['J21', 'J23'],
    
    # ===== K - 法律与经济学 =====
    '法律': ['K00'],
    '产权': ['K11', 'D23'],
    '知识产权': ['K11', 'O34'],
    '监管': ['K20', 'L51'],
    '反垄断': ['K21', 'L40'],
    
    # ===== L - 产业组织 =====
    '产业': ['L00', 'L60'],
    '制造业': ['L60'],
    '工业': ['L60'],
    '服务业': ['L80'],
    '企业': ['L20', 'D21'],
    '中小企业': ['L25'],
    '国有企业': ['L32', 'P31'],
    '民营企业': ['L22', 'L26'],
    '产业政策': ['L52'],
    '产业结构': ['L16', 'O14'],
    '产业升级': ['L16', 'O14'],
    '产业链': ['L14', 'L23'],
    '供应链': ['L14', 'L23'],
    '平台': ['L14', 'L86'],
    '数字平台': ['L14', 'L86'],
    '电子商务': ['L81'],
    '电商': ['L81'],
    
    # ===== M - 企业管理 =====
    '管理': ['M10'],
    '企业管理': ['M10', 'M14'],
    '战略': ['M10', 'L10'],
    '营销': ['M31'],
    '会计': ['M41'],
    '人力资源': ['M50', 'J24'],
    'ESG': ['M14', 'Q56'],
    '社会责任': ['M14'],
    
    # ===== N - 经济史 =====
    # ===== O - 经济发展与技术 =====
    '发展': ['O10', 'O20'],
    '经济发展': ['O10', 'O11'],
    '技术': ['O30', 'O33'],
    '创新': ['O31', 'O32'],
    '研发': ['O32'],
    'R&D': ['O32'],
    '专利': ['O34'],
    '技术进步': ['O33'],
    '技术转移': ['O33'],
    '数字化': ['O33'],
    '数字经济': ['O33', 'L86'],
    '人工智能': ['O33'],
    '机器人': ['O33', 'J23'],
    '自动化': ['O33', 'J23'],
    '智能制造': ['O33', 'L60'],
    
    # ===== P - 经济体制 =====
    '改革': ['P20', 'P30'],
    '市场化': ['P20', 'L10'],
    '国有': ['P31', 'L32'],
    '私有化': ['P31'],
    
    # ===== Q - 农业与环境 =====
    '农业': ['Q10', 'Q12'],
    '农村': ['Q10', 'R20'],
    '农户': ['Q12', 'D13'],
    '粮食': ['Q11', 'Q18'],
    '土地': ['Q15', 'R14'],
    '能源': ['Q40', 'Q41'],
    '环境': ['Q50', 'Q53'],
    '污染': ['Q53'],
    '碳': ['Q54', 'Q58'],
    '碳排放': ['Q54'],
    '碳减排': ['Q54', 'Q58'],
    '碳交易': ['Q54', 'Q58'],
    '绿色': ['Q56'],
    '可持续': ['Q01', 'Q56'],
    '气候': ['Q54'],
    
    # ===== R - 城市与区域 =====
    '城市': ['R10', 'R11'],
    '城镇化': ['R11', 'O18'],
    '区域': ['R10', 'R12'],
    '区域协调': ['R11', 'R58'],
    '空间': ['R12'],
    '房地产': ['R30', 'R31'],
    '房价': ['R31'],
    '住房': ['R21', 'R31'],
    '交通': ['R40', 'R41'],
    '高铁': ['R42'],
    '基础设施': ['R42', 'H54'],
    
    # ===== Z - 其他 =====
    '文化': ['Z10', 'Z11'],
}

# 行业到 JEL 的映射
INDUSTRY_JEL_MAPPING = {
    '制造业': ['L60', 'D24'],
    '金融业': ['G20', 'G21'],
    '银行业': ['G21'],
    '农业': ['Q10', 'Q12'],
    '服务业': ['L80'],
    '房地产': ['R30', 'R31'],
    '房地产业': ['R30', 'R31'],
    '互联网': ['L86', 'O33'],
    '电子商务': ['L81'],
    '数字经济': ['O33', 'L86'],
    '能源': ['Q40', 'Q41'],
    '电力': ['Q41', 'L94'],
    '电力行业': ['Q41', 'L94'],
    '交通运输': ['R40', 'L91'],
    '交通运输业': ['R40', 'L91'],
    '教育': ['I20', 'I21'],
    '医疗': ['I11', 'I18'],
    '公共服务': ['H40', 'H44'],
    '高新技术产业': ['O30', 'L63'],
    '供应链产业': ['L14', 'L23'],
    '人工智能': ['O33', 'C45'],
    '环保产业': ['Q50', 'Q56'],
    '贸易业': ['F10', 'L81'],
    '宏观经济': ['E00', 'E10'],
    '工业': ['L60'],
}


def extract_jel_from_text(text, mapping):
    """从文本中提取 JEL 代码"""
    jel_codes = defaultdict(float)
    
    text_lower = text.lower() if text else ''
    
    for keyword, codes in mapping.items():
        if keyword.lower() in text_lower or keyword in text:
            for code in codes:
                jel_codes[code] += 1.0 / len(codes)
    
    return jel_codes


def infer_jel_codes(paper):
    """推断论文的 JEL 代码"""
    jel_scores = defaultdict(float)
    
    # 从标题提取
    title = paper.get('title', '')
    title_jels = extract_jel_from_text(title, KEYWORD_JEL_MAPPING)
    for code, score in title_jels.items():
        jel_scores[code] += score * 2.0  # 标题权重更高
    
    # 从关键词提取
    keywords = paper.get('keywords', [])
    for kw in keywords:
        kw_jels = extract_jel_from_text(kw, KEYWORD_JEL_MAPPING)
        for code, score in kw_jels.items():
            jel_scores[code] += score * 1.5  # 关键词权重次之
    
    # 从行业领域提取
    industries = paper.get('industries', [])
    for ind in industries:
        ind_jels = extract_jel_from_text(ind, INDUSTRY_JEL_MAPPING)
        for code, score in ind_jels.items():
            jel_scores[code] += score * 1.0
        # 也用关键词映射
        ind_jels2 = extract_jel_from_text(ind, KEYWORD_JEL_MAPPING)
        for code, score in ind_jels2.items():
            jel_scores[code] += score * 0.8
    
    # 从方法提取
    methods = paper.get('methods', [])
    for m in methods:
        m_jels = extract_jel_from_text(m, KEYWORD_JEL_MAPPING)
        for code, score in m_jels.items():
            jel_scores[code] += score * 0.5  # 方法权重较低
    
    # 排序并返回 top codes
    sorted_jels = sorted(jel_scores.items(), key=lambda x: -x[1])
    
    result = []
    for code, score in sorted_jels[:8]:  # 最多8个
        if score >= 0.5:  # 最低阈值
            confidence = min(0.9, score / 3.0)  # 归一化置信度
            result.append({
                'code': code,
                'confidence': round(confidence, 2),
                'source': 'inferred_cn'
            })
    
    return result


def process_journal(base_dir, dry_run=False):
    """处理期刊目录"""
    updated = 0
    total = 0
    
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        
        analysis_dir = os.path.join(folder_path, "analysis")
        if not os.path.isdir(analysis_dir):
            continue
        
        print(f"\n📁 {folder}")
        
        for f in os.listdir(analysis_dir):
            if not f.endswith('.json'):
                continue
            
            path = os.path.join(analysis_dir, f)
            total += 1
            
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    paper = json.load(fp)
                
                # 检查是否已有 JEL
                existing_jels = paper.get('jel_codes', [])
                has_jels = len(existing_jels) > 0
                
                # 推断 JEL
                inferred_jels = infer_jel_codes(paper)
                
                if inferred_jels:
                    # 合并：保留已有的，添加新推断的
                    existing_codes = set()
                    for j in existing_jels:
                        code = j.get('code') if isinstance(j, dict) else j
                        existing_codes.add(code)
                    
                    new_jels = existing_jels.copy()
                    added = 0
                    for jel in inferred_jels:
                        if jel['code'] not in existing_codes:
                            new_jels.append(jel)
                            added += 1
                    
                    if added > 0:
                        paper['jel_codes'] = new_jels
                        
                        if not dry_run:
                            with open(path, 'w', encoding='utf-8') as fp:
                                json.dump(paper, fp, ensure_ascii=False, indent=2)
                        
                        title = paper.get('title', f)[:30]
                        codes = [j['code'] for j in inferred_jels[:5]]
                        print(f"  ✓ {title}... → {codes}")
                        updated += 1
            
            except Exception as e:
                print(f"  ⚠️ 错误 {f}: {e}")
    
    print(f"\n{'='*50}")
    print(f"总计: {total} 篇")
    print(f"更新: {updated} 篇")
    if dry_run:
        print("(dry-run 模式，未实际写入)")


def main():
    parser = argparse.ArgumentParser(description='中文期刊 JEL 代码映射')
    parser.add_argument('directory', help='期刊目录')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不写入')
    
    args = parser.parse_args()
    
    base_dir = args.directory.rstrip('/')
    print(f"处理目录: {base_dir}")
    
    process_journal(base_dir, args.dry_run)


if __name__ == '__main__':
    main()
