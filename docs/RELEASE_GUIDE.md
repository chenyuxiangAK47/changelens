# GitHub Release 创建指南

本指南将帮助你创建 ChangeLens v0.1.0 的 GitHub Release。

## 前置准备

所有发布资源已准备就绪：
- ✅ `release-assets/changelens-demo-results-v0.1.0.zip` (2.91 MB)
- ✅ `docs/changelens-onepager.md` (Markdown 格式)

## 步骤 1: 创建 GitHub Release

1. 访问 GitHub Releases 页面：
   ```
   https://github.com/chenyuxiangAK47/changelens/releases/new
   ```

2. 填写 Release 信息：
   - **Tag version**: `v0.1.0`
   - **Release title**: `ChangeLens v0.1.0 - Research Artifact`
   - **Description** (复制以下内容):

   ```markdown
   # ChangeLens v0.1.0

   ## 🎯 Research Artifact for PhD/RA Applications

   ChangeLens is a reproducible microservice benchmark comparing Blue-Green vs. Canary deployment strategies with automated rollback mechanisms and ML-enhanced early warning.

   ## 📦 What's Included

   - **Demo Results** (`changelens-demo-results-v0.1.0.zip`): Complete experiment outputs including:
     - Aggregated statistical results (mean, std, 95% CI, effect size)
     - Per-run metrics (CSV, JSON, charts)
     - Summary report with key findings
   - **One-Pager** (`changelens-onepager.md`): Research summary template (convert to PDF if needed)

   ## 🔬 Key Research Findings

   - **Canary deployment** achieves **3x lower error rate** (0.02% vs 0.06%) compared to Blue-Green
   - **ML early warning**: XGBoost achieves **33% early detection rate** with **0% false positive rate** (ROC-AUC 0.75)
   - **Error rate** shows larger effect size (Cohen's d = 2.35) than P99 latency

   ## 🚀 Quick Start

   ```powershell
   # Setup
   .\scripts\setup_venv.ps1
   .\venv\Scripts\Activate.ps1
   docker compose up -d

   # Run experiments
   .\scripts\run_research_suite.ps1 -NRuns 10
   ```

   ## 📊 Demo Results

   See `results/demo/` in the repository for sample outputs without running experiments.

   ## 📄 Citation

   If you use ChangeLens in your research, please cite:
   ```
   @software{changelens2024,
     title = {ChangeLens: A Cloud-Native Microservice Benchmark},
     author = {[Your Name]},
     year = {2024},
     url = {https://github.com/chenyuxiangAK47/changelens}
   }
   ```

   ## 📝 License

   MIT License - See LICENSE file for details.
   ```

3. 上传附件：
   - 点击 "Attach binaries by dropping them here or selecting them"
   - 选择 `release-assets/changelens-demo-results-v0.1.0.zip`

4. 选择发布类型：
   - ✅ **Set as the latest release** (推荐)
   - 或者选择 "Set as a pre-release" (如果是测试版)

5. 点击 **"Publish release"**

## 步骤 2: 可选 - 转换 One-Pager 为 PDF

如果你有 `pandoc` 安装：

```powershell
cd D:\ChangeLens
pandoc docs/changelens-onepager.md -o release-assets/changelens-onepager.pdf
```

然后将 PDF 也上传到 Release。

如果没有 `pandoc`，可以使用在线工具：
- https://www.markdowntopdf.com/
- https://dillinger.io/ (导出为 PDF)

或者直接使用 Markdown 文件（GitHub 会自动渲染）。

## 步骤 3: 验证

发布后，检查：
- ✅ Release 页面可以正常访问
- ✅ ZIP 文件可以下载
- ✅ 描述格式正确显示
- ✅ Tag `v0.1.0` 已创建

## 完成！

你的 GitHub Release 已创建。现在可以：
- 在简历/申请材料中引用 Release URL
- 在套磁邮件中附上 Release 链接
- 在论文/报告中引用 Release

---

**Release URL 格式**:
```
https://github.com/chenyuxiangAK47/changelens/releases/tag/v0.1.0
```
