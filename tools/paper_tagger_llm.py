#!/usr/bin/env python3
"""
论文标签提取脚本 - LLM 增强版

使用 LLM 推断行业领域和研究方法，提高准确性。

Usage:
    # 使用 OpenAI API
    export OPENAI_API_KEY=sk-xxx
    python tools/paper_tagger_llm.py paper.pdf

    # 使用本地 Ollama
    python tools/paper_tagger_llm.py paper.pdf --provider ollama --model qwen2.5

    # 输出 JSON
    python tools/paper_tagger_llm.py paper.pdf --json -o result.json
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

# HTTP 请求
try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)


# ============================================================
# LLM 配置
# ============================================================
LLM_PROVIDERS = {
    'openai': {
        'url': 'https://api.openai.com/v1/chat/completions',
        'default_model': 'gpt-4o-mini',
        'env_key': 'OPENAI_API_KEY',
    },
    'anthropic': {
        'url': 'https://api.anthropic.com/v1/messages',
        'default_model': 'claude-3-haiku-20240307',
        'env_key': 'ANTHROPIC_API_KEY',
    },
    'ollama': {
        'url': 'http://localhost:11434/api/chat',
        'default_model': 'qwen2.5:7b',
        'env_key': None,
    },
    'deepseek': {
        'url': 'https://api.deepseek.com/v1/chat/completions',
        'default_model': 'deepseek-chat',
        'env_key': 'DEEPSEEK_API_KEY',
    },
    'bedrock': {
        'default_model': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        'region': 'us-east-1',
        'env_key': None,  # 使用 AWS credentials
    },
}


# ============================================================
# JEL 关键词映射（保留用于 JEL 推断）
# ============================================================
KEYWORD_JEL_MAPPING = {
    "trade": ["F1", "F14"],
    "international trade": ["F1", "F14"],
    "export": ["F1", "F14"],
    "import": ["F1", "F14"],
    "tariff": ["F13"],
    "labor": ["J2", "J6"],
    "employment": ["J2", "J6"],
    "wage": ["J3", "J31"],
    "gender": ["J16"],
    "education": ["I2", "I21", "I23"],
    "health": ["I1", "I12"],
    "environment": ["Q5", "Q54"],
    "climate": ["Q54"],
    "pollution": ["Q53"],
    "innovation": ["O3", "O31", "O33"],
    "technology": ["O3", "O33"],
    "robot": ["O33", "J23"],
    "automation": ["O33", "J23"],
    "finance": ["G2", "G21"],
    "banking": ["G21"],
    "firm": ["D2", "L2"],
    "productivity": ["D24", "O47"],
    "development": ["O1", "O12"],
    "poverty": ["I32", "O15"],
    "inequality": ["D63", "J31"],
    "urban": ["R1", "R11"],
    "rural": ["Q1", "R1"],
    "agriculture": ["Q1", "Q12"],
    "energy": ["Q4", "Q41"],
    "household": ["D1", "D12"],
    "consumption": ["D12", "E21"],
    "investment": ["E22", "G31"],
    "monetary": ["E5", "E52"],
    "fiscal": ["H2", "H3"],
    "tax": ["H2", "H24"],
    "policy": ["E6", "H1"],
}


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


def extract_title(text: str) -> str:
    """提取标题"""
    lines = text.split('\n')[:20]
    for line in lines:
        line = line.strip()
        if len(line) > 20 and len(line) < 200:
            # 跳过期刊信息、页码等
            if re.match(r'^\d{4}', line) or 'http' in line.lower():
                continue
            # 中文标题
            if re.search(r'[\u4e00-\u9fff]{5,}', line):
                return re.sub(r'^[\u4e00-\u9fff]{2,4}等[：:]\s*', '', line)
            # 英文标题（首字母大写）
            if line[0].isupper() and not line.startswith('Abstract'):
                return line
    return ""


def extract_keywords(text: str) -> List[str]:
    """提取关键词"""
    keywords = []
    
    # 英文关键词
    patterns = [
        r'Keywords?[:\s]+([^\n]+)',
        r'Key\s*words?[:\s]+([^\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            kw_str = match.group(1)
            kw_list = re.split(r'[;,·•]+', kw_str)
            keywords = [kw.strip() for kw in kw_list if kw.strip() and len(kw.strip()) > 2]
            if keywords:
                return keywords[:10]
    
    # 中文关键词
    match = re.search(r'关键词[：:]\s*([^\n]+)', text)
    if match:
        kw_str = match.group(1)
        kw_list = re.split(r'[\u3000；;、，,]+|\s{2,}', kw_str)
        keywords = [kw.strip() for kw in kw_list if kw.strip() and len(kw.strip()) >= 2]
    
    return keywords[:10]


def extract_abstract(text: str) -> str:
    """提取摘要"""
    # 英文摘要
    match = re.search(r'Abstract[:\s]*(.{100,2000}?)(?:Keywords|JEL|Introduction|1\.|$)', 
                      text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()[:800]
    
    # 中文摘要
    patterns = [
        r'内容提要[：:]\s*(.{50,}?)(?:关键词|一、)',
        r'摘\s*要[：:]\s*(.{50,}?)(?:关键词|一、)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()[:800]
    
    return ""


def extract_jel_codes(text: str, keywords: List[str]) -> List[Dict]:
    """提取 JEL 代码"""
    jel_codes = []
    
    # 1. 直接匹配论文标注的 JEL
    patterns = [
        r'JEL\s*[Cc]lass(?:ification)?[:\s]*([A-Z]\d{1,2}(?:[,;\s]+[A-Z]\d{1,2})*)',
        r'JEL[:\s]+([A-Z]\d{1,2}(?:[,;\s]+[A-Z]\d{1,2})*)',
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


def call_llm(prompt: str, provider: str = 'openai', model: str = None) -> str:
    """调用 LLM API"""
    config = LLM_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"未知的 LLM 提供商: {provider}")
    
    model = model or config['default_model']
    api_key = os.environ.get(config['env_key']) if config.get('env_key') else None
    
    if config.get('env_key') and not api_key:
        raise ValueError(f"请设置环境变量 {config['env_key']}")
    
    try:
        if provider == 'bedrock':
            return call_bedrock(prompt, model, config.get('region', 'us-east-1'))
        
        elif provider == 'ollama':
            response = requests.post(
                config['url'],
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'stream': False,
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()['message']['content']
        
        elif provider == 'anthropic':
            response = requests.post(
                config['url'],
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': model,
                    'max_tokens': 1024,
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()['content'][0]['text']
        
        else:  # openai 兼容格式 (openai, deepseek)
            response = requests.post(
                config['url'],
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1024,
                    'temperature': 0.3,
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    
    except requests.exceptions.RequestException as e:
        print(f"LLM API 调用失败: {e}", file=sys.stderr)
        return ""


def call_bedrock(prompt: str, model: str, region: str) -> str:
    """调用 AWS Bedrock"""
    try:
        import boto3
        
        client = boto3.client('bedrock-runtime', region_name=region)
        
        # Anthropic Claude 模型
        if 'anthropic' in model:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            })
            
            response = client.invoke_model(
                modelId=model,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
        
        else:
            raise ValueError(f"不支持的 Bedrock 模型: {model}")
    
    except ImportError:
        print("请安装 boto3: pip install boto3", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Bedrock 调用失败: {e}", file=sys.stderr)
        return ""


def infer_with_llm(text: str, title: str, keywords: List[str], 
                   provider: str, model: str) -> Dict:
    """使用 LLM 推断行业领域和研究方法"""
    
    # 准备上下文（摘要 + 部分正文）
    context = text[:4000]
    
    prompt = f"""请分析以下学术论文，提取研究方法和行业领域。

