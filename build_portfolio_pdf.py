from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage, ImageOps

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf" / "performance-edge-portfolio.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont("Inter", str(ROOT / "scripts/fonts/Inter-SemiBold.ttf")))
pdfmetrics.registerFont(TTFont("Playfair", str(ROOT / "scripts/fonts/PlayfairDisplay-Bold.ttf")))

INK = colors.HexColor("#181816")
MID = colors.HexColor("#5f5d57")
FAINT = colors.HexColor("#8c8980")
OFF = colors.HexColor("#f4f2ee")
RULE = colors.HexColor("#ddd9d0")
BLUE = colors.HexColor("#3a6ea8")
WHITE = colors.HexColor("#fafaf8")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Eyebrow", fontName="Inter", fontSize=7.5, leading=10, tracking=1.8, textColor=FAINT, spaceAfter=10))
styles.add(ParagraphStyle(name="Display", fontName="Playfair", fontSize=31, leading=34, textColor=INK, spaceAfter=14))
styles.add(ParagraphStyle(name="DisplayWhite", fontName="Playfair", fontSize=34, leading=36, textColor=WHITE, spaceAfter=14))
styles.add(ParagraphStyle(name="H2", fontName="Playfair", fontSize=21, leading=24, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name="Body", fontName="Inter", fontSize=9.2, leading=14.2, textColor=MID, spaceAfter=8))
styles.add(ParagraphStyle(name="BodyWhite", fontName="Inter", fontSize=9.2, leading=14.2, textColor=colors.HexColor("#d8d6d0"), spaceAfter=8))
styles.add(ParagraphStyle(name="Small", fontName="Inter", fontSize=7.4, leading=10, textColor=FAINT))
styles.add(ParagraphStyle(name="SmallWhite", fontName="Inter", fontSize=7.4, leading=10, textColor=colors.HexColor("#c8c6c0")))
styles.add(ParagraphStyle(name="Stat", fontName="Playfair", fontSize=18, leading=20, textColor=INK, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="StatLabel", fontName="Inter", fontSize=6.7, leading=8.5, textColor=FAINT, alignment=TA_CENTER))

def p(text, style="Body"):
    return Paragraph(text, styles[style])

_crop_cache = {}

def fit_image(path, width, height, crop=True):
    source = Path(path) if Path(path).is_absolute() else ROOT / path
    if not crop:
        iw, ih = ImageReader(str(source)).getSize()
        scale = min(width / iw, height / ih)
        cache_dir = ROOT.parent / "tmp" / "pdfs" / "portfolio-crops"
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / (source.stem + f"-preserve-v2-{int(width*100)}x{int(height*100)}.jpg")
        if not target.exists():
            with PILImage.open(source) as im:
                im = im.convert("RGB")
                im.thumbnail((max(1, int(width*2)), max(1, int(height*2))), PILImage.Resampling.LANCZOS)
                im.save(target, quality=90, optimize=True)
        tw, th = ImageReader(str(target)).getSize()
        fit_scale = min((width * 72) / tw, (height * 72) / th)
        img = Image(str(target), width=tw * fit_scale / 72, height=th * fit_scale / 72)
        img.hAlign = "CENTER"
        return img
    # Crop to the requested frame while preserving the source image's proportions.
    # This prevents the stretched-photo problem while keeping the editorial grid full.
    key = (str(source), round(width, 3), round(height, 3))
    if key not in _crop_cache:
        cache_dir = ROOT.parent / "tmp" / "pdfs" / "portfolio-crops"
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / (source.stem + f"-v2-{int(width*100)}x{int(height*100)}.jpg")
        if not target.exists():
            with PILImage.open(source) as im:
                im = im.convert("RGB")
                fitted = ImageOps.fit(im, (max(1, int(width*2)), max(1, int(height*2))), method=PILImage.Resampling.LANCZOS, centering=(0.5, 0.5))
                fitted.save(target, quality=94, optimize=True)
        _crop_cache[key] = target
    img = Image(str(_crop_cache[key]), width=width, height=height)
    img.hAlign = "CENTER"
    return img

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.62*inch, 0.42*inch, 7.88*inch, 0.42*inch)
    canvas.setFont("Inter", 6.5)
    canvas.setFillColor(FAINT)
    canvas.drawString(0.62*inch, 0.24*inch, "PERFORMANCE EDGE TRAINING + GYM DESIGN")
    canvas.drawRightString(7.88*inch, 0.24*inch, f"{doc.page}")
    canvas.restoreState()

doc = SimpleDocTemplate(str(OUT), pagesize=letter, rightMargin=0.62*inch, leftMargin=0.62*inch, topMargin=0.55*inch, bottomMargin=0.62*inch)
story = []

