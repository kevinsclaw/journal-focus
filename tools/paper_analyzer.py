#!/usr/bin/env python3
"""
论文标签提取脚本 - 统一版

支持中英文论文，使用 LLM 推断行业领域和研究方法。

功能：
- 自动检测中文/英文论文
- 提取标题、作者、关键词、摘要
- 英文论文：提取/推断 JEL 代码
- 中文论文：提取基金项目、CSSCI 分类
- LLM 推断：行业领域、研究方法（含模型名）

Usage:
    python tools/paper_analyzer.py paper.pdf
    python tools/paper_analyzer.py paper.pdf --provider bedrock
    python tools/paper_analyzer.py paper.pdf --json -o result.json
"""

import re
import sys
import json
import argparse
import os
from typing import List, Dict, Optional

# PDF 解析
try:
    import fitz  # PyMuPDF
except ImportError:
    print("请安装 PyMuPDF: pip install pymupdf")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)


# ============================================================
# LLM 配置
# ============================================================
LLM_PROVIDERS = {
    'bedrock': {
        'default_model': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        'region': 'us-east-1',
    },
    'openai': {
        'url': 'https://api.openai.com/v1/chat/completions',
        'default_model': 'gpt-4o-mini',
        'env_key': 'OPENAI_API_KEY',
    },
    'deepseek': {
        'url': 'https://api.deepseek.com/v1/chat/completions',
        'default_model': 'deepseek-chat',
        'env_key': 'DEEPSEEK_API_KEY',
    },
    'ollama': {
        'url': 'http://localhost:11434/api/chat',
        'default_model': 'qwen2.5:7b',
    },
}


# ============================================================
# JEL 关键词映射（英文论文）
# ============================================================
KEYWORD_JEL_MAPPING = {
    "trade": ["F1", "F14"], "export": ["F1", "F14"], "import": ["F1", "F14"],
    "labor": ["J2", "J6"], "employment": ["J2", "J6"], "wage": ["J3", "J31"],
    "gender": ["J16"], "education": ["I2", "I21", "I23"], "health": ["I1", "I12"],
    "environment": ["Q5", "Q54"], "climate": ["Q54"], "pollution": ["Q53"],
    "innovation": ["O3", "O31", "O33"], "technology": ["O3", "O33"],
    "robot": ["O33", "J23"], "finance": ["G2", "G21"], "firm": ["D2", "L2"],
    "productivity": ["D24", "O47"], "development": ["O1", "O12"],
    "urban": ["R1", "R11"], "agriculture": ["Q1", "Q12"], "energy": ["Q4", "Q41"],
    "household": ["D1", "D12"], "consumption": ["D12", "E21"],
}


# ============================================================
# CSSCI 学科分类（中文论文）
# ============================================================
CSSCI_CATEGORIES = {
    '经济学': ['经济', '产业', '市场', '企业', '金融', '投资', '贸易'],
    '管理学': ['管理', '治理', '决策', '战略', '组织', '激励', '机制'],
    '政治学': ['政府', '政策', '制度', '改革', '体制', '公共'],
    '社会学': ['社会', '群体', '阶层', '流动'],
    '法学': ['法律', '法规', '立法', '司法'],
    '教育学': ['教育', '学校', '教学', '学生'],
}


# ============================================================
# PDF 文本提取
# ============================================================
def extract_text_from_pdf(pdf_path: str, max_pages: int = 15) -> str:
    """从 PDF 提取文本"""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"PDF 解析错误: {e}", file=sys.stderr)
    return text


def detect_language(text: str) -> str:
    """检测论文语言"""
    # 统计中文字符比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text[:2000]))
    total_chars = len(text[:2000])
    
    if total_chars > 0 and chinese_chars / total_chars > 0.3:
        return 'zh'
    return 'en'


# ============================================================
# 基础信息提取
# ============================================================
def extract_title(text: str, lang: str) -> str:
    """提取标题"""
    lines = text.split('\n')[:20]
    
    for line in lines:
        line = line.strip()
        if len(line) < 10 or len(line) > 200:
            continue
        # 跳过期刊信息
        if re.match(r'^\d{4}', line) or 'http' in line.lower():
            continue
        if re.match(r'^第\s*\d+\s*期', line) or re.match(r'^Vol\.\s*\d+', line):
            continue
        
        if lang == 'zh':
            if re.search(r'[\u4e00-\u9fff]{5,}', line):
                # 移除作者前缀
                line = re.sub(r'^[\u4e00-\u9fff]{2,4}等[：:]\s*', '', line)
                return line
        else:
            if line[0].isupper() and not line.startswith('Abstract'):
                return line
    return ""