论文标题：{title}
关键词：{', '.join(keywords) if keywords else '未知'}

论文内容（摘要及部分正文）：
{context}

请以 JSON 格式返回，包含两个字段：

1. methods: 研究方法列表，要求：
   - 包含具体的计量/统计模型名称（如：OLS、2SLS、DID、固定效应模型、Probit、Tobit、GMM等）
   - 包含理论方法（如：博弈论、机制设计、一般均衡模型等）
   - 如果论文使用了特定模型，请写出模型全称

2. industries: 行业领域列表，要求：
   - 必须是具体行业/产业属性（如：半导体、制造业、农业、金融业、教育、医疗、房地产、新能源、互联网等）
   - 不要写学科分类（不要写"劳动经济学"、"产业经济"等学科名）
   - 写论文研究涉及的具体行业

只返回 JSON，不要其他解释。示例格式：
{{"methods": ["DID (双重差分)", "双向固定效应模型", "2SLS"], "industries": ["制造业", "机器人", "劳动力市场"]}}
"""

    response = call_llm(prompt, provider, model)
    
    # 解析 JSON
    try:
        # 提取 JSON 部分
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


def analyze_paper(pdf_path: str, provider: str = 'openai', 
                  model: str = None, output_json: bool = False) -> Dict:
    """分析论文"""
    
    print(f"正在分析: {pdf_path}", file=sys.stderr)
    
    # 提取文本
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("无法提取 PDF 文本", file=sys.stderr)
        return None
    
    # 基础信息提取（正则）
    title = extract_title(text)
    keywords = extract_keywords(text)
    abstract = extract_abstract(text)
    jel_codes = extract_jel_codes(text, keywords)
    
    # LLM 推断行业和方法
    print(f"使用 {provider}/{model or 'default'} 推断...", file=sys.stderr)
    llm_result = infer_with_llm(text, title, keywords, provider, model)
    
    result = {
        'title': title,
        'keywords': keywords,
        'abstract': abstract[:500] + '...' if len(abstract) > 500 else abstract,
        'jel_codes': jel_codes,
        'methods': llm_result.get('methods', []),
        'industries': llm_result.get('industries', []),
    }
    
    if output_json:
        return result
    
    # 格式化输出
    print("=" * 60)
    print("论文分析结果 (LLM 增强)")
    print("=" * 60)
    print()
    
    print(f"📄 标题: {title}")
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
    
    methods = result.get('methods', [])
    if methods:
        print(f"🔬 研究方法 ({len(methods)}) [LLM 推断]:")
        for m in methods:
            print(f"   • {m}")
        print()
    
    industries = result.get('industries', [])
    if industries:
        print(f"🏭 行业领域 ({len(industries)}) [LLM 推断]:")
        for ind in industries:
            print(f"   • {ind}")
        print()
    
    print("=" * 60)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="论文标签提取 - LLM 增强版")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--provider", default="openai", 
                        choices=list(LLM_PROVIDERS.keys()),
                        help="LLM 提供商")
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
