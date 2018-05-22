CREATE TABLE console.user_message
(
    ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    message_id VARCHAR(32),
    receiver_id INT,
    content VARCHAR(256),
    is_read TINYINT DEFAULT 0,
    create_time DATETIME,
    update_time DATETIME,
    msg_type VARCHAR(15),
    announcement_id VARCHAR(32)
);