def extract_authors(text: str, lang: str) -> List[str]:
    """提取作者"""
    authors = []
    
    if lang == 'zh':
        # 中文：找标题下一行的作者名
        lines = text.split('\n')
        for line in lines[:15]:
            names = re.findall(r'[\u4e00-\u9fff]{2,4}', line)
            if 2 <= len(names) <= 6 and len(line.strip()) < 30:
                if not any(kw in line for kw in ['研究', '分析', '机制', '影响']):
                    authors = names[:5]
                    break
    else:
        # 英文：匹配常见作者格式
        match = re.search(r'(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)*)', text[:1500])
        if match:
            author_str = match.group(1)
            authors = [a.strip() for a in author_str.split(',')][:5]
    
    return authors


def extract_keywords(text: str, lang: str) -> List[str]:
    """提取关键词"""
    keywords = []
    
    if lang == 'zh':
        match = re.search(r'关键词[：:]\s*([^\n]+)', text)
        if match:
            kw_str = match.group(1)
            kw_list = re.split(r'[\u3000；;、，,]+|\s{2,}', kw_str)
            keywords = [kw.strip() for kw in kw_list if kw.strip() and 2 <= len(kw.strip()) <= 20]
    else:
        # 英文论文：处理多行格式的keywords
        # 格式可能是: "Keywords:\nkw1\nkw2\n..." 或 "Keywords: kw1; kw2; ..."
        patterns = [
            # 多行格式：Keywords: 后跟多行，直到 ABSTRACT 或 JEL 或 Introduction
            r'Keywords?[:\s]*\n((?:[A-Za-z][^\n]{2,50}\n){1,10})',
            # 单行格式：Keywords: kw1; kw2; kw3
            r'Keywords?[:\s]+([^\n]+)',
            r'Key\s*words?[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                kw_str = match.group(1)
                # 尝试按换行符分割（多行格式）
                if '\n' in kw_str:
                    kw_list = [line.strip() for line in kw_str.split('\n')]
                else:
                    # 按分号/逗号分割（单行格式）
                    kw_list = re.split(r'[;,·•]+', kw_str)
                # 过滤掉非关键词项
                stop_words = {'abstract', 'a b s t r a c t', 'jel', 'introduction', 'jel classification'}
                keywords = [kw.strip() for kw in kw_list 
                           if kw.strip() and 2 < len(kw.strip()) < 50 
                           and kw.strip().lower() not in stop_words]
                if keywords:
                    break
    
    return keywords[:10]


def extract_abstract(text: str, lang: str) -> str:
    """提取摘要"""
    if lang == 'zh':
        patterns = [
            r'内容提要[：:]\s*(.{50,}?)(?:关键词|一、)',
            r'摘\s*要[：:]\s*(.{50,}?)(?:关键词|一、)',
        ]
    else:
        patterns = [
            r'Abstract[:\s]*(.{100,2000}?)(?:Keywords|JEL|Introduction|1\.|$)',
        ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract[:800]
    
    return ""


# ============================================================
# JEL 代码提取（英文论文）
# ============================================================
def extract_jel_codes(text: str, keywords: List[str]) -> List[Dict]:
    """提取 JEL 代码"""
    jel_codes = []
    
    # 1. 直接匹配论文标注的 JEL（处理多行格式）
    # 先尝试提取 JEL 区块（直到 Keywords 或 Abstract）
    jel_block_match = re.search(
        r'JEL\s*[Cc]odes?[:\s]*\n?((?:[A-Z]\d{1,2}\s*\n?)+)',
        text, re.IGNORECASE
    )
    if jel_block_match:
        codes = re.findall(r'[A-Z]\d{1,2}', jel_block_match.group(1))
        for code in codes:
            if code not in [j['code'] for j in jel_codes]:
                jel_codes.append({
                    'code': code,
                    'confidence': 1.0,
                    'source': 'paper'
                })
    
    # 如果上面没找到，尝试其他格式
    if not jel_codes:
        patterns = [
            r'JEL\s*[Cc]lass(?:ification)?[:\s]*([A-Z]\d{1,2}(?:[,;\s]+[A-Z]\d{1,2})*)',
            r'JEL[:\s]+([A-Z]\d{1,2}(?:[,;\s]+[A-Z]\d{1,2})*)',
            r'Classification[:\s]*\n([A-Z]\d{1,2}(?:\n[A-Z]\d{1,2})*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                codes = re.findall(r'[A-Z]\d{1,2}', match)
                for code in codes:
                    if code not in [j['code'] for j in jel_codes]:
                        jel_codes.append({
                            'code': code,
                            'confidence': 1.0,
                            'source': 'paper'
                        })
    
    # 2. 基于关键词推断
    combined = ' '.join(keywords).lower() + ' ' + text[:3000].lower()
    inferred = {}
    
    for keyword, codes in KEYWORD_JEL_MAPPING.items():
        if keyword in combined:
            for code in codes:
                if code not in inferred and code not in [j['code'] for j in jel_codes]:
                    inferred[code] = 0.6
    
    for code, conf in list(inferred.items())[:5]:
        jel_codes.append({
            'code': code,
            'confidence': conf,
            'source': 'inferred'
        })
    
    return jel_codes[:10]


# ============================================================
# CSSCI 分类（中文论文）
# ============================================================
def classify_cssci(text: str, keywords: List[str]) -> List[str]:
    """CSSCI 学科分类"""
    categories = []
    combined_text = text[:5000] + ' '.join(keywords)
    
    for category, markers in CSSCI_CATEGORIES.items():
        score = sum(1 for marker in markers if marker in combined_text)
        if score >= 2:
            categories.append((category, score))
    
    categories.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in categories[:3]]


# ============================================================
# 基金项目提取（中文论文）
# ============================================================
def extract_funding(text: str) -> List[str]:
    """提取基金项目"""
    funding = []
    patterns = [
        r'国家自然科学基金[^。]*?（([^）]+)）',
        r'国家社会科学基金[^。]*?（([^）]+)）',
        r'教育部人文社会科学[^。]*?（([^）]+)）',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            if m:
                funding.append(m)
    
    return funding[:5]


# ============================================================
# LLM 调用
# ============================================================
def call_llm(prompt: str, provider: str, model: str = None) -> str:
    """调用 LLM API"""
    config = LLM_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"未知的 LLM 提供商: {provider}")
    
    model = model or config.get('default_model')
    
    try:
        if provider == 'bedrock':
            return call_bedrock(prompt, model, config.get('region', 'us-east-1'))
        
        elif provider == 'ollama':
            response = requests.post(
                config['url'],
                json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False},
                timeout=60
            )
            response.raise_for_status()
            return response.json()['message']['content']
        
        else:  # openai/deepseek
            api_key = os.environ.get(config.get('env_key', ''))
            if not api_key:
                raise ValueError(f"请设置环境变量 {config['env_key']}")
            
            response = requests.post(
                config['url'],
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 1024, 'temperature': 0.3},
                timeout=60
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    
    except Exception as e:
        print(f"LLM 调用失败: {e}", file=sys.stderr)
        return ""


def call_bedrock(prompt: str, model: str, region: str) -> str:
    """调用 AWS Bedrock"""
    try:
        import boto3
        client = boto3.client('bedrock-runtime', region_name=region)
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        })
        
        response = client.invoke_model(
            modelId=model, body=body,
            contentType='application/json', accept='application/json'
        )
        
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    
    except Exception as e:
        print(f"Bedrock 调用失败: {e}", file=sys.stderr)
        return ""


