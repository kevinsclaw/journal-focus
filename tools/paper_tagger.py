#!/usr/bin/env python3
"""
Paper Keyword Extractor and JEL Code Tagger

Extracts keywords from academic papers and assigns JEL classification codes.
https://www.aeaweb.org/econlit/jelCodes.php

Usage:
    python paper_tagger.py paper.pdf
    python paper_tagger.py paper.pdf --output result.json
    python paper_tagger.py paper.pdf --llm  # Use LLM for better classification
"""

import re
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

# JEL Classification Codes (主要类别和子类别)
JEL_CODES = {
    "A": {
        "name": "General Economics and Teaching",
        "subcodes": {
            "A1": "General Economics",
            "A10": "General",
            "A11": "Role of Economics; Role of Economists; Market for Economists",
            "A12": "Relation of Economics to Other Disciplines",
            "A13": "Relation of Economics to Social Values",
            "A14": "Sociology of Economics",
            "A2": "Economic Education and Teaching of Economics",
        }
    },
    "B": {
        "name": "History of Economic Thought, Methodology, and Heterodox Approaches",
        "subcodes": {
            "B1": "History of Economic Thought through 1925",
            "B2": "History of Economic Thought since 1925",
            "B3": "History of Economic Thought: Individuals",
            "B4": "Economic Methodology",
            "B5": "Current Heterodox Approaches",
        }
    },
    "C": {
        "name": "Mathematical and Quantitative Methods",
        "subcodes": {
            "C1": "Econometric and Statistical Methods and Methodology: General",
            "C10": "General",
            "C11": "Bayesian Analysis: General",
            "C12": "Hypothesis Testing: General",
            "C13": "Estimation: General",
            "C14": "Semiparametric and Nonparametric Methods: General",
            "C15": "Statistical Simulation Methods: General",
            "C18": "Methodological Issues: General",
            "C2": "Single Equation Models; Single Variables",
            "C21": "Cross-Sectional Models; Spatial Models; Treatment Effect Models; Quantile Regressions",
            "C23": "Panel Data Models; Spatio-temporal Models",
            "C24": "Truncated and Censored Models; Switching Regression Models; Threshold Regression Models",
            "C25": "Discrete Regression and Qualitative Choice Models; Discrete Regressors; Proportions; Probabilities",
            "C26": "Instrumental Variables (IV) Estimation",
            "C3": "Multiple or Simultaneous Equation Models; Multiple Variables",
            "C32": "Time-Series Models; Dynamic Quantile Regressions; Dynamic Treatment Effect Models",
            "C33": "Panel Data Models; Spatio-temporal Models",
            "C34": "Truncated and Censored Models; Switching Regression Models",
            "C35": "Discrete Regression and Qualitative Choice Models",
            "C36": "Instrumental Variables (IV) Estimation",
            "C38": "Classification Methods; Cluster Analysis; Principal Components; Factor Models",
            "C4": "Econometric and Statistical Methods: Special Topics",
            "C41": "Duration Analysis; Optimal Timing Strategies",
            "C5": "Econometric Modeling",
            "C50": "General",
            "C51": "Model Construction and Estimation",
            "C52": "Model Evaluation, Validation, and Selection",
            "C53": "Forecasting and Prediction Methods; Simulation Methods",
            "C54": "Quantitative Policy Modeling",
            "C55": "Large Data Sets: Modeling and Analysis",
            "C6": "Mathematical Methods; Programming Models; Mathematical and Simulation Modeling",
            "C61": "Optimization Techniques; Programming Models; Dynamic Analysis",
            "C62": "Existence and Stability Conditions of Equilibrium",
            "C63": "Computational Techniques; Simulation Modeling",
            "C7": "Game Theory and Bargaining Theory",
            "C8": "Data Collection and Data Estimation Methodology; Computer Programs",
        }
    },
    "D": {
        "name": "Microeconomics",
        "subcodes": {
            "D1": "Household Behavior and Family Economics",
            "D2": "Production and Organizations",
            "D21": "Firm Behavior: Theory",
            "D22": "Firm Behavior: Empirical Analysis",
            "D23": "Organizational Behavior; Transaction Costs; Property Rights",
            "D24": "Production; Cost; Capital; Capital, Total Factor, and Multifactor Productivity; Capacity",
            "D3": "Distribution",
            "D4": "Market Structure, Pricing, and Design",
            "D5": "General Equilibrium and Disequilibrium",
            "D6": "Welfare Economics",
            "D7": "Analysis of Collective Decision-Making",
            "D8": "Information, Knowledge, and Uncertainty",
            "D81": "Criteria for Decision-Making under Risk and Uncertainty",
            "D82": "Asymmetric and Private Information; Mechanism Design",
            "D83": "Search; Learning; Information and Knowledge; Communication; Belief; Unawareness",
            "D84": "Expectations; Speculations",
            "D85": "Network Formation and Analysis: Theory",
            "D86": "Economics of Contract: Theory",
            "D9": "Intertemporal Choice",
            "D91": "Role and Effects of Psychological, Emotional, Social, and Cognitive Factors on Decision Making",
        }
    },
    "E": {
        "name": "Macroeconomics and Monetary Economics",
        "subcodes": {
            "E1": "General Aggregative Models",
            "E2": "Consumption, Saving, Production, Investment, Labor Markets, and Informal Economy",
            "E3": "Prices, Business Fluctuations, and Cycles",
            "E32": "Business Fluctuations; Cycles",
            "E4": "Money and Interest Rates",
            "E5": "Monetary Policy, Central Banking, and the Supply of Money and Credit",
            "E6": "Macroeconomic Policy, Macroeconomic Aspects of Public Finance, and General Outlook",
        }
    },
    "F": {
        "name": "International Economics",
        "subcodes": {
            "F1": "Trade",
            "F10": "General",
            "F11": "Neoclassical Models of Trade",
            "F12": "Models of Trade with Imperfect Competition and Scale Economies; Fragmentation",
            "F13": "Trade Policy; International Trade Organizations",
            "F14": "Empirical Studies of Trade",
            "F15": "Economic Integration",
            "F16": "Trade and Labor Market Interactions",
            "F17": "Trade Forecasting and Simulation",
            "F18": "Trade and Environment",
            "F2": "International Factor Movements and International Business",
            "F21": "International Investment; Long-Term Capital Movements",
            "F22": "International Migration",
            "F23": "Multinational Firms; International Business",
            "F3": "International Finance",
            "F4": "Macroeconomic Aspects of International Trade and Finance",
            "F5": "International Relations, National Security, and International Political Economy",
            "F51": "International Conflicts; Negotiations; Sanctions",
            "F52": "National Security; Economic Nationalism",
            "F6": "Economic Impacts of Globalization",
        }
    },
    "G": {
        "name": "Financial Economics",
        "subcodes": {
            "G1": "General Financial Markets",
            "G10": "General",
            "G11": "Portfolio Choice; Investment Decisions",
            "G12": "Asset Pricing; Trading Volume; Bond Interest Rates",
            "G13": "Contingent Pricing; Futures Pricing",
            "G14": "Information and Market Efficiency; Event Studies; Insider Trading",
            "G15": "International Financial Markets",
            "G17": "Financial Forecasting and Simulation",
            "G2": "Financial Institutions and Services",
            "G3": "Corporate Finance and Governance",
            "G30": "General",
            "G31": "Capital Budgeting; Fixed Investment and Inventory Studies; Capacity",
            "G32": "Financing Policy; Financial Risk and Risk Management; Capital and Ownership Structure",
            "G33": "Bankruptcy; Liquidation",
            "G34": "Mergers; Acquisitions; Restructuring; Corporate Governance",
            "G38": "Government Policy and Regulation",
        }
    },
    "H": {
        "name": "Public Economics",
        "subcodes": {
            "H1": "Structure and Scope of Government",
            "H2": "Taxation, Subsidies, and Revenue",
            "H3": "Fiscal Policies and Behavior of Economic Agents",
            "H4": "Publicly Provided Goods",
            "H5": "National Government Expenditures and Related Policies",
            "H6": "National Budget, Deficit, and Debt",
            "H7": "State and Local Government; Intergovernmental Relations",
            "H8": "Miscellaneous Issues",
        }
    },
    "I": {
        "name": "Health, Education, and Welfare",
        "subcodes": {
            "I1": "Health",
            "I2": "Education and Research Institutions",
            "I3": "Welfare, Well-Being, and Poverty",
        }
    },
    "J": {
        "name": "Labor and Demographic Economics",
        "subcodes": {
            "J1": "Demographic Economics",
            "J2": "Demand and Supply of Labor",
            "J3": "Wages, Compensation, and Labor Costs",
            "J4": "Particular Labor Markets",
            "J5": "Labor-Management Relations, Trade Unions, and Collective Bargaining",
            "J6": "Mobility, Unemployment, Vacancies, and Immigrant Workers",
        }
    },
    "K": {
        "name": "Law and Economics",
        "subcodes": {
            "K1": "Basic Areas of Law",
            "K2": "Regulation and Business Law",
            "K3": "Other Substantive Areas of Law",
            "K4": "Legal Procedure, the Legal System, and Illegal Behavior",
        }
    },
    "L": {
        "name": "Industrial Organization",
        "subcodes": {
            "L1": "Market Structure, Firm Strategy, and Market Performance",
            "L10": "General",
            "L11": "Production, Pricing, and Market Structure; Size Distribution of Firms",
            "L12": "Monopoly; Monopolization Strategies",
            "L13": "Oligopoly and Other Imperfect Markets",
            "L14": "Transactional Relationships; Contracts and Reputation; Networks",
            "L15": "Information and Product Quality; Standardization and Compatibility",
            "L16": "Industrial Organization and Macroeconomics: Industrial Structure and Structural Change",
            "L2": "Firm Objectives, Organization, and Behavior",
            "L21": "Business Objectives of the Firm",
            "L22": "Firm Organization and Market Structure",
            "L23": "Organization of Production",
            "L24": "Contracting Out; Joint Ventures; Technology Licensing",
            "L25": "Firm Performance: Size, Diversification, and Scope",
            "L26": "Entrepreneurship",
            "L3": "Nonprofit Organizations and Public Enterprise",
            "L4": "Antitrust Issues and Policies",
            "L5": "Regulation and Industrial Policy",
            "L6": "Industry Studies: Manufacturing",
            "L66": "Food; Beverages; Cosmetics; Tobacco; Wine and Spirits",
            "L7": "Industry Studies: Primary Products and Construction",
            "L8": "Industry Studies: Services",
            "L9": "Industry Studies: Transportation and Utilities",
        }
    },
    "M": {
        "name": "Business Administration and Business Economics; Marketing; Accounting",
        "subcodes": {
            "M1": "Business Administration",
            "M10": "General",
            "M11": "Production Management",
            "M16": "International Business Administration",
            "M2": "Business Economics",
            "M21": "Business Economics",
        }
    },
    "N": {
        "name": "Economic History",
        "subcodes": {
            "N1": "Macroeconomics and Monetary Economics; Industrial Structure; Growth; Fluctuations",
            "N5": "Agriculture, Natural Resources, Environment, and Extractive Industries",
            "N7": "Transport, Trade, Energy, Technology, and Other Services",
        }
    },
    "O": {
        "name": "Economic Development, Innovation, Technological Change, and Growth",
        "subcodes": {
            "O1": "Economic Development",
            "O10": "General",
            "O11": "Macroeconomic Analyses of Economic Development",
            "O12": "Microeconomic Analyses of Economic Development",
            "O13": "Agriculture; Natural Resources; Energy; Environment; Other Primary Products",
            "O14": "Industrialization; Manufacturing and Service Industries; Choice of Technology",
            "O15": "Human Resources; Human Development; Income Distribution; Migration",
            "O2": "Development Planning and Policy",
            "O3": "Innovation; Research and Development; Technological Change; Intellectual Property Rights",
            "O4": "Economic Growth and Aggregate Productivity",
            "O5": "Economywide Country Studies",
        }
    },
    "P": {
        "name": "Economic Systems",
        "subcodes": {
            "P1": "Capitalist Systems",
            "P2": "Socialist Systems and Transitional Economies",
            "P3": "Socialist Institutions and Their Transitions",
            "P4": "Other Economic Systems",
            "P5": "Comparative Economic Systems",
        }
    },
    "Q": {
        "name": "Agricultural and Natural Resource Economics; Environmental and Ecological Economics",
        "subcodes": {
            "Q0": "General",
            "Q1": "Agriculture",
            "Q10": "General",
            "Q11": "Aggregate Supply and Demand Analysis; Prices",
            "Q12": "Micro Analysis of Farm Firms, Farm Households, and Farm Input Markets",
            "Q13": "Agricultural Markets and Marketing; Cooperatives; Agribusiness",
            "Q14": "Agricultural Finance",
            "Q15": "Land Ownership and Tenure; Land Reform; Land Use; Irrigation; Agriculture and Environment",
            "Q16": "R&D; Agricultural Technology; Biofuels; Agricultural Extension Services",
            "Q17": "Agriculture in International Trade",
            "Q18": "Agricultural Policy; Food Policy",
            "Q19": "Other",
            "Q2": "Renewable Resources and Conservation",
            "Q3": "Nonrenewable Resources and Conservation",
            "Q4": "Energy",
            "Q5": "Environmental Economics",
            "Q56": "Environment and Development; Environment and Trade; Sustainability",
        }
    },
    "R": {
        "name": "Urban, Rural, Regional, Real Estate, and Transportation Economics",
        "subcodes": {
            "R1": "General Regional Economics",
            "R2": "Household Analysis",
            "R3": "Real Estate Markets, Spatial Production Analysis, and Firm Location",
            "R4": "Transportation Economics",
            "R5": "Regional Government Analysis",
        }
    },
    "Y": {
        "name": "Miscellaneous Categories",
        "subcodes": {}
    },
    "Z": {
        "name": "Other Special Topics",
        "subcodes": {
            "Z1": "Cultural Economics; Economic Sociology; Economic Anthropology",
        }
    },
}

