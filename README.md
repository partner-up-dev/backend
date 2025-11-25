# Main

这个Repo是Anana - Backend的项目，其负责实现Anana产品的核心功能

目前版本：`v0.3.0`

## 项目概览

语言环境：Python 3.12

框架：BlueFirmament

依赖：Supabase, Redis, WeChat API, 等

## 环境配置

### 密钥管理

本项目使用环境变量来管理**密钥和敏感信息**。非敏感的配置（基础设施绑定、业务规则）保留在 JSON 文件中。

#### 快速开始

1. **复制环境变量模板**
   ```bash
   cp .env.example .env
   ```

2. **编辑 `.env` 文件，填入实际密钥**
   
   仅填写密钥类信息：
   - 数据库密钥（Supabase keys）
   - Redis 密码
   - 微信 API 密钥
   - 微信支付密钥
   - JWT 密钥
   - 地图服务密钥

3. **配置非敏感信息**
   
   在 `data/json/` 目录下的 JSON 文件中配置：
   - URL、主机、端口（基础设施绑定）
   - 业务规则、模板 ID
   - 功能标志

4. **确保 `.env` 不被提交**
   
   已添加到 `.gitignore`。

详细说明请参考 `.env.example` 文件。

### Supabase

#### 开发环境安装版

部署在dev.hadream.local /mnt/env/Supabase上，采用docker部署

安装指导：https://supabase.com/docs/guides/self-hosting/docker

端口矩阵：
|Port|Service|
|--|--|
|8000|Dashboard|
|||
|||
