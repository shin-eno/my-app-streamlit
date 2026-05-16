-- 初期メニューデータの投入
INSERT INTO menu_permissions (page_title, file_path, icon, section_name, is_admin_only, display_order) VALUES
('ダッシュボード', 'views/1_Dashboard.py', '📊', 'メインメニュー', FALSE, 10),
('ユーザー管理', 'views/2_User_List.py', '👥', '管理設定', TRUE, 20),
('ユーザー登録', 'views/9_User_Registration.py', '👤', '管理設定', TRUE, 30);

INSERT INTO menu_permissions (page_title, file_path, icon, section_name, is_admin_only, display_order)
VALUES ('パスワード変更', 'views/3_Password_Change.py', '🔑', 'アカウント管理', FALSE, 40);