# 关键词到 JEL 代码的映射规则
KEYWORD_JEL_MAPPING = {
    # Q - Agricultural Economics
    "agriculture": ["Q1", "Q10"],
    "agricultural": ["Q1", "Q10"],
    "agri-food": ["Q13", "Q18"],
    "food": ["Q18", "L66"],
    "food security": ["Q18"],
    "farm": ["Q12"],
    "grain": ["Q11", "Q17"],
    "crop": ["Q11", "Q15"],
    
    # F - International Economics
    "import": ["F1", "F14"],
    "export": ["F1", "F14"],
    "trade": ["F1", "F10"],
    "international trade": ["F1", "F14"],
    "global value chain": ["F1", "F23"],
    "globalization": ["F6"],
    "tariff": ["F13"],
    
    # Supply Chain
    "supply chain": ["L14", "M11", "L23"],
    "supply chain resilience": ["L14", "M11"],
    "supply chain risk": ["G32", "M11"],
    "disruption": ["L14", "G32"],
    "resilience": ["L14", "D81"],
    
    # Risk
    "risk": ["G32", "D81"],
    "risk management": ["G32"],
    "risk co-movement": ["G12", "G15"],
    "market risk": ["G12", "G32"],
    "uncertainty": ["D81"],
    "volatility": ["G12"],
    
    # Diversification
    "diversification": ["G11", "L25"],
    "portfolio": ["G11"],
    
    # Methods
    "survival analysis": ["C41"],
    "cox model": ["C41"],
    "hazard model": ["C41"],
    "panel data": ["C23", "C33"],
    "regression": ["C21"],
    "econometric": ["C1"],
    
    # Firm/Enterprise
    "enterprise": ["D21", "L2"],
    "firm": ["D21", "L2"],
    "corporate": ["G3"],
    "state-owned": ["L32", "P31"],
    
    # Policy
    "policy": ["H0"],
    "trade policy": ["F13"],
    "agricultural policy": ["Q18"],
    
    # Education
    "education": ["I2", "I21"],
    "higher education": ["I23", "I26"],
    "college": ["I23"],
    "university": ["I23"],
    "school": ["I21"],
    
    # Gender / Labor / Family
    "gender": ["J16"],
    "women": ["J16"],
    "female": ["J16"],
    "empowerment": ["J16", "O15"],
    "household": ["D13", "D1"],
    "family": ["D13", "J12"],
    "marriage": ["J12"],
    "fertility": ["J13"],
    "labor": ["J2", "J21"],
    "employment": ["J21", "J23"],
    "wage": ["J31"],
    "income": ["D31", "J31"],
    
    # Development
    "development": ["O1", "O10"],
    "poverty": ["I32", "O15"],
    "inequality": ["D63", "O15"],
    
    # Finance
    "financial inclusion": ["G21", "O16"],
    "digital finance": ["G21", "O33"],
    "credit": ["G21"],
    "bank": ["G21"],
    "fintech": ["G23", "O33"],
    
    # Climate / Environment
    "climate": ["Q54"],
    "climate change": ["Q54", "Q56"],
    "temperature": ["Q54"],
    "precipitation": ["Q54"],
    "environment": ["Q5", "Q56"],
}


