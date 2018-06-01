# RainBond UI Development Document


**Rainbond UI** is written by [Python](https://www.python.org/) and based on Python Web framework [Django](https://www.djangoproject.com/).providing basic web UI for rainbond.You can see it [here](https://console.goodrain.com).

## To start running RainBondUI

### Install rainbond
To run rainbondUI,First of all, you need install rainbond datecenter.RainbondUI is just a client in a sense. To [install Rainbond](https://github.com/goodrain/rainbond).

### Quick Start

According to the installation document of Rainbond,you may already install the RainbondUI , and you can have an access to the console without other settings.
However, If you want to develop Rainbond by youself, we strongly recommend that you use you own database and follow the Instructions bellow.

* clone the code:

~~~
git clone git@github.com:goodrain/rainbond-ui.git
~~~

* configurate you rainbondUI

Otherwise, You need this config in you environment.

`MYSQL_HOST`:the host of mysql
`MYSQL_PORT`:the port of mysql
`MYSQL_USER`:the username of mysql
`MYSQL_PASS`:the password of mysql
`MYSQL_DB`:the database of you rainbond
`REGION_TAG`: the config file you use.(if you use in production it is better to be `www-com` if you use in test way `gr-test` is here for you.You can see details in the code)

* init mysql datebase

~~~
python manage.py makemigrations
python manage.py migrate
~~~

* add you region info into database

  example:

```
INSERT INTO `console_sys_config` (`ID`,`key`,`type`, `value`, `desc`, `enable`, `create_time`) VALUES(NULL, 'REGION_SERVICE_API', 'json', '  [{"url": "http://region.goodrain.me:8888", "token": null, "enable": true, "region_name": "rainbond", "region_alias": "rainbond"}]', '', 1, '2018-02-05 14:00:00.000000');

INSERT INTO `region_info` ( `region_id`, `region_name`, `region_alias`, `url`, `token`, `status`, `desc`, `wsurl`, `httpdomain`, `tcpdomain`) VALUES('asdasdasdasdasdasdasdasdas', 'rainbond', 'private-center', 'http://region.goodrain.me:8888', NULL, '1', 'default region', 'ws://$IP:6060', '$DOMAIN', '$IP');
```

* run the rainbondUI

Get into the root directory of rainbondUI. Run command :

```
python manage.py runserver 0.0.0.0:8000
```



After the you can run the rainbond UI.

### Struct of RainbondUI

The project is from the typical Django projects. RainbondUI is a  `backend-frontend` framework. JavaScript loaded in the browser sends a HTTP request (XHR, XML HTTP Request) from within the page and historically got a Json Response.

The Backend is using  [Django REST framework](http://www.django-rest-framework.org/). 


**Backend**

RainbondUI has 4 main modules.

![base-modules](http://grstatic.oss-cn-shanghai.aliyuncs.com/images/acp/docs/user-docs/rainbondui/base-modules.png)

* `console` is the main api interface for frontend invoking. All of the invoke route is in console module.
* `backends` is main api interface for back manager.If you not using back-manager ,you can just ignore this part.
* `marketapi` is the main api for public app market.Just ignore it when you are using private cloud.
* `www` is the main module we use before. Some files or code are discarded.

**Frontend**

RainbondUI fronend is using [React](https://reactjs.org/)

To Run fronend, you need to install [nodejs](https://nodejs.org/) (version > 8.0).And then go into the directory `www/static/ant-pro/ant-design-pro-template` .

* install dependencies

```
npm install 
```

* start npm

```
npm run start
```

* build files 

```
npm run build
```





