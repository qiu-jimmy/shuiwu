// pages/index/allInput/allInput.js
import { OSS_URL } from '../../../../utils/config';

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL
  },

  /**
   * 智能税务申报点击事件
   */
  onShuiwuInputTap() {
    wx.navigateTo({
      url: '/subpackage/pages/index/shuiwuInput/shuiwuInput'
    });
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {

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

  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})