# 行业领域关键词映射
INDUSTRY_KEYWORDS = {
    # 制造业
    "semiconductor": "半导体",
    "chip": "半导体",
    "integrated circuit": "半导体",
    "manufacturing": "制造业",
    "automobile": "汽车",
    "automotive": "汽车",
    "vehicle": "汽车",
    "steel": "钢铁",
    "textile": "纺织",
    "pharmaceutical": "制药",
    "chemical": "化工",
    "electronics": "电子",
    "machinery": "机械",
    "equipment": "装备制造",
    # 能源
    "energy": "能源",
    "coal": "煤炭",
    "oil": "石油",
    "petroleum": "石油",
    "natural gas": "天然气",
    "renewable energy": "可再生能源",
    "clean energy": "清洁能源",
    "solar": "太阳能",
    "wind power": "风电",
    "nuclear": "核能",
    "electricity": "电力",
    "power generation": "发电",
    "heating": "供暖",
    # 金融
    "banking": "银行",
    "bank": "银行",
    "finance": "金融",
    "financial": "金融",
    "insurance": "保险",
    "stock market": "股票市场",
    "capital market": "资本市场",
    "fintech": "金融科技",
    "digital finance": "数字金融",
    # 农业
    "agriculture": "农业",
    "agricultural": "农业",
    "farming": "农业",
    "grain": "粮食",
    "crop": "农作物",
    "livestock": "畜牧业",
    "fishery": "渔业",
    "food": "食品",
    # 服务业
    "retail": "零售",
    "e-commerce": "电子商务",
    "tourism": "旅游",
    "hospitality": "酒店",
    "healthcare": "医疗健康",
    "health care": "医疗健康",
    "hospital": "医院",
    "education": "教育",
    "university": "高等教育",
    "real estate": "房地产",
    "housing": "房地产",
    "property": "房地产",
    "logistics": "物流",
    "transportation": "交通运输",
    "telecom": "电信",
    # 科技
    "technology": "科技",
    "internet": "互联网",
    "digital economy": "数字经济",
    "artificial intelligence": "人工智能",
    "robot": "机器人",
    "automation": "自动化",
    "smart city": "智慧城市",
    "big data": "大数据",
    "cloud computing": "云计算",
    "blockchain": "区块链",
    # 资源与环境
    "mining": "采矿",
    "mineral": "矿产",
    "natural resource": "自然资源",
    "environment": "环境",
    "pollution": "污染治理",
    "carbon": "碳排放",
    "climate": "气候",
    # 贸易与供应链
    "trade": "贸易",
    "export": "出口",
    "import": "进口",
    "supply chain": "供应链",
    "global value chain": "全球价值链",
    "gvc": "全球价值链",
    "fdi": "外商直接投资",
    # 劳动力市场
    "labor market": "劳动力市场",
    "employment": "就业",
    "unemployment": "失业",
    "wage": "工资",
    "human capital": "人力资本",
    "migration": "劳动力迁移",
}

