# Streamlit Cloud + GitHub 完整部署指南

本文档介绍如何将 Streamlit 应用部署到 Streamlit Cloud，并通过 GitHub 进行版本管理。

---

## 目录

1. [前置条件](#前置条件)
2. [GitHub 配置](#github-配置)
3. [项目准备](#项目准备)
4. [部署到 Streamlit Cloud](#部署到-streamlit-cloud)
5. [常见问题及解决方案](#常见问题及解决方案)
6. [更新部署](#更新部署)

---

## 前置条件

- Python 3.8+
- Git 已安装
- 拥有 GitHub 账号
- 拥有 Streamlit Cloud 账号（使用 GitHub 账号登录）

---

## GitHub 配置

### 1. 生成 SSH 密钥

在命令行中执行：

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519 -N ""

# 查看公钥内容
cat ~/.ssh/id_ed25519.pub
```

### 2. 添加公钥到 GitHub

1. 打开 https://github.com/settings/keys
2. 点击 **"New SSH key"**
3. 标题：例如 `Streamlit Deploy Key`
4. 粘贴刚才生成的公钥内容
5. 点击 **"Add SSH key"**

### 3. 测试连接

```bash
ssh -T git@github.com
```

看到 `Hi username! You've successfully authenticated` 表示成功。

---

## 项目准备

### 1. 项目结构

确保项目结构如下：

```
your-project/
├── CQI_ZTE/                          # 应用代码目录
│   ├── cqi_streamlit_对比版zte.py    # 主应用文件
│   ├── CQI关联指标_中兴.xlsx         # 数据文件（如需）
│   └── requirements.txt              # ⚠️ 必需！依赖文件
├── README.md
└── .gitignore
```

### 2. 创建 requirements.txt

在**应用所在目录**创建 `requirements.txt`：

```txt
streamlit
pandas
numpy
scipy
plotly
openpyxl
altair
matplotlib
seaborn
scikit-learn
statsmodels
```

> **注意**：
> - 文件必须放在与应用相同的目录下
> - 版本号可选，不指定时 Streamlit Cloud 会自动安装兼容版本

### 3. 修改文件路径为相对路径

**错误示例**（使用绝对路径）：
```python
文件路径 = r"h:\pycode\Self\code880_CQI分析\CQI_ZTE\CQI关联指标_中兴.xlsx"
```

**正确示例**（使用相对路径）：
```python
import os

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
文件路径 = os.path.join(current_dir, "CQI关联指标_中兴.xlsx")
```

### 4. 推送到 GitHub

```bash
# 初始化 Git（如未初始化）
git init

# 添加 GitHub 远程仓库
git remote add origin git@github.com:用户名/仓库名.git

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 推送到 GitHub
git push -u origin main
```

---

## 部署到 Streamlit Cloud

### 1. 登录 Streamlit Cloud

1. 访问 https://share.streamlit.io/
2. 使用 GitHub 账号登录

### 2. 创建新应用

1. 点击 **"New app"**
2. 选择仓库：选择您要部署的 GitHub 仓库
3. **Main file path**：填写应用文件路径，例如：
   ```
   CQI_ZTE/cqi_streamlit_对比版zte.py
   ```
4. 点击 **"Deploy"**

### 3. 等待部署完成

部署过程通常需要 2-5 分钟。成功后您会获得一个类似以下的 URL：

```
https://5gcoizte.streamlit.app/
```

---

## 常见问题及解决方案

### 问题 1：ModuleNotFoundError（缺少依赖）

**错误信息**：
```
ModuleNotFoundError: No module named 'scipy'
```

**原因**：缺少 `requirements.txt` 或依赖未正确声明

**解决方案**：
1. 确保 `requirements.txt` 位于应用相同目录
2. 添加所有必需的依赖包
3. 重新部署

```bash
# 本地测试依赖是否完整
pip install -r requirements.txt
```

---

### 问题 2：文件路径错误

**错误信息**：
```
FileNotFoundError: [Errno 2] No such file or directory: 'h:\pycode\...'
```

**原因**：使用了本地绝对路径

**解决方案**：
修改为相对路径：

```python
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
文件路径 = os.path.join(current_dir, "文件名.xlsx")
```

---

### 问题 3：数据文件未找到

**错误信息**：
```
FileNotFoundError: [Errno 2] No such file: '数据文件.xlsx'
```

**原因**：数据文件未推送到 GitHub

**解决方案**：
1. 确保数据文件已添加到 Git：
   ```bash
   git add CQI_ZTE/数据文件.xlsx
   git commit -m "添加数据文件"
   git push origin main
   ```
2. 重新部署

> **注意**：GitHub 对单个文件大小限制为 100MB。如数据文件过大，考虑：
> - 使用外部存储（如 AWS S3、腾讯云 COS）
> - 使用 Git LFS 管理大文件

---

### 问题 4：部署后界面显示异常

**原因**：可能是缓存或版本问题

**解决方案**：
1. 点击应用右下角 **"Manage app"**
2. 点击 **"Reboot"** 重新部署
3. 如仍有问题，尝试清除浏览器缓存

---

## 更新部署

### 方式 1：自动更新（推荐）

Streamlit Cloud 会自动检测 GitHub 仓库的更改并重新部署。

只需推送代码到 GitHub：

```bash
git add .
git commit -m "更新说明"
git push origin main
```

大约 1-2 分钟后，应用会自动更新。

### 方式 2：手动重启

1. 访问 https://share.streamlit.io/
2. 找到您的应用
3. 点击 **"Manage app"**
4. 点击 **"Reboot"**

---

## 最佳实践

### 1. 分支管理

建议创建 `deploy` 分支专门用于部署：

```bash
# 创建部署分支
git checkout -b deploy

# 推送到 GitHub
git push -u origin deploy

# Streamlit Cloud 中选择 deploy 分支部署
```

### 2. 敏感信息处理

不要在代码中硬编码敏感信息（如密码、API Key）：

```python
# ❌ 错误
API_KEY = "sk-1234567890"

# ✅ 正确 - 使用 Streamlit Secrets
import streamlit as st
API_KEY = st.secrets["api_key"]
```

在 Streamlit Cloud 中设置 Secrets：
1. 点击 **"Manage app"**
2. 点击 **"⋮"** → **"Settings"**
3. 选择 **"Secrets"** 选项卡
4. 添加键值对

### 3. 调试日志

查看部署日志排查问题：
1. 访问应用管理页面
2. 点击 **"Logs"** 查看实时日志

---

## 同时推送到 Gitee 和 GitHub（可选）

如需同时推送到两个平台：

```bash
# 添加 Gitee 远程仓库
git remote add gitee git@gitee.com:用户名/仓库名.git

# 推送时
git push github main  # 推送到 GitHub
git push gitee main   # 推送到 Gitee
```

---

## 参考链接

- [Streamlit Cloud 文档](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit 官方文档](https://docs.streamlit.io/)
- [GitHub SSH 文档](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

---

## 附录：完整部署检查清单

部署前请确认：

- [ ] 已生成 SSH 密钥并添加到 GitHub
- [ ] 项目已推送到 GitHub
- [ ] `requirements.txt` 已创建并包含所有依赖
- [ ] 代码中使用相对路径而非绝对路径
- [ ] 数据文件已推送到 GitHub（文件大小 < 100MB）
- [ ] 已在 Streamlit Cloud 中正确配置应用路径
- [ ] 部署成功并能正常访问

---

*最后更新：2026年2月*
