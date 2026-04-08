from flask import Flask, render_template, request, jsonify, send_file
import requests
import json
import os
import io
import re
import datetime
import PyPDF2
import docx

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max

API_CONFIGS = {
    "grok": {"url": "https://api.x.ai/v1/chat/completions", "model": "grok-3-latest", "name": "Grok (xAI)"},
    "deepseek": {"url": "https://api.deepseek.com/chat/completions", "model": "deepseek-chat", "name": "DeepSeek V3"},
    "qwen": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "model": "qwen-long", "name": "Qwen-Long (阿里)"},
    "kimi": {"url": "https://api.moonshot.cn/v1/chat/completions", "model": "moonshot-v1-32k", "name": "Kimi (月之暗面)"}
}

SINGLE_PROMPT = """你是一个严格的分析助手，帮助用户独立判断文章内容，辅助个人决策。

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
  "information_gaps": ["信息缺口1", "信息缺口2（最多2条）"],
  "conclusion": "综合判断结论（2-3句话，直接给倾向性结论）",
  "confidence": "高/中/低",
  "confidence_reason": "置信度理由（1句话）"
}}

只输出JSON，不要任何开场白。

文章摘要列表：
{summaries}"""


def call_api(api_key, provider, messages):
    config = API_CONFIGS.get(provider, API_CONFIGS["grok"])
    resp = requests.post(
        config["url"],
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json={"model": config["model"], "messages": messages, "max_tokens": 1000, "temperature": 0.3},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def extract_pdf(file_bytes):
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return "".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_docx(file_bytes):
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def fetch_url(url):
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()[:8000]


def do_analyze(content, source, api_key, provider):
    content = content[:6000]
    raw = call_api(api_key, provider, [{"role": "user", "content": SINGLE_PROMPT.format(content=content)}])
    result = parse_json(raw)
    result["source"] = source
    result["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    result["provider"] = API_CONFIGS[provider]["name"]
    return result


@app.route("/")
def index():
    return render_template("index.html", api_configs=API_CONFIGS)


@app.route("/analyze", methods=["POST"])
def analyze():
    api_key = request.form.get("api_key", "").strip()
    provider = request.form.get("provider", "grok")
    if not api_key:
        return jsonify({"error": "请填写API Key"}), 400

    input_type = request.form.get("input_type", "text")
    if input_type == "url":
        url = request.form.get("url", "").strip()
        if not url:
            return jsonify({"error": "请输入URL"}), 400
        try:
            content = fetch_url(url)
        except Exception as e:
            return jsonify({"error": f"无法抓取网页：{e}"}), 400
        source = url
    else:
        content = request.form.get("text", "").strip()
        source = request.form.get("source_name", "手动粘贴").strip() or "手动粘贴"

    if len(content) < 50:
        return jsonify({"error": "内容太短或为空"}), 400
    try:
        return jsonify({"success": True, "result": do_analyze(content, source, api_key, provider)})
    except json.JSONDecodeError:
        return jsonify({"error": "AI返回格式异常，请重试"}), 500
    except requests.HTTPError as e:
        return jsonify({"error": f"API调用失败：{e.response.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze_file", methods=["POST"])
def analyze_file():
    """批量上传时每个文件单独调用此接口"""
    api_key = request.form.get("api_key", "").strip()
    provider = request.form.get("provider", "grok")
    if not api_key:
        return jsonify({"error": "请填写API Key"}), 400

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未收到文件"}), 400

    fname = file.filename
    raw = file.read()
    try:
        if fname.lower().endswith(".pdf"):
            content = extract_pdf(raw)
        elif fname.lower().endswith((".docx", ".doc")):
            content = extract_docx(raw)
        elif fname.lower().endswith(".txt"):
            content = raw.decode("utf-8", errors="ignore")
        else:
            return jsonify({"error": f"{fname}：不支持的格式"}), 400
    except Exception as e:
        return jsonify({"error": f"{fname} 解析失败：{e}"}), 400

    if len(content) < 50:
        return jsonify({"error": f"{fname}：内容太短或无法提取文字"}), 400
    try:
        return jsonify({"success": True, "result": do_analyze(content, fname, api_key, provider)})
    except json.JSONDecodeError:
        return jsonify({"error": f"{fname}：AI返回格式异常"}), 500
    except requests.HTTPError as e:
        return jsonify({"error": f"{fname}：API失败 {e.response.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": f"{fname}：{e}"}), 500


@app.route("/compare", methods=["POST"])
def compare():
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
        raw = call_api(api_key, provider, [{"role": "user", "content": COMPARE_PROMPT.format(summaries=summary_text)}])
        result = parse_json(raw)
        result["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": f"对比分析失败：{e}"}), 500


@app.route("/export", methods=["POST"])
def export():
    data = request.json
    topic = data.get("topic", "未命名话题")
    articles = data.get("articles", [])
    comparison = data.get("comparison", None)

    lines = [f"文章分析报告", f"话题：{topic}",
              f"生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", "=" * 60, ""]

    for i, a in enumerate(articles, 1):
        lines += [f"【文章 {i}】{a.get('source', '')}",
                  f"时间：{a.get('timestamp','')}  模型：{a.get('provider','')}",
                  "", f"核心论点：{a.get('core_claim','')}", "",
                  "主要证据："] + [f"  • {e}" for e in a.get('evidence', [])]
        lines += ["", f"作者立场：{a.get('author_intent','')}",
                  f"最大漏洞：{a.get('biggest_flaw','')}",
                  f"需核实：{'; '.join(a.get('verify_these',[]))}",
                  f"可信度：{a.get('credibility','')} — {a.get('credibility_reason','')}",
                  "", "-" * 60, ""]

    if comparison:
        gaps = comparison.get('information_gaps', [])
        gap_str = '; '.join(gaps) if isinstance(gaps, list) else str(gaps)
        lines += ["【综合对比分析】", "",
                  f"共识观点：{comparison.get('consensus','')}", "",
                  f"矛盾之处：{comparison.get('contradictions','')}", "",
                  f"最强证据链：{comparison.get('strongest_evidence','')}", "",
                  f"信息缺口：{gap_str}", "",
                  f"综合结论：{comparison.get('conclusion','')}",
                  f"置信度：{comparison.get('confidence','')} — {comparison.get('confidence_reason','')}"]

    output = "\n".join(lines)
    buf = io.BytesIO(output.encode("utf-8"))
    buf.seek(0)
    safe = re.sub(r'[^\w\u4e00-\u9fff]', '_', topic)[:20]
    fname = f"{safe}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    return send_file(buf, as_attachment=True, download_name=fname, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