# 研究方法关键词映射
METHOD_KEYWORDS = {
    # 因果推断
    "difference-in-differences": "DID (双重差分)",
    "difference in differences": "DID (双重差分)",
    "diff-in-diff": "DID (双重差分)",
    "did": "DID (双重差分)",
    "regression discontinuity": "RDD (断点回归)",
    "rd design": "RDD (断点回归)",
    "rdd": "RDD (断点回归)",
    "instrumental variable": "IV (工具变量)",
    "iv estimation": "IV (工具变量)",
    "2sls": "2SLS (两阶段最小二乘)",
    "two-stage least squares": "2SLS (两阶段最小二乘)",
    "propensity score matching": "PSM (倾向得分匹配)",
    "psm": "PSM (倾向得分匹配)",
    "synthetic control": "SCM (合成控制法)",
    "event study": "事件研究法",
    # 面板数据
    "panel data": "面板数据模型",
    "fixed effect": "固定效应模型",
    "random effect": "随机效应模型",
    "gmm": "GMM (广义矩估计)",
    "generalized method of moments": "GMM (广义矩估计)",
    "dynamic panel": "动态面板模型",
    # 时间序列
    "time series": "时间序列分析",
    "var model": "VAR (向量自回归)",
    " var ": "VAR (向量自回归)",
    "vector autoregression": "VAR (向量自回归)",
    "cointegration": "协整分析",
    "granger causality": "格兰杰因果检验",
    "arima": "ARIMA",
    "garch": "GARCH",
    # 截面数据
    "ols": "OLS (最小二乘)",
    "ordinary least squares": "OLS (最小二乘)",
    "logit": "Logit 模型",
    "probit": "Probit 模型",
    "tobit": "Tobit 模型",
    "quantile regression": "分位数回归",
    "heckman": "Heckman 选择模型",
    # 机器学习
    "machine learning": "机器学习",
    "deep learning": "深度学习",
    "neural network": "神经网络",
    "random forest": "随机森林",
    "gradient boosting": "梯度提升",
    "xgboost": "XGBoost",
    "lasso": "LASSO 回归",
    "ridge regression": "岭回归",
    "svm": "SVM (支持向量机)",
    "support vector": "SVM (支持向量机)",
    "clustering": "聚类分析",
    "k-means": "K-means 聚类",
    "double machine learning": "DML (双重机器学习)",
    "causal forest": "因果森林",
    # 大语言模型
    "llm": "LLM (大语言模型)",
    "large language model": "LLM (大语言模型)",
    "gpt": "GPT",
    "bert": "BERT",
    "transformer": "Transformer",
    "nlp": "NLP (自然语言处理)",
    "natural language processing": "NLP (自然语言处理)",
    "text analysis": "文本分析",
    "sentiment analysis": "情感分析",
    # 结构模型
    "structural model": "结构模型",
    "dsge": "DSGE (动态随机一般均衡)",
    "cge": "CGE (可计算一般均衡)",
    "computable general equilibrium": "CGE (可计算一般均衡)",
    "search and matching": "搜寻匹配模型",
    # 空间计量
    "spatial econometrics": "空间计量",
    "spatial regression": "空间回归",
    "geographically weighted": "地理加权回归",
    # 实验方法
    "randomized controlled trial": "RCT (随机对照实验)",
    "rct": "RCT (随机对照实验)",
    "field experiment": "田野实验",
    "lab experiment": "实验室实验",
    "natural experiment": "自然实验",
    "quasi-experiment": "准实验",
    "auction experiment": "拍卖实验",
    # 其他方法
    "meta-analysis": "元分析",
    "survey": "问卷调查",
    "case study": "案例研究",
    "gravity model": "引力模型",
    "stochastic frontier": "随机前沿分析",
    "dea": "DEA (数据包络分析)",
    "data envelopment analysis": "DEA (数据包络分析)",
    "mediation analysis": "中介效应分析",
    "mediating effect": "中介效应分析",
    "moderation analysis": "调节效应分析",
    "heterogeneity analysis": "异质性分析",
}