def infer_with_llm(text: str, title: str, keywords: List[str], lang: str,
                   provider: str, model: str) -> Dict:
    """使用 LLM 推断行业领域和研究方法"""
    
    context = text[:8000]  # 约 5-6 页，覆盖方法论章节
    
    if lang == 'zh':
        prompt = f"""请分析以下中文学术论文，提取研究方法和行业领域。

论文标题：{title}
关键词：{', '.join(keywords) if keywords else '未知'}

论文内容：
{context}

请以 JSON 格式返回：

1. methods: 研究方法列表
   - 理论方法：博弈论、机制设计、一般均衡等
   - 实证方法：包含具体模型名，如 OLS、DID、固定效应模型、2SLS、PSM 等
   - 如有具体模型，写出完整名称

2. industries: 行业领域列表
   - 必须是具体行业/产业（如：制造业、半导体、金融业、农业、教育、医疗、互联网等）
   - 不要写学科名称

只返回 JSON：
{{"methods": ["方法1", "方法2"], "industries": ["行业1", "行业2"]}}
"""
    else:
        prompt = f"""Analyze this academic paper and extract research methods and industry domains.

Title: {title}
Keywords: {', '.join(keywords) if keywords else 'Unknown'}

Content:
{context}

Return JSON format:

1. methods: Research methods list
   - Include specific model names (OLS, DID, Fixed Effects, 2SLS, IV, PSM, etc.)
   - Include theoretical methods (Game Theory, Mechanism Design, etc.)

2. industries: Industry/sector list
   - Must be specific industries (Manufacturing, Semiconductor, Finance, Agriculture, Education, Healthcare, etc.)
   - NOT academic disciplines

Return only JSON:
{{"methods": ["method1", "method2"], "industries": ["industry1", "industry2"]}}
"""

    response = call_llm(prompt, provider, model)
    
    try:
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                'methods': result.get('methods', [])[:8],
                'industries': result.get('industries', [])[:8],
            }
    except json.JSONDecodeError:
        pass
    
    return {'methods': [], 'industries': []}


