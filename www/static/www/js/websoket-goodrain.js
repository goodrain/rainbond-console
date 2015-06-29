var websocket_uri = "ws://123.59.40.70:6060/websocket"

WEB_SOCKET_SWF_LOCATION = '/static/www/js/WebSocketMain.swf';
WEB_SOCKET_DEBUG = true;
var browser_ua = navigator.userAgent.toLowerCase();
if (browser_ua.indexOf('360se') != -1 || browser_ua.indexOf('maxthon') != -1) {
	WEB_SOCKET_SWF_LOCATION += '?v=' + new Date().getTime().toString();
}

function extPushWebSocketClient() {

}

function extPushWebSocketConnect(client) {
	this.requestUrl = websocket_uri.split(","); // 扩充服务器
	this.socketStore = ''; // web_socket对象存储
	this.keeplivetime = 5; // 心跳时间
	this.trytimes = 1; // 重试次数
	this.linkIndex = 0 // parseInt(Math.random() * 1); //下标值，连接地址随机0, 1
}

extPushWebSocketConnect.prototype = {
	// 连接初始化
	init : function(client, topic, cmd, key, info) {
		this.socketStore = '';
		var self = this, url = this.requestUrl[this.linkIndex];
		this.socketStore = new WebSocket(url);
		// alert(this.client)
		this.socketStore.onopen = function() {
			// if (!$.browser.msie) {
			// console.log("extPush:onopen");
			// }
			if (topic != undefined && topic != "undefined") {
				if (info == undefined) {
					info = ""
				}
				self.sendCmd(topic, cmd, key, info);
			}
			self.trytimes = 1;
		};
		this.socketStore.onmessage = function(e) {
			if (e.data) {
				client.onMessage(e.data)
			}
		};
		this.socketStore.onclose = function() {
			// if (!$.browser.msie) {
			// console.log("extPush:onclose");
			// }
			self.closeWebSocket();
			self.init(client)
		};
		this.socketStore.onerror = function() {
			// if (!$.browser.msie) {
			// console.log("extPush:onerror");
			// }
		};
		this.keepWebSocketLive(client, topic, cmd, key, info);
		this.windowCloseCheck();
	},
	sendCmd : function(topic, cmd, key, info) {
		if (info == undefined) {
			info = ""
		}
		var self = this;
		self.socketStore.send(cmd + ";" + topic + ";" + key + ";" + info);
	},
	closeWebSocket : function() {
		var self = this;
		self.socketStore.close();
	},
	keepWebSocketLive : function(client, topic, cmd, key, info) {
		var self = this;
		clearInterval(window.sockeyTryAgain);
		clearTimeout(window.socketJoinSucc);
		clearTimeout(window.resetCheckFlag);
		window.sockeyTryAgain = setInterval(function() {
			if (self.socketStore.readyState == 0
					|| self.socketStore.readyState == 2
					|| self.socketStore.readyState == 3
					|| self.socketStore.bufferedAmount > 0) {
				self.closeWebSocket();
				self.init(client, topic, cmd, key,info)
			} else {
				//self.sendCmd("check", "1", "1")
				self.init(client, topic, cmd, key,info)
			}
		}, 1000 * 12 * self.keeplivetime);
	},
	windowCloseCheck : function() {
		var self = this;
		// if ($.browser.msie) {
		// window.onbeforeunload = onbeforeunload_handler;
		// function onbeforeunload_handler() {
		// self.closeWebSocket();
		//			}
		//		}
	}
};
