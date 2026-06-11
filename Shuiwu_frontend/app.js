/**
 * 小程序入口文件
 *
 * 功能说明：
 * - 设置全局请求超时时间（5分钟）
 * - 处理启动参数（扫码进入、分享链接等）
 * - 管理全局数据
 *
 * 启动参数处理：
 * 1. 用户扫描小程序码进入
 * 2. onLaunch/onShow捕获scene参数并保存到globalData
 * 3. 用户登录时使用相关参数
 * 4. 后端处理相关逻辑
 */

const DEFAULT_TIMEOUT = 5 * 60 * 1000;
const originRequest = wx.request;

// 设置全局请求超时时间
wx.request = function (options = {}) {
  return originRequest({
    ...options,
    timeout: DEFAULT_TIMEOUT,
  });
};

App({
  /**
   * 小程序初始化
   * 处理冷启动时的启动参数（扫码、分享链接等）
   */
  onLaunch(options) {
    this.handleLaunchOptions(options);

    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    wx.setStorageSync('logs', logs);

    // 登录（原保留逻辑）
    wx.login({
      success: res => {
        // 发送 res.code 到后台换取 openId, sessionKey, unionId
      }
    });
  },

  /**
   * 小程序显示
   * 处理热启动时的启动参数（用户可能扫码进入已启动的小程序）
   */
  onShow(options) {
    this.handleLaunchOptions(options);
  },

  /**
   * 处理启动参数
   *
   * 支持的场景：
   * 1. 扫描小程序码进入（options.scene包含相关参数）
   * 2. 分享链接进入（options.query.invite_code）
   *
   * @param {Object} options - 启动参数
   */
  handleLaunchOptions(options) {
    if (!options) return;

    // 注意：App.onLaunch/onShow 中的 options.scene 是微信场景值编号（整数，如 1047 代表扫描小程序码），
    // 不是 wxacode.getUnlimited 传入的自定义字符串（邀请码）。
    // 冷启动时，真正的邀请码由落地页（pages/index/index/index）的 onLoad(options.scene) 读取并存入 globalData。
    // 热启动时（小程序已在内存中，落地页 onLoad 不会重新执行），邀请码在 options.query.scene 中。

    // 处理分享链接场景：URL参数中的invite_code
    if (options.query && options.query.invite_code) {
      console.log('[启动参数] 检测到邀请码(query):', options.query.invite_code);
      this.globalData.pendingInviteCode = options.query.invite_code;
    }

    // 处理 wxacode.getUnlimited 热启动场景：
    // 落地页已在内存中时，onLoad 不会重新执行，推广码通过 options.query.scene 传入
    if (options.query && options.query.scene) {
      const inviteCode = decodeURIComponent(String(options.query.scene));
      if (inviteCode) {
        console.log('[启动参数] 检测到扫码邀请码(query.scene，热启动):', inviteCode);
        this.globalData.pendingInviteCode = inviteCode;
      }
    }
  },

  /**
   * 全局数据
   */
  globalData: {
    userInfo: null,
    /**
     * 待处理的邀请码
     * 用户扫码进入小程序后，邀请码暂存于此
     * 在用户登录/注册时传递给后端处理
     */
    pendingInviteCode: null
  }
});
