# ArticleLens — 文章分析工具

批量分析 PDF 论文、微信文章、网页，辅助个人决策判断。

## 功能
- 上传 PDF / Word / TXT 文件分析
- 粘贴网页 URL 自动抓取
- 粘贴正文（适合微信文章）
- 多篇横向对比，生成综合结论
- 导出文字报告
- 支持切换 Grok / DeepSeek / Qwen / Kimi

## 本地运行

```bash
pip install -r requirements.txt
python app.py
```
然后打开 http://localhost:5000

## 部署到 Render（免费，手机也能访问）

### 第一步：注册 GitHub
1. 打开 https://github.com
2. 点击右上角 Sign up，注册账号

### 第二步：创建仓库，上传代码
1. 登录 GitHub 后，点击右上角 "+" → "New repository"
2. 仓库名填：article-analyzer
3. 选 Public，点 Create repository
4. 点页面上的 "uploading an existing file"
5. 把本工具所有文件（app.py / templates/ / requirements.txt / render.yaml）拖进去
6. 点 Commit changes

### 第三步：部署到 Render
1. 打开 https://render.com，点 Get Started for Free
2. 用 GitHub 账号登录
3. 点 New → Web Service
4. 选择你的 article-analyzer 仓库
5. 配置如下：
   - Name: article-analyzer（随意）
   - Environment: Python
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
   - Plan: Free
6. 点 Create Web Service
7. 等待 2-5 分钟部署完成
8. Render 会给你一个网址，如 https://article-analyzer-xxxx.onrender.com
9. 这个网址就是你的工具，电脑和手机都能访问

## 使用方法
1. 打开网址
2. 选择 AI 模型（先选 Grok）
3. 填入你的 API Key（仅本次会话使用，不保存）
4. 上传文件 / 粘贴链接 / 粘贴正文
5. 点「分析这篇」
6. 重复 4-5 步，分析多篇
7. 点「综合对比」生成横向分析
8. 点「导出报告」保存结果

## API Key 获取
- Grok: https://console.x.ai
- DeepSeek: https://platform.deepseek.com
- Qwen: https://dashscope.aliyun.com
- Kimi: https://platform.moonshot.cn
