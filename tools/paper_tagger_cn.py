#!/usr/bin/env python3
"""
中文期刊论文标签提取脚本

针对中文学术论文提取：
- 标题、作者
- 中文关键词
- 学科分类（CSSCI）
- 研究方法
- 研究领域

Usage:
    python tools/paper_tagger_cn.py paper.pdf
    python tools/paper_tagger_cn.py paper.pdf --json
    python tools/paper_tagger_cn.py paper.pdf --json -o result.json
"""

import re
import sys
import json
import argparse

# PDF 解析库
try:
    import fitz  # PyMuPDF
    USE_FITZ = True
except ImportError:
    try:
        import pdfplumber
        USE_FITZ = False
    except ImportError:
        print("请安装 PyMuPDF: pip install pymupdf")
        sys.exit(1)


# ============================================================
# CSSCI 学科分类
# ============================================================
CSSCI_CATEGORIES = {
    '经济学': ['经济', '产业', '市场', '企业', '金融', '投资', '贸易', '消费', '价格', '收入', '成本', '利润'],
    '管理学': ['管理', '治理', '决策', '战略', '组织', '激励', '机制', '绩效', '效率'],
    '政治学': ['政府', '政策', '制度', '改革', '体制', '公共', '治理'],
    '社会学': ['社会', '群体', '阶层', '流动', '结构'],
    '法学': ['法律', '法规', '立法', '司法', '诉讼', '权利'],
    '教育学': ['教育', '学校', '教学', '学生', '教师', '课程'],
    '统计学': ['统计', '数据', '样本', '估计', '检验'],
    '心理学': ['心理', '认知', '行为', '情绪', '动机'],
}

# ============================================================
# 中文研究方法关键词
# ============================================================
METHOD_KEYWORDS_CN = {
    # 理论方法
    '博弈论': ['博弈', '纳什均衡', '子博弈', '贝叶斯博弈', '信号博弈'],
    '机制设计': ['机制设计', '激励机制', '激励相容', '显示原理', '最优机制'],
    '契约理论': ['契约', '委托代理', '道德风险', '逆向选择', '信息不对称'],
    '一般均衡': ['一般均衡', '局部均衡', '均衡分析'],
    '动态优化': ['动态优化', '最优控制', '变分法', '动态规划'],
    '数理模型': ['数理模型', '理论模型', '分析框架'],
    
    # 实证方法
    'OLS回归': ['OLS', '最小二乘', '线性回归'],
    '面板数据': ['面板数据', '固定效应', '随机效应'],
    'DID': ['双重差分', 'DID', '差分法'],
    'RDD': ['断点回归', 'RDD'],
    'IV': ['工具变量', 'IV', '两阶段最小二乘', '2SLS'],
    'PSM': ['倾向得分匹配', 'PSM'],
    '结构估计': ['结构估计', '结构模型'],
    
    # 其他方法
    '案例研究': ['案例研究', '案例分析', '典型案例'],
    '问卷调查': ['问卷调查', '调查问卷', '调研'],
    '访谈': ['访谈', '深度访谈', '田野调查'],
    '文献综述': ['文献综述', '文献回顾', '研究述评'],
    '比较研究': ['比较研究', '比较分析', '对比分析'],
    '历史分析': ['历史分析', '历史演变', '发展历程'],
    '仿真模拟': ['仿真', '模拟', '数值模拟', '蒙特卡洛'],
}

# ============================================================
# 研究领域关键词
# ============================================================
DOMAIN_KEYWORDS_CN = {
    # 经济领域
    '产业经济': ['产业', '产业链', '供应链', '价值链', '产业集群', '产业政策'],
    '创新经济': ['创新', '研发', '技术进步', '专利', '知识产权', '科技'],
    '金融经济': ['金融', '银行', '证券', '保险', '投资', '融资', '资本'],
    '国际经济': ['国际贸易', '出口', '进口', '外资', 'FDI', '全球化'],
    '区域经济': ['区域', '城市', '城镇化', '空间', '集聚'],
    '劳动经济': ['劳动', '就业', '工资', '人力资本', '劳动力'],
    '环境经济': ['环境', '绿色', '低碳', '碳排放', '污染', '可持续'],
    '数字经济': ['数字', '互联网', '平台', '电商', '大数据', '人工智能'],
    
    # 管理领域
    '企业管理': ['企业', '公司', '组织', '战略', '竞争'],
    '公共管理': ['公共', '政府', '政策', '治理', '公共服务'],
    '创新管理': ['创新管理', '研发管理', '技术管理', '知识管理'],
    
    # 其他
    '制造业': ['制造', '工业', '生产', '智能制造'],
    '高技术产业': ['高技术', '高新技术', '高端', '芯片', '半导体', '集成电路'],
    '中小企业': ['中小企业', 'SME', '民营企业', '小微企业'],
}


