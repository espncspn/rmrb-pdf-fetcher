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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib import colors

class BookmarkDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, id="normal")
        template = PageTemplate(id="main", frames=frame)
        self.addPageTemplates([template])
        self.bookmarks = []

    def afterFlowable(self, flowable):
        if hasattr(flowable, "bookmark_key"):
            key = flowable.bookmark_key
            title = flowable.bookmark_title
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0, closed=False)

class BookmarkParagraph(Paragraph):
    def __init__(self, text, style, bookmark_key=None, bookmark_title=None):
        super().__init__(text, style)
        self.bookmark_key = bookmark_key
        self.bookmark_title = bookmark_title

def txt_to_pdf(txt_path, pdf_path):
    subprocess.run(["sudo", "apt-get", "install", "-y", "fonts-wqy-zenhei"],
                   capture_output=True)
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    pdfmetrics.registerFont(TTFont("WQY", font_path))

    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    heading_style = ParagraphStyle(
        name="Heading", fontName="WQY", fontSize=15,
        leading=28, wordWrap="CJK", spaceAfter=6
    )
    body_style = ParagraphStyle(
        name="Chinese", fontName="WQY", fontSize=13,
        leading=24, wordWrap="CJK"
    )

    story = []
    bookmark_count = 0

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 8))
        elif line.startswith("【") and line.endswith("】"):
            key = f"bookmark_{bookmark_count}"
            bookmark_count += 1
            p = BookmarkParagraph(line, heading_style,
                                  bookmark_key=key,
                                  bookmark_title=line.strip("【】"))
            story.append(p)
            story.append(Spacer(1, 4))
        elif "=====" in line:
            title = line.replace("=", "").strip()
            if title:
                key = f"bookmark_{bookmark_count}"
                bookmark_count += 1
                p = BookmarkParagraph(title, heading_style,
                                      bookmark_key=key,
                                      bookmark_title=title)
                story.append(p)
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph(line, body_style))
            story.append(Spacer(1, 4))

    doc = BookmarkDocTemplate(pdf_path, pagesize=A4,
                              leftMargin=25*mm, rightMargin=25*mm,
                              topMargin=20*mm, bottomMargin=20*mm)
    doc.build(story)

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

    opinion_files = glob.glob("opinion_articles.txt")
    if opinion_files:
        with open(txt_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            with open(opinion_files[0], "r", encoding="utf-8") as op:
                f.write(op.read())
        print("已合并评论内容")

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
