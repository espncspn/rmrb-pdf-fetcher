import smtplib
import os
import glob
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def txt_to_pdf(txt_path, pdf_path):
    subprocess.run(["sudo", "apt-get", "install", "-y", "fonts-wqy-zenhei"], 
                   capture_output=True)
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    pdfmetrics.registerFont(TTFont("WQY", font_path))

    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    c.setFont("WQY", 12)
    margin = 50
    y = height - margin
    line_height = 20

    for line in lines:
        line = line.rstrip()
        if y < margin:
            c.showPage()
            c.setFont("WQY", 12)
            y = height - margin
        c.drawString(margin, y, line)
        y -= line_height

    c.save()

def send_email():
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    receiver = os.environ.get("EMAIL_RECEIVER")

    today = datetime.now().strftime("%Y-%m-%d")

    txt_files = glob.glob("merged_articles.txt")
    if not txt_files:
        print("未找到文章文件")
        return

    txt_path = txt_files[0]
    pdf_path = f"rmrb-{today}.pdf"
    print(f"正在转换PDF: {txt_path}")
    txt_to_pdf(txt_path, pdf_path)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = f"人民日报 {today}"
    msg.attach(MIMEText(f"{today} 人民日报，请查收附件。", "plain", "utf-8"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="rmrb-{today}.pdf"')
    msg.attach(part)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        print(f"发送成功！收件人：{receiver}")

if __name__ == "__main__":
    send_email()
