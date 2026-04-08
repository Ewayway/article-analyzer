# ArticleLens 文章分析工具

**🔗 在线体验：https://article-analyzer-peway.onrender.com

打开即用，不需要安装任何软件（需自备 AI API Key）。

---

## 解决什么问题？

用 AI 分析文章时，几乎所有人都遇到过这些痛点：

- 粘贴几篇文章后对话窗口就满了
- 每篇要单独粘贴、单独问，效率极低  
- 不同话题的文章混在一起难以管理
- 读了很多，却没有结构化的结论

ArticleLens 专门解决这些问题。

---

## 功能

- 📄 批量上传 PDF / Word / TXT，最多10个文件同时处理，有进度条
- 🔗 粘贴网页链接自动抓取正文
- ✏️ 直接粘贴文字（适合微信文章）
- 🗂️ 话题管理：不同主题完全隔离，结果自动保存
- 🔍 多篇横向对比，自动生成共识、矛盾、综合结论
- 💾 导出分析报告为文本文件
- 🔄 支持一键切换 Grok / DeepSeek / Qwen / Kimi
- 🔒 完全本地部署，API Key 不保存、不上传

---

## 适合谁用？

- 需要大量阅读文献的研究者和学生
- 追踪某个领域动态的从业者
- 希望独立判断、不被单一信源带偏的读者
- 觉得"读了很多文章但记不住结论"的人

---

## 在线体验

**直接访问：https://article-analyzer-peway.onrender.com **

填入自己的 API Key 即可使用。推荐先用 DeepSeek，费用极低。

---

## 自己部署（完全免费）

**需要准备**
- GitHub 账号（免费）
- Render 账号（免费）
- 任意一个 API Key：Grok / DeepSeek / Qwen / Kimi

**步骤**
1. 点右上角 **Fork** 这个仓库
2. 在 [Render](https://render.com) 新建 Web Service，连接 Fork 后的仓库
3. Build Command：`pip install -r requirements.txt`
4. Start Command：`gunicorn app:app --bind 0.0.0.0:$PORT`
5. 部署完成，打开网址，填入 API Key 开始使用

---

## API Key 获取

| 模型 | 获取地址 | 推荐场景 |
|---|---|---|
| DeepSeek | https://platform.deepseek.com | 性价比最高，首选 |
| Qwen | https://dashscope.aliyun.com | 超长PDF文档 |
| Kimi | https://platform.moonshot.cn | 中文内容 |
| Grok | https://console.x.ai | 英文文章 |

---

## 版权声明 / License

Copyright © 2026 Ewayway. All rights reserved.

本项目基于 [MIT License](LICENSE) 开源。

使用本项目代码时，须保留原作者署名及本版权声明。
欢迎 Fork、学习、改进，但请勿直接商用而不注明来源。

如需商业合作或授权，欢迎通过 GitHub Issues 联系。

---

This project is licensed under the MIT License.  
Attribution required. Commercial use without credit is discouraged.  
For commercial licensing, please open a GitHub Issue.
