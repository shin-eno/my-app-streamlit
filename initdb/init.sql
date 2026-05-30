-- 初期メニューデータの投入
INSERT INTO menu_permissions (page_title, file_path, icon, section_name, is_admin_only, display_order) VALUES
('ダッシュボード', 'views/1_Dashboard.py', '📊', 'メインメニュー', FALSE, 10),
('ユーザー管理', 'views/2_User_List.py', '👥', '管理設定', TRUE, 20),
('ユーザー登録', 'views/9_User_Registration.py', '👤', '管理設定', TRUE, 30),
('パスワード変更', 'views/3_Password_Change.py', '🔑', 'アカウント管理', FALSE, 40),
('レシート登録', 'views/5_Receipt_Manager.py', '🧾', '計上', FALSE, 40)
;

INSERT INTO menu_permissions (page_title, file_path, icon, section_name, is_admin_only, display_order)
VALUES ;

-- カテゴリ情報
INSERT INTO categories (name) VALUES ('食費'), ('消耗品'), ('交通費'), ('交際費'), ('その他') ON CONFLICT (name) DO NOTHING;


