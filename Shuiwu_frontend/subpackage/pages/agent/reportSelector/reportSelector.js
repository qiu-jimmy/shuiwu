/**
 * reportSelector.js — 数企云检报告类型选择页
 *
 * 功能：
 *   - 展示三种报告类型：全景报告、发票穿透报告、经营风险报告
 *   - 点击全景报告跳转到已有的 corporateHealth 页面
 *   - 点击其余两种跳转到对应新报告页面
 */

Page({
  onPanoramicTap() {
    wx.navigateTo({
      url: '/subpackage/pages/agent/corporateHealth/corporateHealth',
    });
  },

  onInvoiceTap() {
    wx.navigateTo({
      url: '/subpackage/pages/agent/invoicePenetration/invoicePenetration',
    });
  },

  onBusinessTap() {
    wx.navigateTo({
      url: '/subpackage/pages/agent/businessRisk/businessRisk',
    });
  },
});