# Cover
story += [fit_image("/Users/scottschratwieser/Pictures/Photos Library.photoslibrary/resources/derivatives/1/12B958C2-9636-47BF-84C2-F0469E4C4D7F_1_105_c.jpeg", 5.0*inch, 1.45*inch), Spacer(1, 0.12*inch), p("RESIDENTIAL GYM DESIGN PORTFOLIO", "Eyebrow"), Spacer(1, 0.08*inch), p("The room should make<br/><i>training feel inevitable.</i>", "Display"), p("Private training environments designed around the architecture, routines, and standards of the people who use them.", "Body"), Spacer(1, 0.25*inch), fit_image("jupiter-wide-room.jpeg", 7.25*inch, 3.8*inch, crop=False), Spacer(1, 0.25*inch)]
cover_stats = [[p("01", "Stat"), p("02", "Stat"), p("03", "Stat")], [p("Strategy", "StatLabel"), p("Design direction", "StatLabel"), p("Equipment integration", "StatLabel")]]
t = Table(cover_stats, colWidths=[2.42*inch]*3)
t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LINEABOVE", (0,0), (-1,0), 0.5, RULE), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
story += [t, Spacer(1, 0.2*inch), p("madefromeffort.com  |  516-330-1348  |  scottschratwieser@gmail.com", "Small")]
story.append(PageBreak())

# Positioning
story += [p("RESIDENTIAL GYM DESIGN", "Eyebrow"), p("A fitness space that belongs to the architecture.", "Display"), p("Performance Edge creates private training environments that feel considered before they feel equipped. The work combines performance planning, spatial strategy, equipment selection, custom fabrication, and the details that make a room easy to use every day.", "Body"), Spacer(1, 0.12*inch)]
cap_data = [[p("PRIVATE RESIDENCES", "Eyebrow"), p("YACHTS + MARINE", "Eyebrow")], [p("High-performance home gyms that feel like part of the house - not an afterthought in a spare room.", "Body"), p("Convertible onboard training and recovery systems designed around movement, storage, hospitality, and limited square footage.", "Body")], [p("COUNTRY CLUBS", "Eyebrow"), p("COMMERCIAL FITNESS", "Eyebrow")], [p("Modernize underperforming fitness spaces into amenities members notice, use, and talk about.", "Body"), p("Clear equipment logic, durable details, and a point of view that makes a facility feel intentional.", "Body")]]
t = Table(cap_data, colWidths=[3.55*inch, 3.55*inch], rowHeights=[0.28*inch, 0.78*inch, 0.28*inch, 0.78*inch])
t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LINEBELOW", (0,1), (-1,1), 0.5, RULE), ("LINEBELOW", (0,3), (-1,3), 0.5, RULE), ("LINEAFTER", (0,0), (0,-1), 0.5, RULE), ("LEFTPADDING", (0,0), (-1,-1), 10), ("RIGHTPADDING", (0,0), (-1,-1), 18), ("TOPPADDING", (0,0), (-1,-1), 7)]))
story += [t, Spacer(1, 0.35*inch), fit_image("jupiter-full-room.jpeg", 7.25*inch, 2.75*inch, crop=False), Spacer(1, 0.14*inch), p("The goal is not more equipment. It is a better relationship between the space, the person using it, and the life around it.", "Small")]
story.append(PageBreak())

# Yacht case study
story += [p("FEATURED PROJECT 01  /  M/Y CANOE CANOE", "Eyebrow"), p("A real gym that disappears back into the yacht.", "Display"), fit_image("yacht-couch.png", 7.25*inch, 3.75*inch), Spacer(1, 0.16*inch)]
yacht_cols = [[p("THE BRIEF", "Eyebrow"), p("THE SYSTEM", "Eyebrow")], [p("Create a credible training and recovery environment on a yacht deck without compromising the feeling of a luxury hospitality space.", "Body"), p("NOHrD TriTrainer, a foldable WaterRower, custom Eleiko pull-up bar with a stainless roof bracket, TRX capability, concealed weights, a convertible couch, Chill Bunny plunge / hot tub, and optional virtual coaching with Performance Edge.", "Body")]]
t = Table(yacht_cols, colWidths=[3.55*inch, 3.55*inch])
t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LINEAFTER", (0,0), (0,-1), 0.5, RULE), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 18), ("TOPPADDING", (0,0), (-1,-1), 5)]))
story += [t, Spacer(1, 0.22*inch), p("Performance Edge originated and directed the convertible gym-furniture concept and the performance brief. Paragon Studio developed the finished bespoke product, leading the furniture design, engineering, drawer integration, equipment fitment, and fabrication.", "Body"), p("Result: a deck that transitions between training, recovery, and hospitality without asking the yacht to look like a gym.", "Body")]
story.append(PageBreak())

# Jupiter case study
story += [p("FEATURED PROJECT 02  /  JUPITER ISLAND", "Eyebrow"), p("A complete training environment inside a narrow footprint.", "Display"), fit_image("jupiter-full-room.jpeg", 3.1*inch, 4.15*inch, crop=False), Spacer(1, 0.18*inch)]
jup_right = [p("THE BRIEF", "Eyebrow"), p("Turn a 13-foot-wide estate space into a private training and recovery room that feels architectural, calm, and genuinely useful.", "Body"), p("THE DETAILS", "Eyebrow"), p("Custom Eleiko and Watson pieces, tailored upholstery, integrated storage, a deliberate circulation path, and Chill Bunny recovery equipment - all resolved as one environment.", "Body")]
t = Table([[fit_image("jupiter-wide-room.jpeg", 3.35*inch, 1.42*inch, crop=False), jup_right]], colWidths=[3.45*inch, 3.55*inch])
t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0), ("TOPPADDING", (0,0), (-1,-1), 0)]))
story += [t, Spacer(1, 0.18*inch), p("The strongest rooms often solve the most constraints. Here, the narrow footprint became the design discipline: every piece earns its place, every sightline stays clean, and the room still feels like part of the home.", "Body")]
story.append(PageBreak())

