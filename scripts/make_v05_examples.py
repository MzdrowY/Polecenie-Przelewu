"""Syntetyczne przykłady v0.5, bez danych osobowych."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.models import Payment
from app.pdfgen import generate_pdf
import fitz

def make_valid(bban):
    return str(98-int(bban+'252100')%97).zfill(2)+bban

def record(amount: str, *, stars=False, bar=True, typ='W'):
    return Payment(recipient='ODBIORCA PRZYKŁADOWY',recipient_address='UL. TESTOWA 1, 00-001 MIASTO',
        recipient_account=make_valid('109000000000000000000001'),
        amount=amount,currency='PLN', payer='NADAWCA PRZYKŁADOWY',
        payer_address='UL. PRÓBNA 2, 00-002 MIASTO',title='PRZYKŁADOWA WPŁATA TESTOWA',
        payer_account=make_valid('109000000000000000000099') if typ=='P' else '',
        payment_type=typ,amount_prefix_stars=stars,amount_end_bar=bar)

examples={'WPŁATA_1250_BEZ_GWIAZDEK_Z_KRESKĄ':record('1250,50'),
          'WPŁATA_1_01_W_KRATKACH':record('1,01'),
          'WPŁATA_1250_Z_GWIAZDKAMI_BEZ_KRESKI':record('1250,50',stars=True,bar=False),
          'PRZELEW_P_1250':record('1250,50',typ='P')}
docs=Path(__file__).resolve().parents[1]/'docs'
for name,p in examples.items():
    pdf=generate_pdf(p,docs/(name+'.pdf'))
    with fitz.open(pdf) as doc:
        page=doc[0]
        im=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
        im.save(docs/(name+'.png'))
        print(name, len(doc),round(page.rect.width,1),round(page.rect.height,1),pdf.stat().st_size)
