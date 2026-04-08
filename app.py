from flask import Flask, render_template, request, jsonify, send_file
import requests
import json
import os
import io
import datetime
from urllib.parse import urlparse
import PyPDF2
import docx

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# ─────────────────────────────────────────
#  API 配置（支持切换）
# ─────────────────────────────────────────
API_CONFIGS = {
    "grok": {
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3-latest",
        "name": "Grok (xAI)"
    },
    "deepseek": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "name": "DeepSeek V3"
    },
    "qwen": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-long",
        "name": "Qwen-Long (阿里)"
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "model": "moonshot-v1-32k",
        "name": "Kimi (月之暗面)"
    }
}

# ─────────────────────────────────────────
#  分析提示词（中英文通用）
# ─────────────────────────────────────────
SINGLE_ARTICLE_PROMPT = """你是一个严格的分析助手，帮助用户独立判断文章内容，辅助个人决策。

请分析以下文章，输出格式严格按照下面的JSON结构，不得增减字段：

{{
  "core_claim": "核心论点（1句话，不超过40字）",
  "evidence": ["最硬的证据或数据1（不超过25字）", "证据2", "证据3（最多3条）"],
  "author_intent": "文章想让读者相信什么（1句话，识别立场倾向）",
  "biggest_flaw": "最值得怀疑的地方（1-2句话）",
  "verify_these": ["需要核实的问题1", "需要核实的问题2（最多2条）"],
  "credibility": "高/中/低",
  "credibility_reason": "可信度评估理由（1句话）",
  "language": "zh/en"
}}

只输出JSON，不要任何开场白或解释。

文章内容：
{content}"""

COMPARE_PROMPT = """你是一个帮助用户做决策的分析助手。

以下是用户对多篇文章的分析摘要。请做横向综合分析，输出严格按照以下JSON格式：

{{
  "consensus": "这些文章相互印证的核心观点（1-2句话，若无则写'无明显共识'）",
  "contradictions": "相互矛盾的地方（1-2句话，若无则写'无明显矛盾'）",
  "strongest_evidence": "目前证据最强的观点是什么（1-2句话）",
  "information_gaps": "还缺什么信息才能做出更可靠判断（1-2条）",
  "conclusion": "综合判断结论（2-3句话，直接给倾向性结论）",
  "confidence": "高/中/低",
  "confidence_reason": "置信度理由（1句话）"
}}

只输出JSON，不要任何开场白。

文章摘要列表：
{summaries}"""


def call_api(api_key, provider, messages):
    """调用指定的AI API"""
    config = API_CONFIGS.get(provider, API_CONFIGS["grok"])
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": config["model"],
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.3
    }
    resp = requests.post(config["url"], headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_pdf_text(file_bytes):
    """从PDF提取文字"""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()


def extract_docx_text(file_bytes):
    """从Word文档提取文字"""
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs]).strip()


