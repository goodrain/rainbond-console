const util ={
	getBody: function(response){
	    if(response){
	    	 return response.data;
	    }
	},
	//获取http status的值
	getHttpStatus: function(response){
		if(response){
	    	 return response.status;
	    }
	},
	//获取业务code
	getCode: function(response){
		var body = this.getBody(response);
		if( body ){
	    	 return body.code;
	    }
	},
	getMessage: function(response){
		if(response) {
			return response.msg_show;
		}
	}
}

export default util;