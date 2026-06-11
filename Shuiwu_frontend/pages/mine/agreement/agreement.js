// pages/mine/agreement/agreement.js
Page({
  onLoad(options) {

  },

  onCopyTap() {
    wx.setClipboardData({
      data: 'zsj7777777wssy',
      success: () => {
        wx.showToast({
          title: '微信号已复制',
          icon: 'success'
        });
      }
    });
  }
})
