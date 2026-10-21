CREATE TABLE IF NOT EXISTS Users (
    uid       BINARY(16)                          NOT NULL,
    username  VARCHAR(255)                        NOT NULL,
    password  VARCHAR(255)                        NULL DEFAULT NULL,
    -- MariaDB foloseste prima valoare cand rolul lipseste: trebuie sa fie cea mai putin privilegiata.
    role      ENUM('maintainer', 'administrator') NOT NULL,
    is_active BOOLEAN                             NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_users PRIMARY KEY (uid),
    CONSTRAINT uk_users_username UNIQUE (username)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