def extract_industry(text: str, keywords: List[str]) -> List[str]:
    """从论文中提取研究的行业领域"""
    industries = {}
    combined_text = (text + " " + " ".join(keywords)).lower()
    
    for pattern, industry in INDUSTRY_KEYWORDS.items():
        if pattern in combined_text:
            # 计算出现次数作为权重
            count = combined_text.count(pattern)
            if industry not in industries:
                industries[industry] = 0
            industries[industry] += count
    
    # 按权重排序，返回前5个
    sorted_industries = sorted(industries.items(), key=lambda x: -x[1])
    return [ind for ind, _ in sorted_industries[:5]]


def extract_methodology(text: str, keywords: List[str]) -> List[str]:
    """从论文中提取使用的研究方法/模型"""
    methods = {}
    combined_text = (text + " " + " ".join(keywords)).lower()
    
    for pattern, method in METHOD_KEYWORDS.items():
        if pattern in combined_text:
            # 计算出现次数作为权重
            count = combined_text.count(pattern)
            if method not in methods:
                methods[method] = 0
            methods[method] += count
    
    # 按权重排序，返回前5个
    sorted_methods = sorted(methods.items(), key=lambda x: -x[1])
    return [m for m, _ in sorted_methods[:5]]


@dataclass
class PaperAnalysis:
    """论文分析结果"""
    title: str
    keywords: List[str]
    jel_codes: List[Dict[str, str]]
    abstract: str
    confidence_scores: Dict[str, float]
    industries: List[str] = None  # 行业领域
    methods: List[str] = None     # 研究方法
    

