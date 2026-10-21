-- Fara parola: administratorul si-o seteaza prin ActivateAccount.
INSERT IGNORE INTO Users (uid, username, password, role, is_active)
VALUES (UNHEX(REPLACE(UUID_v7(), '-', '')), 'admin', NULL, 'administrator', FALSE);
