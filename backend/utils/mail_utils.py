import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_reset_email(to_email, token):
    """
    開発用SMTPサーバー（Mailpit）を経由して、パスワード再設定用のURLリンクを送信します。
    """
    smtp_server = "mailpit"  # Dockerコンテナ名
    smtp_port = 1025
    sender_email = "system@example.com"
    reset_url = f"http://localhost:8501/?token={token}"  # フロントエンドURL
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = "【重要】パスワード再設定のご案内"
    
    body = f"""
    パスワード再設定のリクエストを受け付けました。
    以下のリンクをクリックして、30分以内に新しいパスワードを設定してください。

    {reset_url}

    ※心当たりがない場合は、このメールを破棄してください。
    """
    message.attach(MIMEText(body, "plain"))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.sendmail(sender_email, to_email, message.as_string())
