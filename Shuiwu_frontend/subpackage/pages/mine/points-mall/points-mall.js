// 积分商城页面
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';

const getAuthHeader = () => {
  const token = wx.getStorageSync('access_token');
  if (!token) {
    return '';
  }
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return `${normalizedType} ${token}`;
};

Page({
  /**
   * 页面的初始数据
   */
  data: {
    userPoints: '0',
    products: [
      {
        id: 1,
        name: 'VIP会员月卡',
        points: 500,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
        badge: '热销'
      },
      {
        id: 2,
        name: 'VIP会员季卡',
        points: 1200,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
        badge: '推荐'
      },
      {
        id: 3,
        name: '税务咨询券',
        points: 300,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
      },
      {
        id: 4,
        name: '合同审查券',
        points: 400,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
      },
      {
        id: 5,
        name: '报税申报券',
        points: 600,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
      },
      {
        id: 6,
        name: '企业体检券',
        points: 800,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
        badge: '新品'
      },
      {
        id: 7,
        name: '发票识别券',
        points: 200,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
      },
      {
        id: 8,
        name: '专属客服月卡',
        points: 1000,
        stock: 0,
        image: `${OSS_URL}/images/mall/暂未上架.png`,
        badge: '限时'
      },
    ]
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad() {
    this.loadUserPoints();
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    this.loadUserPoints();
  },

  /**
   * 加载用户积分
   */
  loadUserPoints() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      this.setData({ userPoints: '0' });
      return;
    }

    wx.request({
      url: `${API_BASE_URL}/api/user/points/records?page=1&page_size=1`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      timeout: 10000,
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        if (!ok) {
          return;
        }

        const data = payload.code === 1 && payload.data ? payload.data : payload;
        const rawRecords = Array.isArray(data.records) ? data.records : [];

        if (rawRecords.length > 0) {
          // 获取最新记录的余额
          const balance = Number(rawRecords[0].balance_after || 0);
          this.setData({
            userPoints: balance % 1 === 0 ? balance.toFixed(0) : balance.toFixed(2)
          });
        } else {
          this.setData({ userPoints: '0' });
        }
      },
      fail: (err) => {
        console.error('获取积分余额失败：', err);
        this.setData({ userPoints: '0' });
      },
    });
  },

  /**
   * 点击商品
   */
  onProductClick(e) {
    const product = e.currentTarget.dataset.product;

    wx.showModal({
      title: '确认兑换',
      content: `确定要消耗 ${product.points} 积分兑换「${product.name}」吗？`,
      confirmText: '确认兑换',
      confirmColor: '#3B55F3',
      success: (res) => {
        if (res.confirm) {
          this.handleExchange(product);
        }
      }
    });
  },

  /**
   * 处理兑换逻辑
   */
  handleExchange(product) {
    // 检查商品库存
    if (product.stock <= 0) {
      wx.showToast({
        title: '商品待补充',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 检查积分是否足够
    const currentPoints = parseFloat(this.data.userPoints);
    if (currentPoints < product.points) {
      wx.showToast({
        title: '积分不足',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 模拟兑换成功
    wx.showLoading({
      title: '兑换中...',
      mask: true
    });

    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({
        title: '兑换成功',
        icon: 'success',
        duration: 2000
      });

      // 扣除积分（仅更新本地显示，实际需要后端接口）
      const newPoints = (currentPoints - product.points).toFixed(2);
      this.setData({
        userPoints: newPoints
      });
    }, 1000);
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {

  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.loadUserPoints();
    wx.stopPullDownRefresh();
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onPointsDetailTap() {
    wx.navigateTo({
      url: '/subpackage/pages/mine/point/point',
      fail: () => {
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none',
        });
      },
    });
  },

  onReachBottom() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})