def extract_text_from_pdf(pdf_path: str) -> str:
    """从 PDF 提取文本"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        # 尝试使用 pdfplumber
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except ImportError:
            print("请安装 PyMuPDF 或 pdfplumber: pip install pymupdf pdfplumber")
            sys.exit(1)


def extract_keywords(text: str) -> List[str]:
    """从论文文本中提取关键词"""
    keywords = []
    
    # 方法1: 查找 Keywords 部分（支持多行关键词）
    patterns = [
        # 匹配 Keywords 到 ABSTRACT 之间的内容
        r"Keywords?[:\s]*(.+?)(?:A\s*B\s*S\s*T\s*R\s*A\s*C\s*T|ABSTRACT|\d+\.\s*Introduction)",
        # 匹配单行关键词
        r"Keywords?[:\s]+([^\n]+(?:\n(?![A-Z\d])[^\n]+)*)",
        r"Key\s*words?[:\s]+([^\n]+(?:\n(?![A-Z\d])[^\n]+)*)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            # 清理并分割关键词（支持换行、分号、逗号分隔）
            kws = re.split(r'[;,\n]', match)
            for kw in kws:
                kw = kw.strip()
                # 过滤掉太长或太短的，以及非关键词内容
                if 2 <= len(kw) <= 60:
                    # 跳过 JEL 代码、数字开头等
                    if not re.match(r'^(JEL|[A-Z]\d|[\d\.])', kw):
                        keywords.append(kw)
        
        # 如果找到了关键词就不继续尝试其他模式
        if keywords:
            break
    
    # 去重但保持顺序
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)
    
    return unique_keywords


def extract_title(text: str) -> str:
    """提取论文标题"""
    lines = text.split('\n')
    for line in lines[:20]:  # 通常标题在前20行
        line = line.strip()
        if len(line) > 20 and len(line) < 200:
            # 跳过常见的非标题行
            if not any(skip in line.lower() for skip in ['abstract', 'keyword', 'doi', 'http', 'journal', 'received', 'accepted']):
                return line
    return "Unknown Title"


def extract_abstract(text: str) -> str:
    """提取摘要"""
    # 查找 Abstract 部分
    patterns = [
        r"A\s*B\s*S\s*T\s*R\s*A\s*C\s*T\s*(.+?)(?:Keywords?|1\.\s*Introduction|Introduction)",
        r"Abstract[:\s]*(.+?)(?:Keywords?|1\.\s*Introduction|Introduction)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # 清理换行
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract[:2000]  # 限制长度
    
    return ""


def extract_paper_jel_codes(text: str) -> List[str]:
    """从论文中提取作者标注的 JEL 代码"""
    jel_codes = []
    
    # 查找 JEL classification 部分（支持多种格式）
    patterns = [
        r'JEL\s*classification[s]?[:\s]*(.+?)(?:Keywords|Abstract|Introduction|\d+\.\s)',
        r'JEL\s*codes?[:\s]*(.+?)(?:Keywords|Abstract|Introduction|\d+\.\s)',
        r'JEL[:\s]+codes?[:\s]*(.+?)(?:Keywords|Abstract|Introduction|\d+\.\s)',
        r'JEL[:\s]*Classification[:\s]*(.+?)(?:Keywords|Abstract|Introduction|\d+\.\s)',
        r'JEL[:\s]+([A-Z]\d{1,2}(?:[\s\n,;]+[A-Z]\d{1,2})*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            jel_section = match.group(1)
            # 提取所有 JEL 代码格式的字符串
            codes = re.findall(r'\b([A-Z]\d{1,2})\b', jel_section)
            for code in codes:
                if code[0] in JEL_CODES and code not in jel_codes:
                    jel_codes.append(code)
            if jel_codes:
                break
    
    return jel_codes


def match_jel_codes(keywords: List[str], text: str = "") -> List[Dict[str, str]]:
    """根据关键词匹配 JEL 代码，优先使用论文自带的 JEL 代码"""
    matched_codes = {}
    
    # 首先尝试提取论文中标注的 JEL 代码
    paper_jel_codes = extract_paper_jel_codes(text)
    for code in paper_jel_codes:
        matched_codes[code] = 10  # 论文自带的权重最高
    
    # 合并所有文本用于匹配
    all_text = " ".join(keywords).lower() + " " + text.lower()
    
    # 基于关键词映射
    for keyword_pattern, jel_list in KEYWORD_JEL_MAPPING.items():
        if keyword_pattern in all_text:
            for jel in jel_list:
                if jel not in matched_codes:
                    matched_codes[jel] = 0
                matched_codes[jel] += 1
    
    # 排序并返回
    sorted_codes = sorted(matched_codes.items(), key=lambda x: -x[1])
    
    results = []
    for code, score in sorted_codes[:10]:  # 最多返回10个
        main_cat = code[0]
        if main_cat in JEL_CODES:
            cat_info = JEL_CODES[main_cat]
            subcode_desc = cat_info["subcodes"].get(code, cat_info["name"])
            # 标注来源
            is_from_paper = code in paper_jel_codes
            results.append({
                "code": code,
                "category": cat_info["name"],
                "description": subcode_desc,
                "confidence": 1.0 if is_from_paper else min(score / 5, 0.8),
                "source": "paper" if is_from_paper else "inferred",
            })
    
    return results


def analyze_paper(pdf_path: str, use_llm: bool = False) -> PaperAnalysis:
    """分析论文"""
    print(f"正在分析: {pdf_path}")
    
    # 提取文本
    text = extract_text_from_pdf(pdf_path)
    
    # 提取各部分
    title = extract_title(text)
    keywords = extract_keywords(text)
    abstract = extract_abstract(text)
    
    # 匹配 JEL 代码（传入完整文本以便提取论文标注的 JEL）
    jel_codes = match_jel_codes(keywords, text)
    
    # 计算置信度
    confidence_scores = {item["code"]: item["confidence"] for item in jel_codes}
    
    # 提取行业领域和研究方法
    industries = extract_industry(text, keywords)
    methods = extract_methodology(text, keywords)
    
    return PaperAnalysis(
        title=title,
        keywords=keywords,
        jel_codes=jel_codes,
        abstract=abstract[:500] + "..." if len(abstract) > 500 else abstract,
        confidence_scores=confidence_scores,
        industries=industries,
        methods=methods,
    )


def format_output(analysis: PaperAnalysis) -> str:
    """格式化输出"""
    output = []
    output.append("=" * 60)
    output.append("论文分析结果")
    output.append("=" * 60)
    
    output.append(f"\n📄 标题: {analysis.title}")
    
    output.append(f"\n🔑 关键词 ({len(analysis.keywords)}):")
    for kw in analysis.keywords:
        output.append(f"   • {kw}")
    
    output.append(f"\n📊 JEL 分类代码 ({len(analysis.jel_codes)}):")
    for item in analysis.jel_codes:
        conf = item['confidence']
        bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
        source_tag = "📄" if item.get('source') == 'paper' else "🔍"
        output.append(f"   {source_tag} [{item['code']}] {item['description']}")
        output.append(f"         置信度: {bar} {conf:.0%}")
    
    # 显示行业领域
    if analysis.industries:
        output.append(f"\n🏭 行业领域 ({len(analysis.industries)}):")
        for ind in analysis.industries:
            output.append(f"   • {ind}")
    
    # 显示研究方法
    if analysis.methods:
        output.append(f"\n🔬 研究方法 ({len(analysis.methods)}):")
        for method in analysis.methods:
            output.append(f"   • {method}")
    
    output.append("\n📄 = 论文标注  🔍 = 推断")
    output.append("\n" + "=" * 60)
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="论文关键词提取与 JEL 分类")
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")
    parser.add_argument("--llm", action="store_true", help="使用 LLM 进行更精准的分类")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    # 检查文件
    if not Path(args.pdf).exists():
        print(f"错误: 文件不存在 - {args.pdf}")
        sys.exit(1)
    
    # 分析论文
    analysis = analyze_paper(args.pdf, use_llm=args.llm)
    
    # 输出结果
    if args.json or args.output:
        result = asdict(analysis)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"结果已保存到: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_output(analysis))


if __name__ == "__main__":
    main()
