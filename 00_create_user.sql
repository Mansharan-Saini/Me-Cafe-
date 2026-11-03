-- =====================================================================
-- 00_create_user.sql  (OPTIONAL)
-- Run this ONCE as a privileged user (SYSTEM or SYS) connected to the
-- PLUGGABLE database (XEPDB1 on 21c XE, FREEPDB1 on 23ai Free).
-- Do NOT run it while connected to CDB$ROOT (you would get ORA-65096).
--
-- SQL Developer prompts for the password when this script runs.
-- Never save a real password in this file or source control.
-- =====================================================================

ACCEPT food_admin_password CHAR PROMPT 'Enter a strong password for FOOD_ADMIN: '
CREATE USER food_admin IDENTIFIED BY "&food_admin_password"
    DEFAULT TABLESPACE users
    QUOTA UNLIMITED ON users;

-- Minimum rights needed for the small project (tables and PL/SQL).
GRANT CREATE SESSION   TO food_admin;
GRANT CREATE TABLE     TO food_admin;
GRANT CREATE SEQUENCE  TO food_admin;
GRANT CREATE PROCEDURE TO food_admin;

UNDEFINE food_admin_password