# Glen Cove design study
story += [p("DESIGN STUDY 03  /  GLEN COVE RESTORED BARN", "Eyebrow"), p("High-performance training, kept light in the room.", "Display"), fit_image("glen-cove-render-2.jpg", 7.25*inch, 3.35*inch, crop=False), Spacer(1, 0.16*inch)]
glen_cols = [[p("THE SETTING", "Eyebrow"), p("THE DIRECTION", "Eyebrow")], [p("A restored barn with an unusually broad wellness program: indoor swim pool, cold tub, hot tub, traditional sauna, steam room, and art room.", "Body"), p("These mid-project renders show equipment planned to integrate into the walls and preserve the space's light, airy character while still supporting the highest level workout.", "Body")]]
t = Table(glen_cols, colWidths=[3.55*inch, 3.55*inch])
t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LINEAFTER", (0,0), (0,-1), 0.5, RULE), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 18), ("TOPPADDING", (0,0), (-1,-1), 5)]))
glen_detail = Table([[fit_image("glen-cove-render-1.jpg", 3.45*inch, 1.75*inch, crop=False), fit_image("glen-cove-render-3.jpg", 3.45*inch, 1.75*inch, crop=False)]], colWidths=[3.55*inch, 3.55*inch])
glen_detail.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 10), ("TOPPADDING", (0,0), (-1,-1), 0)]))
story += [t, Spacer(1, 0.16*inch), p("Performance Edge is consulting on the gym and has contributed expertise to several complementary wellness spaces. The renders represent the design direction at mid-project, not a completed installation.", "Body"), Spacer(1, 0.08*inch), glen_detail]
story.append(PageBreak())

# Selected imagery
story += [p("SELECTED PROJECT IMAGERY", "Eyebrow"), p("The details are the design.", "Display"), p("A closer look at the rooms, equipment, and custom solutions behind the work.", "Body"), Spacer(1, 0.12*inch)]
gallery = [
    [fit_image("yacht-couch.png", 3.45*inch, 2.05*inch), fit_image("IMG_4936.jpeg", 3.45*inch, 2.05*inch)],
    [fit_image("jupiter-full-room.jpeg", 3.45*inch, 2.55*inch, crop=False), fit_image("jupiter-rack-detail.jpeg", 3.45*inch, 2.55*inch, crop=False)],
    [fit_image("yacht-exterior.jpeg", 3.45*inch, 1.7*inch, crop=False), fit_image("chill-bunny.png", 3.45*inch, 1.7*inch, crop=False)],
]
gallery_table = Table(gallery, colWidths=[3.55*inch, 3.55*inch], rowHeights=[2.18*inch, 2.7*inch, 1.85*inch])
gallery_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 10), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
story += [gallery_table, Spacer(1, 0.16*inch), p("Every image in this portfolio comes from the published Performance Edge project archive.", "Small")]
story.append(PageBreak())

# Process and CTA
story += [p("HOW WE WORK", "Eyebrow"), p("From performance brief to finished room.", "Display")]
process = [[p("01  DISCOVER", "Eyebrow"), p("02  DIRECT", "Eyebrow"), p("03  RESOLVE", "Eyebrow")], [p("We learn how the space needs to perform, who will use it, and what the architecture already says.", "Body"), p("We set the equipment logic, circulation, aesthetic direction, and partner strategy before the room becomes a shopping list.", "Body"), p("We coordinate the details that make the finished environment feel inevitable: fabrication, storage, surfaces, recovery, and ongoing use.", "Body")]]
t = Table(process, colWidths=[2.37*inch]*3)
t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LINEAFTER", (0,0), (1,-1), 0.5, RULE), ("LEFTPADDING", (0,0), (-1,-1), 10), ("RIGHTPADDING", (0,0), (-1,-1), 16), ("TOPPADDING", (0,0), (-1,-1), 7)]))
story += [t, Spacer(1, 0.35*inch), fit_image("jupiter-rack-detail.jpeg", 7.25*inch, 2.75*inch, crop=False), Spacer(1, 0.2*inch), p("Planning a private gym that feels like part of your home? Start with the room, not the equipment list.", "H2"), fit_image("/Users/scottschratwieser/Pictures/Photos Library.photoslibrary/resources/derivatives/C/C20EB532-EEEC-4A1C-B359-E4DA1360B203_1_102_o.jpeg", 1.15*inch, 1.15*inch), Spacer(1, 0.08*inch), p("Performance Edge Training + Gym Design\nMade From Effort\nmadefromeffort.com\n516-330-1348\nscottschratwieser@gmail.com", "Body")]

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