def extract_text_from_pdf(pdf_path, max_pages=10):
    """从 PDF 提取文本"""
    text = ""
    try:
        if USE_FITZ:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                if i >= max_pages:
                    break
                text += page.get_text() + "\n"
            doc.close()
        else:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages[:max_pages]):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
    except Exception as e:
        print(f"PDF 解析错误: {e}", file=sys.stderr)
    return text


def extract_title_cn(text):
    """提取中文标题"""
    lines = text.split('\n')
    
    # 尝试找第一行非空的中文内容作为标题
    for line in lines[:10]:
        line = line.strip()
        # 跳过期刊名、年份、页码等
        if re.match(r'^\d{4}\s*年', line):
            continue
        if re.match(r'^第\s*\d+\s*期', line):
            continue
        if len(line) > 5 and len(line) < 50:
            # 检查是否包含中文
            if re.search(r'[\u4e00-\u9fff]', line):
                # 移除可能的作者前缀
                line = re.sub(r'^[\u4e00-\u9fff]{2,4}等[：:]\s*', '', line)
                return line
    
    return ""


def extract_authors_cn(text):
    """提取中文作者"""
    authors = []
    
    # 模式1: "作者：张三 李四"
    match = re.search(r'作者[：:]\s*([\u4e00-\u9fff\s、，,]+)', text)
    if match:
        author_str = match.group(1)
        authors = re.split(r'[、，,\s]+', author_str)
        authors = [a.strip() for a in authors if a.strip() and len(a) >= 2]
    
    # 模式2: 标题下一行是作者（2-4个汉字的名字）
    if not authors:
        lines = text.split('\n')
        for i, line in enumerate(lines[:15]):
            # 查找类似 "荣健欣   王大中   张天衡" 的行
            names = re.findall(r'[\u4e00-\u9fff]{2,4}', line)
            if 2 <= len(names) <= 6 and len(line.strip()) < 30:
                # 检查不是标题（标题通常更长）
                if not any(kw in line for kw in ['研究', '分析', '机制', '影响', '效应']):
                    authors = names
                    break
    
    return authors[:5]  # 最多返回5个作者


