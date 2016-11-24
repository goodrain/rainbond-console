USE console;
CREATE TABLE `tenant_service_image_relation` (
    `ID`         INT(11)      NOT NULL AUTO_INCREMENT,
    `tenant_id`  VARCHAR(32)  NOT NULL,
    `service_id` VARCHAR(32)  NOT NULL,
    `image_url`  VARCHAR(100) NOT NULL,
    PRIMARY KEY (`ID`)
)
    ENGINE = InnoDB
    AUTO_INCREMENT = 39
    DEFAULT CHARSET = utf8;

CREATE TABLE `docker_compose_yaml` (
    `ID`         INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version`    VARCHAR(10)            NOT NULL,
    `file_name`  VARCHAR(100)           NOT NULL,
    `md5`        VARCHAR(100)           NOT NULL,
    `services`   VARCHAR(3000)          NOT NULL,
    `volumes`    VARCHAR(1000)          NOT NULL,
    `networks`   VARCHAR(500)           NOT NULL,
    `build_args` VARCHAR(200)           NOT NULL
);

CREATE TABLE `docker_service` (
    `ID`             INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `compose_id`     INTEGER                NOT NULL,
    `command`        VARCHAR(100)           NULL,
    `name`           VARCHAR(100)           NOT NULL,
    `depends_on`     VARCHAR(100)           NOT NULL,
    `entrypoint`     VARCHAR(100)           NOT NULL,
    `environment`    VARCHAR(500)           NOT NULL,
    `image`          VARCHAR(100)           NOT NULL,
    `links`          VARCHAR(500)           NOT NULL,
    `expose`         VARCHAR(100)           NOT NULL,
    `ports`          VARCHAR(500)           NOT NULL,
    `volumes`        VARCHAR(500)           NOT NULL,
    `volumes_from`   VARCHAR(15)            NOT NULL,
    `build`          VARCHAR(100)           NOT NULL,
    `context`        VARCHAR(30)            NOT NULL,
    `dockerfile`     VARCHAR(30)            NOT NULL,
    `args`           VARCHAR(100)           NOT NULL,
    `cap_add`        VARCHAR(100)           NOT NULL,
    `cap_drop`       VARCHAR(100)           NOT NULL,
    `cgroup_parent`  VARCHAR(50)            NOT NULL,
    `container_name` VARCHAR(50)            NOT NULL,
    `devices`        VARCHAR(50)            NOT NULL,
    `dns`            VARCHAR(50)            NOT NULL,
    `dns_search`     VARCHAR(50)            NOT NULL,
    `tmpfs`          VARCHAR(50)            NOT NULL,
    `env_file`       VARCHAR(100)           NOT NULL,
    `extends`        VARCHAR(100)           NOT NULL,
    `external_links` VARCHAR(100)           NOT NULL,
    `extra_hosts`    VARCHAR(100)           NOT NULL,
    `group_add`      VARCHAR(50)            NOT NULL,
    `isolation`      VARCHAR(20)            NOT NULL,
    `logging`        VARCHAR(200)           NOT NULL
);
CREATE TABLE `tenant_compose_file` (
    `ID`              INT(11)     NOT NULL AUTO_INCREMENT,
    `tenant_id`       VARCHAR(32) NOT NULL,
    `compose_file_id` VARCHAR(32) NOT NULL,
    `compose_file`    VARCHAR(100)         DEFAULT NULL,
    PRIMARY KEY (`ID`)
)
    ENGINE = InnoDB
    AUTO_INCREMENT = 2
    DEFAULT CHARSET = utf8;


USE region;
ALTER TABLE tenant_services
    ADD code_from VARCHAR(20) DEFAULT NULL;
