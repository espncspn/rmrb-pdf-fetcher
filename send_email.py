import smtplib
import os
import glob
import shutil
import subprocess
from html import escape
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

def install_linux_cjk_font():
    if os.name == "nt":
        return
    if os.path.exists("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        return

    apt_get = shutil.which("apt-get")
    if not apt_get:
        return

    sudo = shutil.which("sudo")
    command = [apt_get, "install", "-y", "fonts-noto-cjk", "fonts-wqy-zenhei"]
    if sudo:
        command.insert(0, sudo)

    subprocess.run(command, capture_output=True, check=False)

def register_first_available_font(candidates):
    last_error = None
    for font_name, paths in candidates:
        for font_path in paths:
            if not font_path or not os.path.exists(font_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name, None
            except Exception as exc:
                last_error = exc

    return None, last_error

def register_pdf_fonts():
    install_linux_cjk_font()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    simhei_paths = [
        os.environ.get("RMRB_PDF_FONT_PATH"),
        os.path.join(project_dir, "fonts", "simhei.ttf"),
        os.path.join(project_dir, "fonts", "SimHei.ttf"),
        r"C:\Windows\Fonts\simhei.ttf",
        "/usr/local/share/fonts/simhei.ttf",
        "/usr/share/fonts/truetype/simhei.ttf",
        "/usr/share/fonts/truetype/windows/simhei.ttf",
    ]
    wqy_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/wenquanyi/wqy-zenhei/wqy-zenhei.ttc",
    ]

    simhei_font, simhei_error = register_first_available_font(
        [("SimHei", simhei_paths)]
    )
    if simhei_font:
        print(f"PDF字体: 正文={simhei_font}, 标题={simhei_font}")
        return simhei_font, simhei_font

    body_font, body_error = register_first_available_font(
        [
            (
                "NotoSansCJK",
                [
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
                ],
            ),
            ("WQYZenHei", wqy_paths),
        ]
    )
    heading_font, heading_error = register_first_available_font(
        [
            (
                "NotoSansCJKBold",
                [
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.otf",
                ],
            ),
            (
                "NotoSansCJK",
                [
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
                ],
            ),
            ("WQYZenHei", wqy_paths),
        ]
    )

    if body_font:
        heading_font = heading_font or body_font
        print(f"PDF字体: 正文={body_font}, 标题={heading_font}")
        return body_font, heading_font

    raise RuntimeError(
        "未找到可用中文字体，PDF生成失败: "
        f"{body_error or heading_error or simhei_error}"
    )

def txt_to_pdf(txt_path, pdf_path):
    body_font, heading_font = register_pdf_fonts()

    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    heading_style = ParagraphStyle(
        name="Heading", fontName=heading_font, fontSize=18,
        leading=32, wordWrap="CJK", spaceAfter=8
    )
    body_style = ParagraphStyle(
        name="Chinese", fontName=body_font, fontSize=15,
        leading=28, wordWrap="CJK"
    )

    story = []
    bookmark_count = 0

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 10))
        elif line.startswith("【") and line.endswith("】"):
            key = f"bookmark_{bookmark_count}"
            bookmark_count += 1
            p = BookmarkParagraph(escape(line), heading_style,
                                  bookmark_key=key,
                                  bookmark_title=line.strip("【】"))
            story.append(p)
            story.append(Spacer(1, 6))
        elif "=====" in line:
            title = line.replace("=", "").strip()
            if title:
                key = f"bookmark_{bookmark_count}"
                bookmark_count += 1
                p = BookmarkParagraph(escape(title), heading_style,
                                      bookmark_key=key,
                                      bookmark_title=title)
                story.append(p)
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(escape(line), body_style))
            story.append(Spacer(1, 5))

    doc = BookmarkDocTemplate(pdf_path, pagesize=A4,
                              leftMargin=27*mm, rightMargin=27*mm,
                              topMargin=22*mm, bottomMargin=22*mm)
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