def extract_keywords_cn(text):
    """提取中文关键词"""
    keywords = []
    
    # 模式1: "关键词：xxx、xxx、xxx" 或 "关键词: xxx; xxx"
    patterns = [
        r'关键词[：:]\s*([^\n]+)',
        r'关\s*键\s*词[：:]\s*([^\n]+)',
        r'Keywords[：:]\s*([^\n]+)',  # 有些论文用英文标记但后面是中文
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            kw_str = match.group(1).strip()
            # 分割关键词（支持全角空格 \u3000、普通空格、分号、顿号等）
            kw_list = re.split(r'[\u3000；;、，,]+|\s{2,}', kw_str)
            for kw in kw_list:
                kw = kw.strip()
                # 清理关键词
                kw = re.sub(r'^[\d\.\s]+', '', kw)  # 移除开头的数字
                if kw and len(kw) >= 2 and len(kw) <= 20:
                    # 检查是否包含中文或有意义的英文
                    if re.search(r'[\u4e00-\u9fff]', kw) or re.match(r'^[A-Za-z]+$', kw):
                        keywords.append(kw)
            break
    
    return keywords[:10]  # 最多返回10个关键词


def extract_abstract_cn(text):
    """提取中文摘要"""
    # 模式: "内容提要：xxx" 或 "摘要：xxx"
    patterns = [
        r'内容提要[：:]\s*([^一二三四五六七八九十、]+)',
        r'摘\s*要[：:]\s*([^一二三四五六七八九十、]+)',
        r'【摘要】\s*([^【】]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # 清理摘要
            abstract = re.sub(r'\s+', ' ', abstract)
            # 截断到第一个明显的分节标记
            abstract = re.split(r'关键词|一、|1\.|引言|绑Ⅱ', abstract)[0]
            if len(abstract) > 50:
                return abstract[:500] + "..." if len(abstract) > 500 else abstract
    
    return ""


def classify_cssci(text, keywords):
    """CSSCI 学科分类"""
    categories = []
    combined_text = text[:5000] + ' '.join(keywords)
    
    for category, markers in CSSCI_CATEGORIES.items():
        score = sum(1 for marker in markers if marker in combined_text)
        if score >= 2:
            categories.append((category, score))
    
    # 按匹配度排序
    categories.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in categories[:3]]


def extract_methods_cn(text):
    """提取研究方法"""
    methods = []
    text_lower = text.lower()
    
    for method, markers in METHOD_KEYWORDS_CN.items():
        for marker in markers:
            if marker in text or marker.lower() in text_lower:
                if method not in methods:
                    methods.append(method)
                break
    
    return methods[:8]


def extract_domains_cn(text, keywords):
    """提取研究领域"""
    domains = []
    combined_text = text[:8000] + ' '.join(keywords)
    
    for domain, markers in DOMAIN_KEYWORDS_CN.items():
        for marker in markers:
            if marker in combined_text:
                if domain not in domains:
                    domains.append(domain)
                break
    
    return domains[:8]


def extract_funding_cn(text):
    """提取基金项目信息"""
    funding = []
    
    patterns = [
        r'国家自然科学基金[^。]*?（([^）]+)）',
        r'国家社会科学基金[^。]*?（([^）]+)）',
        r'国家重点研发计划',
        r'教育部人文社会科学[^。]*?（([^）]+)）',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            for m in matches:
                if isinstance(m, str) and m:
                    funding.append(m)
    
    return funding[:5]


def analyze_paper_cn(pdf_path, output_json=False):
    """分析中文论文"""
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("无法提取 PDF 文本")
        return None
    
    # 提取各项信息
    title = extract_title_cn(text)
    authors = extract_authors_cn(text)
    keywords = extract_keywords_cn(text)
    abstract = extract_abstract_cn(text)
    cssci_categories = classify_cssci(text, keywords)
    methods = extract_methods_cn(text)
    domains = extract_domains_cn(text, keywords)
    funding = extract_funding_cn(text)
    
    result = {
        'title': title,
        'authors': authors,
        'keywords': keywords,
        'abstract': abstract,
        'cssci_categories': cssci_categories,
        'methods': methods,
        'domains': domains,
        'funding': funding,
    }
    
    if output_json:
        return result
    
    # 格式化输出
    print(f"正在分析: {pdf_path}")
    print("=" * 60)
    print("中文论文分析结果")
    print("=" * 60)
    print()
    
    print(f"📄 标题: {title}")
    print()
    
    if authors:
        print(f"👤 作者 ({len(authors)}):")
        for author in authors:
            print(f"   • {author}")
        print()
    
    if keywords:
        print(f"🔑 关键词 ({len(keywords)}):")
        for kw in keywords:
            print(f"   • {kw}")
        print()
    
    if abstract:
        print(f"📝 摘要:")
        print(f"   {abstract[:200]}...")
        print()
    
    if cssci_categories:
        print(f"📚 CSSCI 学科分类:")
        for cat in cssci_categories:
            print(f"   • {cat}")
        print()
    
    if methods:
        print(f"🔬 研究方法 ({len(methods)}):")
        for method in methods:
            print(f"   • {method}")
        print()
    
    if domains:
        print(f"🏭 研究领域 ({len(domains)}):")
        for domain in domains:
            print(f"   • {domain}")
        print()
    
    if funding:
        print(f"💰 基金项目:")
        for f in funding:
            print(f"   • {f}")
        print()
    
    print("=" * 60)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="中文期刊论文标签提取")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("-o", "--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    result = analyze_paper_cn(args.pdf_path, output_json=args.json)
    
    if args.json and result:
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"结果已保存到: {args.output}")
        else:
            print(json_str)


if __name__ == "__main__":
    main()
