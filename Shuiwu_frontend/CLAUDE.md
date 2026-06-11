# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is "智税引擎" (Smart Tax Engine), a WeChat Mini Program that provides AI-powered tax consultation services. The app features an intelligent chat assistant, file management, and various tax-related utilities.

## Development Environment

This is a WeChat Mini Program project. Development requires:
- **WeChat Developer Tools** - Open the project root directory in WeChat DevTools
- **Node.js** - For installing dependencies

## Common Commands

```bash
# Install dependencies (TDesign UI library)
npm install

# Build npm packages (required after npm install)
# Run this from WeChat DevTools: Tools > Build npm
```

No test framework is configured in this project.

## Architecture

### Tab-Based Navigation
The app has three main tab sections configured in [app.json](app.json):

1. **首页** (`pages/index/index/index`) - Home page with search and service categories
2. **AI** (`pages/agent/agent/agent`) - AI chat interface for tax consultation
3. **我的** (`pages/mine/mine/mine`) - User profile and settings

### Page Structure

**Main Pages (8)** - Loaded at startup:
- `pages/index/index/index` - Home page
- `pages/file/file/file` - File management
- `pages/agent/agent/agent` - AI assistant
- `pages/mine/mine/mine` - User profile
- `pages/mine/login/login` - Login page
- `pages/mine/register/register` - Register page
- `pages/agent/chat/chat` - Chat interface
- `pages/agent/chat-vip/chat-vip` - VIP chat interface

**Subpackage Pages (18)** - Lazy-loaded for performance:
- Located in `subpackage/pages/` directory
- Organized by feature: `agent`, `file`, `index`, `mine`
- Includes pages for: tax queries, business queries, contract review, invoice input, VIP management, etc.

### Component Framework
- Uses **TDesign Mini Program** (`tdesign-miniprogram`) as the UI component library
- Component framework: `glass-easel` (configured in [app.json](app.json:45))
- Lazy code loading is enabled for required components

### App Initialization

[app.js](app.js) sets up:
- Global HTTP request timeout of 5 minutes (overrides `wx.request`)
- WeChat login flow on app launch
- Global `userInfo` data store

### API Configuration

API base URL is configured in [utils/config.js](utils/config.js). Multiple environment URLs are available as commented options:
- Active: `http://192.168.0.58:8000`
- Alternates: `http://47.121.118.126:8000`, `http://192.168.0.40:8000`

### Project Configuration

WeChat Mini Program configuration in [project.config.json](project.config.json):
- **AppID**: `wx44805469e5b39573`
- **ES6 transpilation**: Enabled
- **PostCSS**: Enabled
- **Code minification**: Enabled (WXSS, WXML, JS)
- **Source maps**: Uploaded for debugging
- **Editor settings**: 2-space indentation

## Key Features

- AI-powered tax consultation chat
- File upload and management
- User authentication (login/register)
- VIP subscription system
- Tax case queries
- Business information queries
- Contract review
- Invoice input processing

## Development Notes

- Page structure follows WeChat Mini Program conventions: `.js` (logic), `.json` (config), `.wxml` (template), `.wxss` (styles)
- Subpackage architecture improves initial loading performance - add new non-critical pages to `subpackage/`
- When using TDesign components, follow the component library documentation
- API requests automatically have a 5-minute timeout
- Use `wx.navigateTo` for navigation within the subpackage
- Global state can be accessed via `getApp().globalData`
