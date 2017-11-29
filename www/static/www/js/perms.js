(function($){
    var csrftoken = $.cookie('csrftoken');
    var tenantName = $('#mytags').attr('tenant');
    var serviceAlias = $('#mytags').attr('service');

    $(document).ready(function() {  
      $('#permission a.member-remove').click(
        function() {
          user = $(this).closest('tr').attr('entry-user');
          perm_type = $(this).closest('table').attr('perm-type');
          tr = $(this).closest('tr')

          var url;
          if (perm_type=='service') {
            url = '/ajax/' + tenantName + '/' + serviceAlias + '/perms';
          } else if (perm_type=='tenant') {
            url = '/ajax/' + tenantName + '/perms';
          }

          $.ajax({
            url: url, method: "POST",
            data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity": "remove"},
            success: function (event) {
              tr.remove();
              $.action_report(event);
            },

            statusCode: {
                403: function(event) {
                  swal("你没有此权限！");
                }
            },

          })
        }
      )

      $('#permission tbody td input').click(
        function() {
          checked = $(this).prop('checked');
          
          user = $(this).closest('tr').attr('entry-user');
          perm_type = $(this).closest('table').attr('perm-type');
          var url;

          if (perm_type=='service') {
            url = '/ajax/' + tenantName + '/' + serviceAlias + '/perms';
          } else if (perm_type=='tenant') {
            url = '/ajax/' + tenantName + '/perms';
          }

          if (checked) {
            identity = $(this).attr('identity');
            next_identities = $(this).parent().nextAll()
            console.log(identity);
            $.ajax({
              url: url,
              method: "POST",
              data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity":identity},
              success: function (event) {
                  console.log(event);
                  if (event.ok) {
                    next_identities.children('input').prop('checked',true).prop('disabled',true);
                  } else {
                    $(this).prop('checked',false);
                  }
                  $.action_report(event);
              },
              
              statusCode: {
                403: function(event) {
                  swal("你没有此权限！");
                }
              },
              
            });

          } else {
            next = $(this).parent().next('th');
            identity = next.children('input').attr('identity');
            console.log(identity);
            $.ajax({
              url: url,
              method: "POST",
              data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity":identity},
              success :function (event) {
                console.log(event);
                $.action_report(event);
                if (next.is('.perm-modify-enable')) {
                  next.children('input').prop('disabled',false);
                }
              },

              statusCode: {
                403: function(event) {
                  swal("你没有此权限！");
                }
              },
            });
            return true;
          }

        }
      );

        $('#invite_user_btn').click(function() {
            identity = $("#ivite_perm").val();
            var email = $("#invite_email").val();
            if (email == "") {
                swal("邮件地址不能为空!");
                return;
            }

            if(typeof(serviceAlias) == "undefined" || serviceAlias==""){
                url = '/ajax/' + tenantName +'/invite';
            } else {
                url = '/ajax/' + tenantName + '/' + serviceAlias + '/invite';
            }

            $.ajax({
                url: url,
                data: {
                    "csrfmiddlewaretoken":csrftoken,
                    "email":email,
                    "identity":identity
                },
                method: "POST",
                success: function (event) {
                    console.log(event);
                    $.action_report(event);
                },
                statusCode: {
                    500: function() {
                        swal("服务器错误,请稍后再尝试！");
                    }
                }
            });
        }
      );
      //option:selected
    
    });

})(jQuery);