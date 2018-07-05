var domUtil = {
    prependChild: function(parent,child){ 
        if(parent.hasChildNodes()){ 
            parent.insertBefore(child ,parent.firstChild); 
        }else{ 
            parent.appendChild(child); 
        } 
    } 
}
export default domUtil;