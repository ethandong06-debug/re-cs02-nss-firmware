'use strict';
'require view';

return view.extend({
	// 薄壳入口：立即跳转到 AthenaWrt 液态玻璃单页（SPA）
	load: function() {
		window.location.replace('/luci-static/resources/view/athena/index.html');
		// 立即 resolve，避免 LuCI 视图框架停留在"加载中"状态
		return Promise.resolve();
	},
	render: function() {
		return E('div', { 'class': 'cbi-map' }, '正在加载 AthenaWrt…');
	}
});