# ============================================================
# 主分析函数
# ============================================================
def analyze_paper(pdf_path: str, provider: str = 'bedrock', 
                  model: str = None, output_json: bool = False) -> Dict:
    """分析论文"""
    
    print(f"正在分析: {pdf_path}", file=sys.stderr)
    
    # 提取文本
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("无法提取 PDF 文本", file=sys.stderr)
        return None
    
    # 检测语言
    lang = detect_language(text)
    print(f"检测语言: {'中文' if lang == 'zh' else '英文'}", file=sys.stderr)
    
    # 基础信息提取
    title = extract_title(text, lang)
    authors = extract_authors(text, lang)
    keywords = extract_keywords(text, lang)
    abstract = extract_abstract(text, lang)
    
    # 语言相关提取
    jel_codes = []
    cssci_categories = []
    funding = []
    
    if lang == 'en':
        jel_codes = extract_jel_codes(text, keywords)
    else:
        cssci_categories = classify_cssci(text, keywords)
        funding = extract_funding(text)
    
    # LLM 推断
    print(f"使用 {provider} 推断行业/方法...", file=sys.stderr)
    llm_result = infer_with_llm(text, title, keywords, lang, provider, model)
    
    result = {
        'title': title,
        'authors': authors,
        'keywords': keywords,
        'abstract': abstract[:500] + '...' if len(abstract) > 500 else abstract,
        'language': lang,
        'methods': llm_result.get('methods', []),
        'industries': llm_result.get('industries', []),
    }
    
    if lang == 'en':
        result['jel_codes'] = jel_codes
    else:
        result['cssci_categories'] = cssci_categories
        result['funding'] = funding
    
    if output_json:
        return result
    
    # 格式化输出
    print("=" * 60)
    print(f"论文分析结果 ({'中文' if lang == 'zh' else '英文'})")
    print("=" * 60)
    print()
    
    print(f"📄 标题: {title}")
    if authors:
        print(f"👤 作者: {', '.join(authors)}")
    print()
    
    if keywords:
        print(f"🔑 关键词 ({len(keywords)}):")
        for kw in keywords:
            print(f"   • {kw}")
        print()
    
    if jel_codes:
        print(f"📊 JEL 分类 ({len(jel_codes)}):")
        for jel in jel_codes:
            source = "📄" if jel['source'] == 'paper' else "🔍"
            print(f"   {source} [{jel['code']}] 置信度: {jel['confidence']*100:.0f}%")
        print()
    
    if cssci_categories:
        print(f"📚 CSSCI 分类: {', '.join(cssci_categories)}")
        print()
    
    if funding:
        print(f"💰 基金项目: {', '.join(funding)}")
        print()
    
    methods = result.get('methods', [])
    if methods:
        print(f"🔬 研究方法 ({len(methods)}) [LLM]:")
        for m in methods:
            print(f"   • {m}")
        print()
    
    industries = result.get('industries', [])
    if industries:
        print(f"🏭 行业领域 ({len(industries)}) [LLM]:")
        for ind in industries:
            print(f"   • {ind}")
        print()
    
    print("=" * 60)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="论文标签提取（统一版）")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--provider", default="bedrock", 
                        choices=list(LLM_PROVIDERS.keys()),
                        help="LLM 提供商 (默认: bedrock)")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("-o", "--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    result = analyze_paper(args.pdf_path, args.provider, args.model, args.json)
    
    if args.json and result:
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"结果已保存到: {args.output}", file=sys.stderr)
        else:
            print(json_str)


if __name__ == "__main__":
    main()
