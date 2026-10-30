#!/usr/bin/env bash
set -euo pipefail
# Generated lab passwords use only hexadecimal characters. Never echo SQL.
[[ "$LAB_RUNTIME_PASSWORD" =~ ^[a-f0-9]+$ && "$LAB_READER_PASSWORD" =~ ^[a-f0-9]+$ ]]
export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"
mysql -uroot <<SQL
CREATE USER IF NOT EXISTS 'crm_runtime'@'%' IDENTIFIED BY '$LAB_RUNTIME_PASSWORD';
CREATE USER IF NOT EXISTS 'crm_reader'@'localhost' IDENTIFIED BY '$LAB_READER_PASSWORD';
GRANT SELECT ON crm_lab.* TO 'crm_runtime'@'%';
GRANT SELECT, SHOW VIEW, TRIGGER ON crm_lab.* TO 'crm_reader'@'localhost';
GRANT SHOW_ROUTINE ON *.* TO 'crm_reader'@'localhost';
GRANT ALL PRIVILEGES ON test_crm_lab.* TO 'crm_migrate'@'%';
SQL
for table in auth_user auth_group auth_permission auth_user_groups auth_user_user_permissions auth_group_permissions django_session django_admin_log website_record; do
  mysql -uroot -e "GRANT INSERT, UPDATE, DELETE ON crm_lab.$table TO 'crm_runtime'@'%'"
done
if mysql -uroot -N -e "SHOW TABLES FROM crm_lab LIKE 'website_auditevent'" | grep -q website_auditevent; then
  mysql -uroot -e "GRANT INSERT ON crm_lab.website_auditevent TO 'crm_runtime'@'%'"
fi