def fetch_url_content(url):
    """抓取网页正文"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    # 简单提取：去掉HTML标签
    import re
    text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:8000]  # 限制长度


# ─────────────────────────────────────────
#  路由
# ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", api_configs=API_CONFIGS)


@app.route("/analyze", methods=["POST"])
def analyze():
    """分析单篇文章"""
    api_key = request.form.get("api_key", "").strip()
    provider = request.form.get("provider", "grok")

    if not api_key:
        return jsonify({"error": "请填写API Key"}), 400

    content = ""
    source_name = ""

    # 判断输入类型
    input_type = request.form.get("input_type", "text")

    if input_type == "file":
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "未收到文件"}), 400
        source_name = file.filename
        file_bytes = file.read()
        if file.filename.lower().endswith(".pdf"):
            content = extract_pdf_text(file_bytes)
        elif file.filename.lower().endswith((".docx", ".doc")):
            content = extract_docx_text(file_bytes)
        elif file.filename.lower().endswith(".txt"):
            content = file_bytes.decode("utf-8", errors="ignore")
        else:
            return jsonify({"error": "支持格式：PDF、Word、TXT"}), 400

    elif input_type == "url":
        url = request.form.get("url", "").strip()
        if not url:
            return jsonify({"error": "请输入URL"}), 400
        source_name = url
        try:
            content = fetch_url_content(url)
        except Exception as e:
            return jsonify({"error": f"无法抓取网页：{str(e)}"}), 400

    else:  # text
        content = request.form.get("text", "").strip()
        source_name = request.form.get("source_name", "手动粘贴").strip() or "手动粘贴"

    if not content or len(content) < 50:
        return jsonify({"error": "文章内容太短或为空"}), 400

    # 截断超长文章（节省token）
    content = content[:6000]

    try:
        prompt = SINGLE_ARTICLE_PROMPT.format(content=content)
        result_text = call_api(api_key, provider, [
            {"role": "user", "content": prompt}
        ])

        # 解析JSON
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text)
        result["source"] = source_name
        result["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        result["provider"] = API_CONFIGS[provider]["name"]
        return jsonify({"success": True, "result": result})

    except json.JSONDecodeError:
        return jsonify({"error": "AI返回格式异常，请重试", "raw": result_text}), 500
    except requests.HTTPError as e:
        return jsonify({"error": f"API调用失败：{e.response.status_code} - 请检查API Key"}), 500
    except Exception as e:
        return jsonify({"error": f"错误：{str(e)}"}), 500


@app.route("/compare", methods=["POST"])
def compare():
    """横向对比多篇摘要"""
    data = request.json
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "grok")
    summaries = data.get("summaries", [])

    if not api_key:
        return jsonify({"error": "请填写API Key"}), 400
    if len(summaries) < 2:
        return jsonify({"error": "至少需要2篇文章才能对比"}), 400

    summary_text = ""
    for i, s in enumerate(summaries, 1):
        summary_text += f"\n【文章{i}】来源：{s.get('source','未知')}\n"
        summary_text += f"核心论点：{s.get('core_claim','')}\n"
        summary_text += f"主要证据：{'; '.join(s.get('evidence',[]))}\n"
        summary_text += f"作者立场：{s.get('author_intent','')}\n"
        summary_text += f"最大漏洞：{s.get('biggest_flaw','')}\n"
        summary_text += f"可信度：{s.get('credibility','')}\n"

    try:
        prompt = COMPARE_PROMPT.format(summaries=summary_text)
        result_text = call_api(api_key, provider, [
            {"role": "user", "content": prompt}
        ])
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text)
        result["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": f"对比分析失败：{str(e)}"}), 500


@app.route("/export", methods=["POST"])
def export():
    """导出分析结果为文本"""
    data = request.json
    articles = data.get("articles", [])
    comparison = data.get("comparison", None)

    output = f"文章分析报告\n生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    output += "=" * 60 + "\n\n"

    for i, a in enumerate(articles, 1):
        output += f"【文章 {i}】{a.get('source', '')}\n"
        output += f"分析时间：{a.get('timestamp', '')}\n"
        output += f"使用模型：{a.get('provider', '')}\n\n"
        output += f"核心论点：{a.get('core_claim', '')}\n\n"
        output += f"主要证据：\n"
        for ev in a.get('evidence', []):
            output += f"  • {ev}\n"
        output += f"\n作者立场：{a.get('author_intent', '')}\n"
        output += f"最大漏洞：{a.get('biggest_flaw', '')}\n"
        output += f"需核实：{'; '.join(a.get('verify_these', []))}\n"
        output += f"可信度：{a.get('credibility', '')} — {a.get('credibility_reason', '')}\n"
        output += "\n" + "-" * 60 + "\n\n"

    if comparison:
        output += "【综合对比分析】\n\n"
        output += f"共识观点：{comparison.get('consensus', '')}\n\n"
        output += f"矛盾之处：{comparison.get('contradictions', '')}\n\n"
        output += f"最强证据链：{comparison.get('strongest_evidence', '')}\n\n"
        output += f"信息缺口：{'; '.join(comparison.get('information_gaps', []))}\n\n"
        output += f"综合结论：{comparison.get('conclusion', '')}\n"
        output += f"置信度：{comparison.get('confidence', '')} — {comparison.get('confidence_reason', '')}\n"

    buf = io.BytesIO(output.encode("utf-8"))
    buf.seek(0)
    filename = f"analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
