/**
 * taxAuthWebview.js — 税局授权 H5 跳板页
 *
 * 功能：
 *   - 接收 url 参数（第三方 H5 授权链接）并加载到 web-view
 *   - 授权完成后，第三方 H5 页面会重定向到我们的 cburl
 *   - cburl 为后端提供的 HTML 中间页，调用 wx.miniProgram.navigateTo 跳回报告页
 *   - 用户也可手动点击「授权完成，返回」按钮回到上一页
 *
 * URL 参数：
 *   - url: 第三方 H5 授权链接（encodeURIComponent 编码）
 *   - orderNo: 订单号（encodeURIComponent 编码）
 *   - returnPage: 返回的报告页面名称（invoicePenetration / businessRisk）
 */

Page({
  data: {
    authUrl: '',
    orderNo: '',
    returnPage: 'invoicePenetration',
    loaded: false,
  },

  onLoad(options) {
    const url = options.url ? decodeURIComponent(options.url) : '';
    const orderNo = options.orderNo ? decodeURIComponent(options.orderNo) : '';
    const returnPage = options.returnPage || 'invoicePenetration';

    if (!url) {
      wx.showToast({ title: '授权链接无效', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }

    this.setData({ authUrl: url, orderNo, returnPage });
  },

  onWebViewMessage(e) {
    // 处理 H5 页面发来的消息（若有需要）
    const messages = e.detail && e.detail.data ? e.detail.data : [];
    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      // 若 H5 发送 {type: 'auth_complete'}，自动返回并带 orderNo
      if (lastMsg && lastMsg.type === 'auth_complete') {
        this.onAuthComplete();
      }
    }
  },

  onWebViewError(e) {
    wx.showToast({ title: '页面加载失败', icon: 'none' });
    console.error('webview error:', e.detail);
  },

  // 用户手动点击"授权完成，返回查看"
  onAuthComplete() {
    const { orderNo, returnPage } = this.data;
    const pageMap = {
      invoicePenetration: '/subpackage/pages/agent/invoicePenetration/invoicePenetration',
      businessRisk: '/subpackage/pages/agent/businessRisk/businessRisk',
    };
    const targetPage = pageMap[returnPage] || pageMap.invoicePenetration;
    const url = orderNo
      ? `${targetPage}?orderNo=${encodeURIComponent(orderNo)}&fromAuth=true`
      : targetPage;

    // 尝试 navigateBack，失败则 navigateTo
    wx.navigateBack({
      fail: () => {
        wx.navigateTo({ url });
      },
    });
  },
});
