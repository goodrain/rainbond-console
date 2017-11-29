import createPageController from '../utils/page-controller';
import { 
	getTenantAllAppsStatusAndMemory,
	getAnnouncement
} from '../comms/apiCenter';
import util from '../utils/util';
import {
	getPageHomeData
} from '../comms/page-app-apiCenter';
import {
	getAllApp
} from '../comms/tenant-apiCenter';
var template = require('./home-tpl.html');

class NewsScroll {
	constructor(props){
		this.timer = null;
		this.index = 0;
		this.size = 0;
		this.maxItemHeight = 0;
		this.minItemHeight = 40;
		// 是否鼠标悬浮
		this.isHover = false;
		// 是否打开
		this.isOpen = false;
		this.$newsWrap = $('.news');
    	this.$newsList = $('.news-list');
    	this.$newsItem = this.$newsWrap.find('.news-item');
		this.init();
	}
	init(){
		this.initStatus();
		this.initDom();
		this.bindEvent();
		if(this.size > 1){
			this.setOpen(false);
			this.play();
		}
	}
	initDom(){
		this.$newsList.css({position:'absolute', top:0,visibility: 'visible'});
		this.$newsItem.height(this.maxItemHeight);
		if(this.size == 0){
			this.$newsWrap.hide();
		}
		
	}
	
	initStatus(){
		var self =  this;
		this.size = this.$newsItem.length;
		//最大高度
		this.$newsItem.each(function(){
			var itemHeight = $(this).outerHeight();
			self.maxItemHeight = Math.max(self.maxItemHeight, itemHeight);
		})
		this.maxItemHeight = Math.max(this.maxItemHeight, this.minItemHeight);
		

	}
	setOpen(isOpen){
		this.isOpen = isOpen;
		this.index = 0;
		this.$newsList.css({top: 0});
		if(isOpen){
			this.$newsWrap.height(this.maxItemHeight * this.size);
			$('.news-down').hide();
			$('.news-up').show();
		}else{
			this.$newsWrap.height(this.maxItemHeight);
			$('.news-down').show();
			$('.news-up').hide();
		}
	}
	setHover(isHover){
		this.isHover = isHover;
	}
	play(){
		var self = this;
	    this.timer = setTimeout(function(){
	      self.next();
	      self.doAnimate();
	    }, 5000)
	}
	doAnimate(){
		var self = this;
		this.$newsList.animate({
			top: -(this.index * this.maxItemHeight)
		},'fast', function(){
			if(!self.isOpen && !self.isHover){
				self.play();
			}
		})
	}
	next() {
		this.index ++;
		if(this.index >=this.size){
			this.index = 0;
		}
	}
	stop(){
		clearTimeout(this.timer);
	}
	bindEvent(){
		var self = this;
	    this.$newsWrap.bind('mouseenter', function(e){
	        self.setHover(true);
	        self.stop();
	    }).bind('mouseleave', function(e){
	        self.setHover(false);
	        if(!self.isOpen){
	      	   self.play();
	        }
	    })

	    this.$newsWrap.find('.news-down').bind('click', function(e){
	      self.stop();
	      self.setOpen(true);
	    })

	    this.$newsWrap.find('.news-up').bind('click', function(e){
	      self.setOpen(false);
	    })
	}
}






/* 业务逻辑控制器 */
const Home = createPageController({
	template: template,
	property: {
		//租户名
		tenantName: '',
		checkInterval: 3 * 1000,
		renderData:{
			pageData: {},
			apps:{}
		}
	},
	method: {
		//获取页面初始化数据
		getInitData: function(){
			return $.when(
				getPageHomeData(
					this.tenantName
				),
				getAllApp(
					this.tenantName
				)
			).done((pageData, apps) => {
				this.renderData.pageData = pageData;
				this.renderData.apps = apps || [];
				this.render();
			})
		},
		//轮询监测应用列表的运行状态
		checkAppsInfo: function() {

			getTenantAllAppsStatusAndMemory(
				this.tenantName
			).done((data) => {
				this.updateAppsInfo(data);
			}).always(() => {
				setTimeout(() => {
					this.checkAppsInfo();
				}, this.checkInterval);
			})
		},
		//更新状态dom
		updateAppsInfo: function(result){
			var list = result.list;
			var totalMemory = result.totalMemory;
			for(var i=0,len=list.length; i < len; i++){
				var app = list[i];
				var statusMap = util.getStatusMap(app.status);
				$("#service_status_"+app.id).find("span").html(app.statusCN);
				$("#service_status_"+app.id).find("span").attr("class",statusMap.bgClass +' pading5');
				$("#service_memory_"+app.id).html(app.runtime_memory+"M");
			}
			$("#service_total_memory").html(totalMemory+"M")
		},
		handleSearch: function(){
			var value = $.trim(this.$wrap.find('#search-key').val()) || '';
			var $rows = this.$wrap.find('.app-table-row');
			if(!value) {
				$rows.show();
			}else{
				$rows.each(function(){
					var name = $(this).attr('data-name') || '';
					if(name.indexOf(value) > -1){
						 $(this).show();
					}else{
						 $(this).hide();
					}
				})
			}
		},
		//获取公告信息
		getAnnounceMentShow: function(){
			getAnnouncement(
				this.tenantName
			).done(function(data){
				var datalist = data["announcements"];
				var dataStr = "";
				for(var i=0;i<datalist.length; i++){
					if(datalist[i]["a_tag_url"] == ""){
						dataStr += '<div class="alert alert-info">'+ datalist[i]["content"] +'</div>'
					}else{
						dataStr += '<div class="alert alert-info"><a href="'+ datalist[i]["a_tag_url"] +'" target="_blank">'+ datalist[i]["content"] +'。请点击查看详情！</a></div>'
					}
				}
				$("#home-wrap .news").after(dataStr);
			}).fail(function(data){
				console.log(data);
			})
		}
		
	},
	domEvents:{
		'#search-app-form submit': function(e){
			e.preventDefault();
			this.handleSearch();
			return false;
		}
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.getInitData().done(() => {
			setTimeout(() => {
				//新闻滚动
				this.getAnnounceMentShow();
				this.newsScroller = new NewsScroll();
				this.checkAppsInfo();
			})
		});
		
	}
})

window.HomeController = Home;
export default Home;